---
name: deploy-system
description: "Manages deployment operations on the deploy.bajiaolu.cn system — trigger deployments, monitor tasks, manage PM2 services, edit project configs, and view system status. Use when the user asks to deploy a project, check service status, or manage services on the deploy panel."
---

# deploy-system 运维部署系统

> 本文件面向系统的**使用方**——通过 API 完成部署与运维的 AI Agent。Agent 读取本文件时是接口的调用方，不是部署方：这里只写接口用法、参数解释与使用注意事项；安装、凭据生成、Nginx/服务器配置等部署细节见项目 README，不放入本文件。

---

## 1. 设计原则

整个系统只有 **5 个接口**，按"读/写/配"严格分工，同一接口路径绝不承担两种语义：

| 原则 | 落地 |
|------|------|
| 所有**只读查询** | `GET /api/query`，用 `type` 参数区分查什么（磁盘/内存/负载/日志/PM2 服务/PAT），扩展新查询只加 type |
| 所有**写操作** | `POST /api/ops`，用 `action` 参数区分做什么（重载 Nginx、控制服务等），扩展新操作只加 action |
| 所有**项目配置** | `POST /api/projects`，用 `action` 参数区分 list/save/delete/write |
| **部署** | 独立 `POST /api/deploy`（核心业务，手动与 Webhook 共用） |
| **异步任务** | 独立 `POST /api/tasks`（任务全生命周期：提交/查询/取消，`action` 区分） |

---

## 2. 系统概览

| 项目 | 值 |
|------|-----|
| 服务器 | 腾讯云 62.234.16.218 |
| Base URL | `https://deploy.bajiaolu.cn`（HTTPS，Let's Encrypt） |
| Web 面板 | `https://deploy.bajiaolu.cn/panel`（人类用户使用） |
| GitHub 仓库 | `https://github.com/engrecho/deploy-system` |
| 服务端口 | 11417（Node.js 原生 HTTP，无框架） |
| PM2 服务名 | `deploy-ops-api` |
| 代码目录 | `/www/wwwroot/deploy` |
| 配置文件 | `/www/wwwroot/deploy/config/projects.conf` |
| API Key | `dcdIEUot2rX2BYPCaAD8NBteWcTX53H4RVdeilo8cd0gjL13tamylvSFkhUdTnRkt5O5bZpkqFI7QR2rFRjWfcSJJ9xroQNQoTtZmwHxdM9693nM7OvEQkboEpP6mxpo` |

**GitHub 代理说明**：服务器无法直连 GitHub，部署时自动通过 `gh-proxy.com` 代理拉取代码。本地开发连不上 GitHub 时：`export https_proxy=http://127.0.0.1:7890 http_proxy=http://127.0.0.1:7890`。

---

## 3. 鉴权方式

**所有 API 接口均需鉴权，无任何例外**。唯一的公开资源是 `/panel` 页面外壳（HTML 内不含任何密钥）。

鉴权方式二选一：

```bash
# 方式一：URL Query 参数
curl "https://deploy.bajiaolu.cn/api/query?type=load&token=KEY"

# 方式二：HTTP Header
curl "https://deploy.bajiaolu.cn/api/query?type=load" -H "X-API-Key: KEY"
```

### 凭据管理（仅部署方关心，Agent 只需向用户索要 API Key）

所有凭据存于服务器本地 `.api-keys`（600 权限，永不进 Git），由部署方维护，**Agent 无需了解其内部格式**。GitHub PAT 可通过 `GET /api/query?type=pat` 读取、`POST /api/ops` 的 `pat_set` 动作更新（见第 8 / 9 节）。

鉴权失败统一返回：

```json
{ "error": "Unauthorized" }   // HTTP 401
```

---

## 4. Agent 快速上手

1. **确认项目已在 `projects.conf` 注册**（见第 10 节）。没注册则先 `POST /api/projects` 的 `save` 动作添加。
2. **调用任何接口都带 `?token=KEY`**。
3. **部署是异步的**：`POST /api/deploy` 立即返回 `task_id`，用 `POST /api/tasks` 的 `{"action":"get","id":"xxx"}` 轮询，直到 `status` 变为 `done` 或 `failed`。
4. **部署会强制覆盖服务器代码**（`git reset --hard origin/<branch>`），服务器上的本地修改会丢失。

---

## 5. 接口总览（共 5 个）

| # | 接口 | 方法 | 职责 |
|---|------|------|------|
| 1 | `/api/deploy` | POST | 触发部署（手动 + GitHub Webhook 共用） |
| 2 | `/api/tasks` | POST | **任务全生命周期**：提交 / 查询 / 取消（`action` 参数区分） |
| 3 | `/api/query` | GET | **所有只读查询**：系统信息 / 服务 / PAT（`type` 参数区分） |
| 4 | `/api/ops` | POST | **所有写操作**：重载 Nginx / 控制服务 / 更新 PAT（`action` 参数区分） |
| 5 | `/api/projects` | POST | **项目配置管理**：list / save / delete / write（`action` 参数区分） |

---

## 6. 部署 — POST /api/deploy

**系统唯一的部署入口**，手动部署与 GitHub Webhook 共用（服务端根据 body 自动区分：手动传 `project`，Webhook 传 `ref` + `repository`）。

**请求参数（JSON body）**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `project` | string | 是* | 项目名（= GitHub 仓库名），必须在 `projects.conf` 中有映射。*Webhook 时从 `repository.name` 自动提取 |
| `action` | string | 否 | 部署动作，默认 `deploy`，枚举见下表 |
| `branch` | string | 否 | Git 分支，默认 `main`。Webhook 时从 `ref` 自动解析 |
| `path` | string | 否 | 自定义部署路径——项目不在 `projects.conf` 中时使用 |
| `pm2` | string | 否 | 自定义 PM2 服务名，仅在传了 `path` 时生效，默认为 `project` |
| `url` | string | 否 | 自定义 Git clone URL（不传则由 `git` 字段解析，自动加 gh-proxy 代理） |

**action 枚举**：

| action | 拉代码 | 装依赖 | 构建 | 重启 PM2 | 适用场景 |
|--------|--------|--------|------|----------|----------|
| `deploy` | ✅ | ✅ | ✅ | ✅ | 完整部署（默认） |
| `build` | ❌ | ✅ | ✅ | ✅ | 代码已在服务器，只需重新构建 |
| `pull` | ✅ | ✅ | ✅ | ❌ | 先拉代码构建，暂不重启 |
| `restart` | ❌ | ❌ | ❌ | ✅ | 仅重启 PM2，适合纯配置变更 |

**实际执行步骤**：目录无 `.git` 时自动 clone（gh-proxy 代理）→ `git reset --hard origin/<branch>`（**强制覆盖本地改动**）→ `yarn/npm install` → 有 build 脚本则 `yarn build` → `pm2 restart`（无此服务则尝试 `server/index.js`、`index.js` 作为入口启动）→ `pm2 save`。

**示例**：

```bash
KEY="dcdIEUot2rX2BYPCaAD8NBteWcTX53H4RVdeilo8cd0gjL13tamylvSFkhUdTnRkt5O5bZpkqFI7QR2rFRjWfcSJJ9xroQNQoTtZmwHxdM9693nM7OvEQkboEpP6mxpo"

curl -X POST "https://deploy.bajiaolu.cn/api/deploy?token=$KEY" \
  -H 'Content-Type: application/json' \
  -d '{"project":"myapp","action":"deploy"}'
```

**响应**：`{ "task": "a1b2c3d4e5f6", "project": "myapp", "branch": "main", "message": "Deploying myapp@main" }`（HTTP 200，异步执行）。部署任务固定 300 秒超时。

**GitHub Webhook 配置**：Payload URL 填 `https://deploy.bajiaolu.cn/api/deploy?token=KEY`，Content type 选 `application/json`，Events 选 Just the push event。

---

## 7. 任务 — POST /api/tasks（任务全生命周期的唯一入口，核心运维接口）

这是**核心运维接口**：异步任务的**提交、查询、取消**全部在这里完成，`action` 参数区分。部署（`/api/deploy`）返回的 `task_id` 同样在这里查询——部署也是任务体系的一员。

**action 全集**：

| action | 功能 | 额外参数 | 说明 |
|--------|------|----------|------|
| `submit` | 提交异步任务 | `cmd`*、`timeout`（毫秒，默认600000） | 传了 `cmd` 时 action 可省略，默认即 submit |
| `list` | 全部任务列表 | 无 | cmd 截断 70 字符，适合快速浏览 |
| `get` | 单任务详情 | `id`*（task_id） | 含 out/err 完整输出，**部署结果轮询用这个** |
| `cancel` | 取消任务 | `id`* | 只能取消 `pending` 状态；执行中的无法取消 |

**任务 status 流转**：`pending`（排队）→ `running`（执行中）→ `done` / `failed` / `cancelled`（终态，可停止轮询）。任务存内存，服务重启后历史清空。

**安全过滤**：命令以 `reboot`、`shutdown`、`halt` 开头会被拒绝（HTTP 403）。`rm -rf` 等不拦截（个人使用），Agent 应谨慎构造命令。

**并发限制**：最多 5 个任务同时执行，超出排队。单任务输出上限 10MB。

**使用示例**：

```bash
# 1) 提交任务（传 cmd 即提交，action 可省略）
curl -X POST "https://deploy.bajiaolu.cn/api/tasks?token=$KEY" \
  -H 'Content-Type: application/json' \
  -d '{"cmd":"ls -la /www/wwwroot","timeout":60000}'
# 响应：{ "task": "a1b2c3d4e5f6" }

# 2) 查询单个任务/部署结果（轮询直到 status 为终态）
curl -X POST "https://deploy.bajiaolu.cn/api/tasks?token=$KEY" \
  -H 'Content-Type: application/json' \
  -d '{"action":"get","id":"a1b2c3d4e5f6"}'

# 3) 列出全部任务
curl -X POST "https://deploy.bajiaolu.cn/api/tasks?token=$KEY" \
  -H 'Content-Type: application/json' -d '{"action":"list"}'

# 4) 取消排队中的任务
curl -X POST "https://deploy.bajiaolu.cn/api/tasks?token=$KEY" \
  -H 'Content-Type: application/json' -d '{"action":"cancel","id":"a1b2c3d4e5f6"}'
```

---

## 8. 查询 — GET /api/query（所有只读查询的唯一入口）

一个接口覆盖所有查询，`type` 参数区分，**后续新查询项也在这里扩展**：

```bash
curl "https://deploy.bajiaolu.cn/api/query?type=disk&token=$KEY"
```

**type 全集**：

| type | 内容 | 额外参数 | 响应 |
|------|------|----------|------|
| `disk` | 磁盘使用（df -hT） | 无 | `{type, output}` |
| `memory` | 内存使用（free -h） | 无 | `{type, output}` |
| `load` | 系统负载（uptime） | 无 | `{type, output}` |
| `log` | 系统运行日志末 50 行 | 无 | `{type, output}` |
| `services` | PM2 服务列表 | 无 | `{type, services:[{name,status,cpu,mem}]}` |
| `service_logs` | 指定服务日志 | `name`*、`lines`（默认50） | `{type, output}` |
| `pat` | 当前 GitHub PAT（面板维护用） | 无 | `{pat}` |

type 非法返回 HTTP 400，列出来所有合法值。

> 注：任务查询不在此接口——任务的提交/查询/取消统一在 `POST /api/tasks`（见第 7 节）。

---

## 9. 操作 — POST /api/ops（所有写操作的唯一入口）

一个接口覆盖所有操作动作，`action` 参数区分，**后续新操作也在这里扩展**：

```bash
curl -X POST "https://deploy.bajiaolu.cn/api/ops?token=$KEY" \
  -H 'Content-Type: application/json' \
  -d '{"action":"nginx_reload"}'
```

**action 全集**：

| action | 功能 | 额外参数 | 说明 |
|--------|------|----------|------|
| `nginx_reload` | 重载 Nginx | 无 | 先 `nginx -t` 校验语法，通过才 reload；失败返回 HTTP 500 及错误详情，不影响现有配置 |
| `service_restart` | 重启 PM2 服务 | `name`* | 服务名不存在返回 HTTP 500 |
| `service_stop` | 停止服务 | `name`* | 同上 |
| `service_start` | 启动服务 | `name`* | 同上 |
| `pat_set` | 更新 GitHub PAT | `pat`*（空字符串清除） | 写入 `.api-keys` 的 `pat:` 行，立即生效无需重启；读取用 `GET /api/query?type=pat` |

**示例**：

```bash
# 重启服务
curl -X POST "https://deploy.bajiaolu.cn/api/ops?token=$KEY" \
  -H 'Content-Type: application/json' \
  -d '{"action":"service_restart","name":"ai-buddy-api"}'
```

---

## 10. 项目配置 — POST /api/projects（projects.conf 管理唯一入口）

`projects.conf`（YAML）是核心映射表：**项目名 → git 地址 + 服务器路径 + PM2 服务名**。所有操作收敛在这一个 POST 接口，`action` 参数区分：

```yaml
myapp:
  git: engrecho/myapp      # user/repo 简写，或完整 URL
  path: /www/wwwroot/myapp
  pm2: myapp-api
```

### action 全集

**`list` — 项目列表**（`status:1` 附带 PM2 状态；`raw:1` 附带原始 YAML）：

```bash
curl -X POST "https://deploy.bajiaolu.cn/api/projects?token=$KEY" \
  -H 'Content-Type: application/json' \
  -d '{"action":"list","status":1}'
```

响应：`{ "projects": [{ "name","git","path","pm2","pm2Status" }], "config": "原始YAML（raw=1时）" }`

**`save` — 新增/编辑单个项目**（四字段全必填，同名覆盖即编辑）：

```bash
curl -X POST "https://deploy.bajiaolu.cn/api/projects?token=$KEY" \
  -H 'Content-Type: application/json' \
  -d '{"action":"save","name":"myapp","git":"engrecho/myapp","path":"/www/wwwroot/myapp","pm2":"myapp-api"}'
```

**`delete` — 删除项目**（只删配置，不动文件和 PM2 进程；不存在返回 404）：

```bash
curl -X POST "https://deploy.bajiaolu.cn/api/projects?token=$KEY" \
  -H 'Content-Type: application/json' \
  -d '{"action":"delete","name":"myapp"}'
```

**`write` — 全量替换 YAML**（非增量！标准姿势：`list` 带 `raw:1` 读取 → 修改 → `write` 写回 → `list` 确认）：

```bash
curl -X POST "https://deploy.bajiaolu.cn/api/projects?token=$KEY" \
  -H 'Content-Type: application/json' \
  -d '{"action":"write","config":"# projects.conf\nmyapp:\n  git: engrecho/myapp\n  path: /www/wwwroot/myapp\n  pm2: myapp-api\n"}'
```

响应含解析后的新 `projects` 数组，写回后建议再 list 确认。

---

## 11. Web 面板

地址：`https://deploy.bajiaolu.cn/panel`

- 账号密码登录（服务端校验后下发 Key；页面外壳不含任何密钥）
- 项目列表 + PM2 实时状态、一键部署 / 删除 / 编辑配置
- GitHub PAT 维护（读取/更新/清除，存 `.api-keys` 的 `pat:` 行，立即生效）
- 查看运行日志、复制 GitHub Webhook 链接
- 内置 API 文档页：分类目录 + 每个接口一键复制可测试的 curl 脚本
- 移动端适配

---

## 12. 使用注意事项

- **全接口鉴权，无例外**：所有 API 都需要 token；唯一免鉴权的是 `/panel` 页面外壳（HTML 内不含任何密钥）
- **Webhook 也需鉴权**：Payload URL 必须带 `?token=KEY`
- **危险命令过滤**：`reboot` / `shutdown` / `halt` 开头的命令被拦截；`rm -rf` 等不拦截（个人使用），Agent 应自行谨慎
- **HTTPS 全程加密**：Let's Encrypt 证书
- **密钥不要外泄**：API Key 仅在私密渠道转发给受信 Agent，严禁出现在公开群聊、Git Commit、Issue、截图、日志中
