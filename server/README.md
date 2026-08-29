# server — 微信发布中转服务

## 作用

解决微信公众号 API 的 **IP 白名单**限制：本服务部署在腾讯云服务器（出口 IP 已加入白名单），客户端把发布请求发到本服务，由本服务从服务器出口转发到 `api.weixin.qq.com`。

技术：Node.js 原生 HTTP 代理（无第三方框架），无数据库。

## 目录内容

| 文件 | 说明 |
|------|------|
| `index.js` | 中转代理服务（转发 /draft/add 等微信 API 请求） |
| `package.json` | 服务依赖（仅 node，无第三方依赖） |
| `deploy.sh` | **首次部署**脚本：装环境 → 复制代码 → 生成 `.env` → PM2 启动 |
| `README.md` | 本说明 |

## 首次部署（一次性）

在服务器上（本仓库克隆目录内）执行：

```bash
bash server/deploy.sh
```

脚本会交互式生成 `server/.env`（含 `PUBLISH_API_TOKEN`），并输出需要记下的客户端配置：

- `server_publish_url` / `server_publish_token`（填到客户端 `~/.post-to-wechat/EXTEND.md`）
- 部署目标：`/www/wwwroot/post-to-wechat/server/`，PM2 服务名 `wechat-publish`，端口 `8080`

随后还需手动完成 2 件事（脚本末尾会提示）：

1. **微信 IP 白名单**：mp.weixin.qq.com → 设置与开发 → 基本配置 → IP 白名单，添加本服务器出口 IP
2. **宝塔反向代理**：域名（如 tencent.bajiaolu.cn）→ SSL → 反代到 `http://127.0.0.1:8080`

## 后续更新

代码 push 后，通过 **deploy-system**（https://deploy.bajiaolu.cn）触发部署：

```bash
curl -X POST "https://deploy.bajiaolu.cn/api/deploy?token=$KEY" \
  -H 'Content-Type: application/json' \
  -d '{"project":"publish-to-wechat-mp","branch":"main","action":"deploy"}'
```

> 若项目的部署路径/服务名已配置在 `projects.conf`，无需额外参数。查看部署进度：

```bash
curl -X POST "https://deploy.bajiaolu.cn/api/tasks?token=$KEY" \
  -H 'Content-Type: application/json' \
  -d '{"action":"get","id":"<task_id>"}'
```

## 客户端配置

```yaml
# ~/.post-to-wechat/EXTEND.md
default_publish_method: server-api
server_publish_url: https://<你的域名>
server_publish_token: <deploy.sh 输出的 PUBLISH_API_TOKEN>
server_publish_timeout: 60
```

## 常用运维命令

```bash
pm2 status                 # 查看服务状态
pm2 logs wechat-publish    # 查看日志
pm2 restart wechat-publish # 重启服务
pm2 stop wechat-publish    # 停止服务
```

## 环境变量

| 变量 | 必填 | 默认 | 说明 |
|------|------|------|------|
| `PUBLISH_API_TOKEN` | 是 | - | 客户端访问本服务的鉴权 token |
| `PORT` | 否 | `8080` | 监听端口 |

> `.env` 位于部署后的 `server/.env`，权限 600，不入 Git。
