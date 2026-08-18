---
name: post-to-wechat
description: 通过 API 或 Chrome CDP 向微信公众号发布内容。支持文章发布（文章），可输入 HTML、Markdown 或纯文本；也支持贴图发布（贴图，原名图文），可包含多张图片。Markdown 文章工作流默认将普通外部链接转换为底部引用，以生成对微信友好的输出。当用户提到"发布公众号"、"post to wechat"、"微信公众号"或"贴图/图文/文章"时触发。
version: 1.118.2
metadata:
  openclaw:
    requires:
      anyBins:
        - bun
        - npx
---

# 微信公众号发布技能

## 用户输入工具

当此技能需要提示用户时，遵循以下工具选择规则（按优先级排序）：

1. **优先使用当前代理运行时暴露的内置用户输入工具** — 例如 `AskUserQuestion`、`request_user_input`、`clarify`、`ask_user` 或任何等效工具。
2. **备选方案**：如果不存在此类工具，则输出带编号的纯文本消息，要求用户回复选择的编号/答案。
3. **批量处理**：如果工具支持每次调用多个问题，则将所有适用的问题合并为一次调用；如果仅支持单问题提问，则按优先级逐个提问。

下方具体的 `AskUserQuestion` 引用仅为示例 — 在其他运行时中请替换为本地等效工具。

## 语言

使用用户的语言进行回复。如果他们用中文书写，则用中文回复；如果用英文，则用英文回复。技术标记（路径、标志、字段名）保持英文即可。

## 脚本目录

`{baseDir}` = 本 SKILL.md 所在的目录。解析 `${BUN_X}`：优先使用 `bun`；否则使用 `npx -y bun`；否则建议执行 `brew install oven-sh/bun/bun`。

| 脚本 | 用途 |
|--------|---------|
| `scripts/wechat-browser.ts` | 贴图发布（图文） |
| `scripts/wechat-article.ts` | 通过浏览器发布文章（文章） |
| `scripts/wechat-api.ts` | 通过 API 发布文章（文章） |
| `scripts/md-to-wechat.ts` | Markdown → 带图片占位符的微信格式 HTML |
| `scripts/check-permissions.ts` | 验证环境与权限 |

## 偏好设置（EXTEND.md）

按顺序检查以下路径，首个命中即生效：

| 路径 | 作用域 |
|------|-------|
| `.post-to-wechat/EXTEND.md` | 项目级 |
| `${XDG_CONFIG_HOME:-$HOME/.config}/post-to-wechat/EXTEND.md` | XDG 规范 |
| `$HOME/.post-to-wechat/EXTEND.md` | 用户级 |

找到 → 读取、解析并应用。未找到 → 在运行任何其他操作之前先执行首次设置（`references/config/first-time-setup.md`）。

**最小配置键**（不区分大小写，接受 `1/0` 或 `true/false`）：

| 键 | 默认值 | 映射 |
|-----|---------|--------|
| `default_author` | 空 | 当 CLI/未提供 frontmatter 时作为 `author` 的回退 |
| `need_open_comment` | `1` | `draft/add` 请求中 `articles[].need_open_comment` |
| `only_fans_can_comment` | `0` | `draft/add` 请求中 `articles[].only_fans_can_comment` |

**推荐的 EXTEND.md 配置**：

```md
default_theme: default
default_color: blue
default_publish_method: remote-api
default_author:
need_open_comment: 1
only_fans_can_comment: 0
chrome_profile_path: /path/to/chrome/profile

# 远程 API 发布（可选）— 仅当微信的 IP 白名单
# 不包含你本机 IP 时使用。详见下方"远程 API 方式"和 references/server-setup.md。
# remote_publish_host: 62.234.16.218
# remote_publish_user: root
# remote_publish_port: 22
# remote_publish_password:
# （通过 sshpass 填写 SSH 密码 — 仅用于受信任的私有服务器；推荐使用 remote_publish_identity_file）
# remote_publish_identity_file: ~/.ssh/id_ed25519
# remote_publish_known_hosts_file: ~/.ssh/known_hosts
# remote_publish_strict_host_key_checking: accept-new
# remote_publish_connect_timeout: 10
# remote_publish_proxy_jump: bastion.example.com
```

明确不支持原始的 `ssh` / `scp` 选项；仅识别上述带类型的键。生产环境推荐使用 SSH 密钥认证（通过 `remote_publish_identity_file`）；密码认证（通过 `remote_publish_password` + sshpass）可用于受信任的私有服务器。

**主题选项**：default、grace、simple、modern。**颜色预设**：blue、green、vermilion、yellow、purple、sky、rose、olive、black、gray、pink、red、orange（或使用十六进制值）。

**值优先级**：CLI 参数 → frontmatter → EXTEND.md（账号级 → 全局）→ 技能默认值。

## 多账号支持

EXTEND.md 支持使用 `accounts:` 块管理多个公众号。当配置了 2 个及以上条目时，工作流会在步骤 0.5 插入账号选择提示（或基于 `default: true` / `--account <alias>` 自动选择）。

完整详情 — 兼容性规则、账号级键、凭据解析、账号级 Chrome 配置文件、CLI 用法 — 见 `references/multi-account.md`。

## 飞行前检查（可选）

首次使用前，可建议运行环境检查（用户可跳过）：

```bash
${BUN_X} {baseDir}/scripts/check-permissions.ts
```

检查项：Chrome、配置文件隔离、Bun、辅助功能、剪贴板、粘贴快捷键、API 凭据、Chrome 冲突。

| 检查失败 | 修复方法 |
|-------------|-----|
| Chrome | 安装 Chrome 或设置 `WECHAT_BROWSER_CHROME_PATH` |
| 配置文件目录 | 在 `post-to-wechat/chrome-profile` 创建独立配置文件 |
| Bun 运行时 | `brew install oven-sh/bun/bun` 或 `npm install -g bun` |
| 辅助功能（macOS） | 系统设置 → 隐私与安全性 → 辅助功能 → 启用终端应用 |
| 剪贴板复制 | 确保 Swift/AppKit 可用（macOS：`xcode-select --install`） |
| 粘贴快捷键（Linux） | 安装 `xdotool`（X11）或 `ydotool`（Wayland） |
| API 凭据 | 按照步骤 2 的引导设置，或在 `.post-to-wechat/.env` 中设置 |
| sshpass（仅密码认证） | 安装：`brew install hudochenkov/sshpass/sshpass`（macOS）/ `apt install sshpass`（Debian/Ubuntu） |

## 贴图发布（图文）

带多张图片（最多 9 张）的短内容发布：

```bash
${BUN_X} {baseDir}/scripts/wechat-browser.ts --markdown article.md --images ./images/
${BUN_X} {baseDir}/scripts/wechat-browser.ts --title "标题" --content "内容" --image img.png --submit
```

详细用法：`references/image-text-posting.md`。

## 文章发布工作流（文章）

```
- [ ] 步骤 0：加载偏好设置（EXTEND.md）
- [ ] 步骤 0.5：确定账号（仅多账号 — 见 references/multi-account.md）
- [ ] 步骤 1：确定输入类型
- [ ] 步骤 2：选择方式并配置凭据
- [ ] 步骤 3：确定主题/颜色并验证元数据
- [ ] 步骤 4：发布到微信
- [ ] 步骤 5：报告完成情况
```

### 步骤 0：加载偏好设置

检查并加载 EXTEND.md（见上方"偏好设置"）。如果未找到，则在任何其他问题之前完成首次设置。解析并缓存供后续步骤使用：`default_theme`、`default_color`、`default_author`、`need_open_comment`、`only_fans_can_comment`。

### 步骤 1：确定输入类型

| 输入 | 检测方式 | 后续操作 |
|-------|-----------|------|
| HTML 文件 | 路径以 `.html` 结尾且文件存在 | 跳至步骤 3 |
| Markdown 文件 | 路径以 `.md` 结尾且文件存在 | 步骤 2 |
| 纯文本 | 非文件路径，或文件不存在 | 保存为 markdown，然后执行步骤 2 |

**纯文本处理**：

1. 生成 slug（取前 2-4 个有意义词汇，短横线连接；中文需翻译为英文作为 slug）。
2. 保存到 `post-to-wechat/YYYY-MM-DD/<slug>.md`（如目录不存在则创建）。
3. 作为 markdown 文件继续处理。

### 步骤 2：选择发布方式并配置

除非在 EXTEND.md 或 CLI 中已指定，否则询问发布方式：

| 方式 | 速度 | 要求 |
|--------|-------|----------|
| `remote-api`（推荐） | 快 | API 凭据 + 一台 SSH 可达且 IP 在微信白名单上的服务器（支持密码或 SSH 密钥认证） |
| `api` | 快 | API 凭据（本机 IP 必须已加入白名单） |
| `browser` | 慢 | Chrome + 已登录的会话 |

**`remote-api` 方式**：微信的"公众号设置 → IP 白名单"通常将 API 访问限制在一两个固定 IP 上。如果你的本机 IP 不在该白名单上，但某台云服务器 IP 在，则可使用 `remote-api`：所有的 Markdown 渲染、图片处理、草稿组装和 HTML 重写仍在本地完成，只有发往 `api.weixin.qq.com` 的外向 HTTPS 调用（token、uploadimg、add_material、draft/add）通过 SSH SOCKS5 动态端口转发（`ssh -N -D`）进行隧道传输，因此微信看到的是远端服务器的源 IP。远端主机上不会写入任何文件；`AppSecret` 不会离开本地进程。远端主机只需要 `sshd` 和外网访问即可 — 无需 Python，无需代理进程。详见下方"远程 API 方式"。密码认证（通过 sshpass）可用于受信任的私有服务器；生产环境推荐使用 SSH 密钥认证（`remote_publish_identity_file`）。

**远程 API 首次配置**：参见 `references/server-setup.md` 完成微信公众号 IP 白名单（添加 `62.234.16.218`）、SSH 可达性验证、sshpass 安装。

**已选择 API 方式 + 缺少凭据** → 按照 `references/api-setup.md` 的引导设置（写入 `.post-to-wechat/.env`）。

### 步骤 3：确定主题/颜色并验证元数据

1. **主题**：CLI `--theme` → EXTEND.md `default_theme` → `default`（首个命中即生效；确定后不要询问）。
2. **颜色**：CLI `--color` → EXTEND.md `default_color` → 省略（使用主题默认值）。
3. **验证元数据**（markdown 使用 frontmatter，HTML 使用 meta 标签）：

| 字段 | 缺失时 → |
|-------|-----------|
| 标题 | 询问，或按回车键根据内容自动生成 |
| 摘要 | Frontmatter `description` → `summary` → 询问或自动生成 |
| 作者 | CLI `--author` → frontmatter `author` → EXTEND.md `default_author` |
| 原文链接 | CLI `--source-url` → frontmatter `sourceUrl`/`contentSourceUrl`/`content_source_url` |

自动生成规则：标题 = 首个 H1/H2 或首句；摘要 = 首段，截断至 120 字符。

4. **封面图片**（API `article_type=news` 必需）：CLI `--cover` → frontmatter（`coverImage` / `featureImage` / `cover` / `image`）→ `imgs/cover.png` → 首张内联图片 → 如果仍然缺失则请求提供。

### 步骤 4：发布

**重要 — 切勿预先将 Markdown 转换为 HTML。** 发布脚本内部会处理转换，且两种方式的图片渲染逻辑不同：API 会将 `<img>` 标签用于上传，浏览器方式则使用占位符进行粘贴替换。传入预转换的 HTML 会破坏其中一种逻辑。

**Markdown 引用默认行为**：对于 Markdown 输入，默认情况下普通外部链接会被转换为底部引用。仅当用户明确希望保留内联链接时使用 `--no-cite`。已有的 HTML 输入保持原样。

**API 方式**（接受 `.md` 或 `.html`）：

```bash
${BUN_X} {baseDir}/scripts/wechat-api.ts <file> --theme <theme> [--color <color>] [--title <title>] [--summary <summary>] [--author <author>] [--cover <cover_path>] [--source-url <url>] [--no-cite]
```

始终传递 `--theme`，即使值是 `default`。仅在用户或 EXTEND.md 明确设置时才传递 `--color`。

**远程 API 方式**（同一脚本，添加 `--remote`）：

```bash
${BUN_X} {baseDir}/scripts/wechat-api.ts <file> --theme <theme> --remote [--remote-host <host>] [--remote-user <user>] [--remote-port <port>] [--remote-identity-file <path>] [--remote-known-hosts-file <path>] [--remote-strict-host-key-checking yes|no|accept-new] [--remote-connect-timeout <s>] [--remote-proxy-jump <spec>]
```

任何 `--remote-*` 标志都隐含 `--remote`。CLI 值优先覆盖 EXTEND.md 中的账号级和全局 `remote_publish_*` 键。设置 `default_publish_method: remote-api` 也会启用远程模式而无需 `--remote`。

**`draft/add` 请求体规则**：
- 接口：`POST https://api.weixin.qq.com/cgi-bin/draft/add?access_token=ACCESS_TOKEN`
- `article_type`：`news`（默认）或 `newspic`
- `news` 类型时，必须包含 `thumb_media_id`（需要封面）
- 即使 CLI 未暴露这些字段，请求体中也要始终包含 `need_open_comment`（默认 `1`）和 `only_fans_can_comment`（默认 `0`）
- `news` 类型时，可选包含 `content_source_url`（原文 URL，显示为"阅读原文"链接，最长 1KB）。通过 `--source-url` CLI 标志或 frontmatter `sourceUrl`/`contentSourceUrl`/`content_source_url` 提供

**浏览器方式**（接受 `--markdown` 或 `--html`）：

```bash
${BUN_X} {baseDir}/scripts/wechat-article.ts --markdown <markdown_file> --theme <theme> [--color <color>] [--no-cite]
${BUN_X} {baseDir}/scripts/wechat-article.ts --html <html_file>
```

### 步骤 5：完成报告

```
微信公众号发布完成！

输入：[type] - [path]
方式：[API | 浏览器]
主题：[theme] [如有 color 则显示]

文章信息：
• 标题：[title]
• 摘要：[summary]
• 图片：[N] 张内联图片
• 评论：[开/关], [仅粉丝/所有人可评]    ← 仅 API 方式

发布结果：
✓ 草稿已保存至微信公众号
• media_id: [media_id]                       ← 仅 API 方式

后续操作（API 方式）：
→ 管理草稿：https://mp.weixin.qq.com（登录后进入「内容管理」→「草稿箱」）

生成的文件：
[• post-to-wechat/YYYY-MM-DD/slug.md（纯文本输入时生成）]
[• slug.html（转换后的 HTML）]
```

## 功能对比

| 功能 | 贴图 | 文章（API） | 文章（远程 API） | 文章（浏览器） |
|---------|:---:|:---:|:---:|:---:|
| 纯文本输入 | ✗ | ✓ | ✓ | ✓ |
| HTML 输入 | ✗ | ✓ | ✓ | ✓ |
| Markdown 输入 | 标题/内容 | ✓ | ✓ | ✓ |
| 多张图片 | ✓（最多 9 张） | ✓（内联） | ✓（内联） | ✓（内联） |
| 主题 | ✗ | ✓ | ✓ | ✓ |
| 自动生成元数据 | ✗ | ✓ | ✓ | ✓ |
| 默认封面回退（`imgs/cover.png`） | ✗ | ✓ | ✓ | ✗ |
| 评论控制 | ✗ | ✓ | ✓ | ✗ |
| 需要 Chrome | ✓ | ✗ | ✗ | ✓ |
| 需要 API 凭据（本机 IP 白名单） | ✗ | ✓ | ✓ | ✗ |
| 需要 SSH 可达的白名单 IP 服务器 | ✗ | ✗ | ✓ | ✗ |
| 速度 | 中等 | 快 | 快 | 慢 |

## 故障排除

| 问题 | 修复方法 |
|-------|-----|
| 缺少 API 凭据 | 按照步骤 2 的引导设置 |
| access_token 错误 | 验证凭据有效且未过期 |
| 未登录（浏览器方式） | 首次运行会打开浏览器 — 扫描二维码登录。设置 `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` 可通过 Telegram 接收二维码图片 |
| 未找到 Chrome | 设置 `WECHAT_BROWSER_CHROME_PATH` |
| 标题/摘要缺失 | 使用自动生成或手动提供 |
| 缺少封面图片 | 在 frontmatter 中添加封面或将 `imgs/cover.png` 放在文章目录下 |
| 评论默认值不对 | 检查 EXTEND.md 中的 `need_open_comment` / `only_fans_can_comment` |
| 粘贴失败 | 检查系统剪贴板权限 |
| `Remote publish host is required` | 在 EXTEND.md 中设置 `--remote-host` 或 `remote_publish_host` |
| `SOCKS proxy on 127.0.0.1:… not ready` | SSH 无法启动隧道 — 检查密钥、主机、`StrictHostKeyChecking`，或使用 `--remote-connect-timeout` |
| 远程发布期间 `ssh exited early` | 验证用户能否以非交互方式 `ssh` 到服务器；如果链路较慢，提高 `--remote-connect-timeout` |
| 远程 API 调用返回 `errcode 40164`（IP 无效） | 远端服务器的出口 IP 不在微信白名单上；在公众号设置 → IP 白名单中添加 |
| `sshpass: command not found` | 安装 sshpass：`brew install hudochenkov/sshpass/sshpass`（macOS）/ `apt install sshpass`（Debian/Ubuntu） |
| 远程发布缺少认证 | 在 EXTEND.md 中设置 `remote_publish_password` 或 `remote_publish_identity_file`，或使用 `--remote-password` / `--remote-identity-file` |
| 旧版配置目录（v1.x 命名）不再读取 | 手动迁移：将旧 `EXTEND.md` 移至 `.post-to-wechat/EXTEND.md` |

## 参考文档

| 文件 | 内容 |
|------|---------|
| `references/image-text-posting.md` | 贴图参数、自动压缩 |
| `references/article-posting.md` | 文章主题、图片处理 |
| `references/multi-account.md` | 多账号兼容性、凭据、Chrome 配置文件、CLI 用法 |
| `references/api-setup.md` | 凭据引导设置 |
| `references/server-setup.md` | 服务器侧设置：IP 白名单、SSH、sshpass |
| `references/config/first-time-setup.md` | 首次 EXTEND.md 设置 |

## 扩展支持

通过 EXTEND.md 进行自定义配置。详见上方"偏好设置"了解路径和支持的选项。
