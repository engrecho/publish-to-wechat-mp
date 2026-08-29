---
name: publisher
description: 发布到微信公众号。支持 remote-api（默认，经白名单服务器 SSH SOCKS5 隧道出口）、api、browser 三种方式，将最终 HTML 存为公众号草稿。当用户要求"发布/发草稿/推送到公众号"时触发；在 gzh-pipeline 流程中作为最后阶段。
version: 2.0.0
metadata:
  openclaw:
    requires:
      anyBins:
        - bun
        - npx
---

# 公众号发布器

## 概述

将 typography 输出的 final.html（或用户直接提供的 Markdown/HTML）发布到微信公众号草稿箱。严格按以下顺序执行：

1. 加载偏好设置（EXTEND.md）
2. 确定账号（多账号时）
3. 选择发布方式并校验凭据
4. 发布到微信
5. 报告完成情况

## 发布方式

| 方式 | 速度 | 前置条件 |
|------|------|---------|
| remote-api（默认推荐） | 快 | API 凭据 + SSH 可达且 IP 在微信白名单的服务器（62.234.16.218） |
| api | 快 | API 凭据，本机 IP 必须在白名单内 |
| browser | 慢 | Chrome + 已登录公众号的会话 |

**remote-api 原理**：渲染、图片处理、草稿组装均在本地完成，仅发往 api.weixin.qq.com 的 HTTPS 调用（token、uploadimg、add_material、draft/add）经 SSH SOCKS5 动态端口转发从服务器出口发出。AppSecret 不离开本地进程，服务器上不写入任何文件。

## 偏好设置（EXTEND.md）

按顺序检查，首个命中生效：

| 路径 | 作用域 |
|------|-------|
| `.post-to-wechat/EXTEND.md` | 项目级 |
| `${XDG_CONFIG_HOME:-$HOME/.config}/post-to-wechat/EXTEND.md` | XDG 规范 |
| `$HOME/.post-to-wechat/EXTEND.md` | 用户级 |

**最小配置键**：

| 键 | 默认值 | 说明 |
|-----|---------|------|
| `default_publish_method` | 空 | 设为 `remote-api` 即默认走远程发布 |
| `default_author` | 空 | 作者回退值 |
| `need_open_comment` | `1` | 是否开启评论 |
| `only_fans_can_comment` | `0` | 是否仅粉丝可评论 |
| `remote_publish_host` | — | 服务器地址 |
| `remote_publish_user` | — | SSH 用户 |
| `remote_publish_password` | — | SSH 密码（需 sshpass，仅限受信任私有服务器） |
| `remote_publish_identity_file` | — | SSH 密钥（生产推荐；与 password 同时设置时优先） |

**推荐的 EXTEND.md 配置**：

```md
default_publish_method: remote-api
remote_publish_host: 62.234.16.218
remote_publish_user: root
remote_publish_identity_file: ~/.ssh/id_tencent
remote_publish_strict_host_key_checking: accept-new
need_open_comment: 1
only_fans_can_comment: 0
```

**值优先级**：CLI 参数 → frontmatter → EXTEND.md → 技能默认值。

**多账号**：EXTEND.md 的 `accounts:` 块支持多公众号，详见 `../references/multi-account.md`。

## 发布流程

### 步骤 1：加载 EXTEND.md

未找到时先执行首次设置（`../references/config/first-time-setup.md`）。

### 步骤 2：确定输入

| 输入 | 检测方式 | 后续 |
|------|---------|------|
| HTML 文件（final.html） | 路径以 .html 结尾且存在 | 直接进入发布 |
| Markdown 文件 | 路径以 .md 结尾且存在 | 由发布脚本内部渲染（勿预转 HTML） |
| 纯文本 | 非文件路径 | 保存为 post-to-wechat/YYYY-MM-DD/<slug>.md 再发布 |

### 步骤 3：校验凭据

- API 凭据缺失 → 按 `../references/api-setup.md` 引导设置（写入 `.post-to-wechat/.env`）
- remote-api 缺 SSH 配置 → 按 `../references/server-setup.md` 引导（白名单 + sshpass/密钥）
- 飞行前检查（可选）：`bun ./scripts/check-permissions.ts`

### 步骤 4：发布

**远程 API 方式（默认）**：

```bash
bun ./scripts/wechat-api.ts work/<slug>/final.html \
  --theme <theme> --remote \
  [--remote-host <host>] [--remote-identity-file <path>] \
  [--title <title>] [--summary <summary>] [--author <author>] \
  [--cover work/<slug>/images/cover.jpg] [--source-url <url>] [--no-cite]
```

**API 方式**（本机 IP 在白名单时）：

```bash
bun ./scripts/wechat-api.ts <file> --theme <theme> [同上参数]
```

**贴图发布（图文，最多 9 张图）**：

```bash
bun ./scripts/wechat-browser.ts --markdown article.md --images ./images/
bun ./scripts/wechat-browser.ts --title "标题" --content "内容" --image img.png --submit
```

**draft/add 请求体规则**：

- 接口：`POST https://api.weixin.qq.com/cgi-bin/draft/add?access_token=ACCESS_TOKEN`
- `article_type`：`news`（默认，必须有 `thumb_media_id` 即封面）或 `newspic`
- 始终包含 `need_open_comment`（默认 1）和 `only_fans_can_comment`（默认 0）
- `content_source_url`（"阅读原文"链接，≤1KB）由 `--source-url` 或 frontmatter 提供

### 步骤 5：完成报告

```
微信公众号发布完成！

输入：[type] - [path]
方式：[remote-api | api | 浏览器]
主题：[theme] [color]

文章信息：
• 标题：[title]
• 摘要：[summary]
• 图片：[N] 张
• 封面：[cover]

发布结果：
✓ 草稿已保存至微信公众号
• media_id: [media_id]
• 原创声明：[已声明/未声明]（gzh-pipeline 流程提示：去后台验证原创声明）

后续操作：
→ 管理草稿：https://mp.weixin.qq.com（内容管理 → 草稿箱）
```

## 常见问题

| 问题 | 修复方法 |
|------|---------|
| `errcode 40164`（IP 无效） | 服务器出口 IP 不在微信白名单，公众号设置 → 基本配置 → IP 白名单中添加 |
| `SOCKS proxy on 127.0.0.1:… not ready` | SSH 隧道未建立：检查主机/凭据/StrictHostKeyChecking，链路慢提高 connect-timeout |
| `sshpass: command not found` | 安装 sshpass（macOS：`brew install hudochenkov/sshpass/sshpass`；Ubuntu：`apt install sshpass`）或改用密钥 |
| Remote publish requires either password or identity_file | 两种认证都未配置，在 EXTEND.md 设置其一 |
| access_token 错误 | 验证凭据有效且未过期 |
| 未登录（浏览器方式） | 首次运行扫码登录；可配 TELEGRAM_BOT_TOKEN 接收二维码 |

## 参考文档

| 文件 | 内容 |
|------|------|
| `../references/api-setup.md` | API 凭据引导设置 |
| `../references/server-setup.md` | 服务器侧设置：IP 白名单、SSH、sshpass |
| `../references/article-posting.md` | 文章主题、图片处理 |
| `../references/image-text-posting.md` | 贴图参数、自动压缩 |
| `../references/multi-account.md` | 多账号兼容性、凭据、CLI 用法 |
| `../references/config/first-time-setup.md` | 首次 EXTEND.md 设置 |
