# Webhook 参数化部署

一个 Webhook 端点，根据 `project` 参数路由到不同项目的部署脚本，支持多项目、多分支、多种动作。

## 工作流程

```
GitHub push event
       │
       ▼
https://tencent.bajiaolu.cn:11416/hook?access_key=xxx&project=aibuddy
       │
       ▼
宝塔 WebHook 插件
       │ (执行脚本，$1 = query string)
       ▼
webhook-router.sh  ─── 解析 project/branch/action 参数
       │
       ├─ project=aibuddy   →  deploy-aibuddy.sh   →  /www/wwwroot/aibuddy
       └─ project=wechat-mp →  deploy-wechat-mp.sh →  /www/wwwroot/wechat-mp/server
```

## URL 参数

```
https://tencent.bajiaolu.cn:11416/hook?access_key=xxx&project=<project>&branch=<branch>&action=<action>
```

| 参数 | 必填 | 默认 | 说明 |
|------|------|------|------|
| `access_key` | 是 | - | 宝塔 WebHook 鉴权密钥 |
| `project` | 是 | - | 部署项目：`aibuddy` / `wechat-mp` |
| `branch` | 否 | `main` | 部署分支 |
| `action` | 否 | `deploy` | 动作：`deploy` / `pull` / `restart` |

### action 语义

| action | 行为 |
|--------|------|
| `deploy` | git pull → 构建（npm install / composer install）→ 重启服务（PM2 / php-fpm / nginx） |
| `pull` | 仅 git pull，不构建不重启 |
| `restart` | 仅重启服务，不拉代码 |

## 服务器端安装（一次性）

SSH 上服务器执行：

```bash
cd /tmp
curl -fsSL -o webhook.tar.gz https://ghproxy.com/https://github.com/engrecho/publish-to-wechat-mp/archive/refs/heads/main.tar.gz
tar xzf webhook.tar.gz 'publish-to-wechat-mp-main/webhook'
cd publish-to-wechat-mp-main/webhook
bash install-webhook.sh
```

`install-webhook.sh` 会：
1. 把 `webhook-router.sh` / `deploy-aibuddy.sh` / `deploy-wechat-mp.sh` 复制到 `/www/server/panel/script/`
2. 询问并写入 access_key 到 `/www/server/panel/script/.webhook-access-key`
3. 创建日志文件 `/var/log/webhook-deploy.log`
4. 输出宝塔面板与 GitHub 的配置指引

## 宝塔面板配置（一次性）

1. 宝塔面板 → 软件商店 → 安装「宝塔WebHook」插件
2. 打开 WebHook 插件 → 添加 hook
3. 填写：
   - **名称**: `deploy-router`
   - **执行脚本**:
     ```bash
     bash /www/server/panel/script/webhook-router.sh "$1"
     ```
     > 注意：`$1` 要保留原样，宝塔会自动把 query string 传进来
4. 保存

## GitHub 仓库配置

在每个 GitHub 仓库的 Settings → Webhooks → Add webhook：

### AI-buddy 仓库

```
Payload URL:  https://tencent.bajiaolu.cn:11416/hook?access_key=<key>&project=aibuddy
Content type: application/json
Events:       Just the push event
```

### publish-to-wechat-mp 仓库

```
Payload URL:  https://tencent.bajiaolu.cn:11416/hook?access_key=<key>&project=wechat-mp
Content type: application/json
Events:       Just the push event
```

> 把 `<key>` 替换为宝塔 WebHook 插件生成的 access_key

## 手动触发

不依赖 GitHub push 也能触发部署：

```bash
# 仅拉取代码
curl 'https://tencent.bajiaolu.cn:11416/hook?access_key=xxx&project=wechat-mp&action=pull'

# 拉取 + 构建 + 重启
curl 'https://tencent.bajiaolu.cn:11416/hook?access_key=xxx&project=wechat-mp&action=deploy'

# 部署指定分支
curl 'https://tencent.bajiaolu.cn:11416/hook?access_key=xxx&project=wechat-mp&branch=dev&action=deploy'

# 仅重启服务
curl 'https://tencent.bajiaolu.cn:11416/hook?access_key=xxx&project=wechat-mp&action=restart'
```

## 部署目标路径

| project | 部署目录 | 服务名 |
|---------|----------|--------|
| `aibuddy` | `/www/wwwroot/aibuddy` | `aibuddy`（PM2，如有 Node 部分）+ php-fpm + nginx |
| `wechat-mp` | `/www/wwwroot/wechat-mp` | `wechat-publish`（PM2） |

## 日志

```bash
# 实时查看部署日志
tail -f /var/log/webhook-deploy.log

# 查看最近 50 行
tail -50 /var/log/webhook-deploy.log

# 查看 PM2 服务日志
pm2 logs wechat-publish --lines 30
pm2 logs aibuddy --lines 30
```

## 扩展：新增一个项目

1. 在 `/workspace/webhook/` 目录下新建 `deploy-<new-project>.sh`，参考 `deploy-wechat-mp.sh` 模板
2. 修改 `webhook-router.sh` 的 `case "$PROJECT"` 分支，新增：
   ```bash
   new-project)
     DEPLOY_SCRIPT="$SCRIPT_DIR/deploy-new-project.sh"
     ;;
   ```
3. push 到 GitHub → 服务器跑 `bash install-webhook.sh` 重新安装
4. 在新项目的 GitHub 仓库 Webhook URL 里加 `&project=new-project`

## 首次部署注意

Webhook 只负责「更新」（pull + 构建 + 重启）。**首次部署**需要：

- `wechat-mp`：先 SSH 上服务器跑 `bash deploy.sh`（在仓库根目录），它会交互式生成 `server/.env` 并首次启动 PM2
- `aibuddy`：在宝塔面板创建站点，绑定域名 + SSL，配置 nginx root 到 `/www/wwwroot/aibuddy/public`

之后 push 代码就会自动触发 webhook 更新。

## 安全

- `access_key` 存于 `/www/server/panel/script/.webhook-access-key`，权限 600
- `server/.env` 由首次 `deploy.sh` 交互式生成，权限 600
- webhook 走 HTTPS（宝塔自动签发或手动配 Let's Encrypt）
- 建议在宝塔防火墙限制 11416 端口仅放行 GitHub IP 段（如能确定）

## 故障排查

| 现象 | 排查 |
|------|------|
| webhook 触发但无部署日志 | `tail -f /var/log/webhook-deploy.log`；检查宝塔 webhook 脚本是否正确 |
| `access_key 不匹配` | 检查 URL 里的 key 与 `/www/server/panel/script/.webhook-access-key` 是否一致 |
| `部署脚本不存在` | 跑 `bash install-webhook.sh` 重新安装脚本 |
| `PM2 进程不存在` | 首次部署需先手动 `bash deploy.sh` 启动 |
| `git clone 失败` | 腾讯云访问 GitHub 受限，确认脚本用了 `ghproxy.com` 代理 |
| 部署后服务不可用 | `pm2 logs <service> --lines 50` 查看错误 |
