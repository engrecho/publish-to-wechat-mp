# 多账号支持

通过一份 EXTEND.md 管理多个微信公众号的详细说明。SKILL.md 仅涵盖单账号流程和选择提示 — 当用户配置了 `accounts:` 块、要求发布到特定账号或需要账号级凭据时，请阅读本文件。

## 兼容性

| 条件 | 模式 | 行为 |
|-----------|------|----------|
| 无 `accounts` 块 | 单账号 | 原始行为，无变化 |
| `accounts` 中仅 1 条 | 单账号 | 自动选择，不提示 |
| `accounts` 中 2 条及以上 | 多账号 | 发布前提示选择 |
| `accounts` 中有 `default: true` | 多账号 | 预选默认账号；用户可切换 |

## EXTEND.md 示例

```md
default_theme: default
default_color: blue

accounts:
  - name: 主账号
    alias: main
    default: true
    default_publish_method: remote-api
    default_author:
    need_open_comment: 1
    only_fans_can_comment: 0
    app_id: your_wechat_app_id
    app_secret: your_wechat_app_secret
    remote_publish_host: 62.234.16.218
    remote_publish_user: root
    remote_publish_password: your_ssh_password
  - name: AI工具集
    alias: ai-tools
    default_publish_method: browser
    default_author: AI工具集
    need_open_comment: 1
    only_fans_can_comment: 0
```

## 账号级键与全局键

**账号级**（也接受全局值作为回退）：`default_publish_method`、`default_author`、`need_open_comment`、`only_fans_can_comment`、`app_id`、`app_secret`、`chrome_profile_path`、`remote_publish_host`、`remote_publish_user`、`remote_publish_port`、`remote_publish_password`、`remote_publish_identity_file`、`remote_publish_known_hosts_file`、`remote_publish_strict_host_key_checking`、`remote_publish_connect_timeout`、`remote_publish_proxy_jump`。

**仅全局**（始终共享）：`default_theme`、`default_color`。

## 账号选择（步骤 0.5）

插入在步骤 0（加载 EXTEND.md）和步骤 1（确定输入类型）之间：

```
if 无 accounts 块：
    → 单账号模式（原始行为）
elif accounts.length == 1：
    → 自动选择唯一的账号
elif --account <alias> CLI 参数：
    → 选择匹配的账号
elif 某个账号设置了 default: true：
    → 预选该项，显示："正在使用账号：<name>（--account 切换）"
else：
    → 提示用户从列表中选择
```

## 凭据解析（API 方式）

对于别名是 `{alias}` 的已选账号，按以下顺序尝试（首个命中即生效）：

1. EXTEND.md 账号块中内嵌的 `app_id` / `app_secret`
2. 环境变量 `WECHAT_{ALIAS}_APP_ID` / `WECHAT_{ALIAS}_APP_SECRET`（别名大写，连字符替换为下划线）
3. `.post-to-wechat/.env` 中带前缀的键 `WECHAT_{ALIAS}_APP_ID`
4. `~/.post-to-wechat/.env` 中带前缀的键
5. 回退到无前缀的 `WECHAT_APP_ID` / `WECHAT_APP_SECRET`

### .env 多账号示例

```bash
# 账号：main
WECHAT_MAIN_APP_ID=your_wechat_app_id
WECHAT_MAIN_APP_SECRET=your_wechat_app_secret

# 账号：ai-tools
WECHAT_AI_TOOLS_APP_ID=your_ai_tools_wechat_app_id
WECHAT_AI_TOOLS_APP_SECRET=your_ai_tools_wechat_app_secret
```

## Chrome 配置文件（浏览器方式）

每个账号使用独立的 Chrome 配置文件，避免登录冲突。

| 来源 | 路径 |
|--------|------|
| EXTEND.md 中账号的 `chrome_profile_path` | 原样使用 |
| 根据别名自动生成 | `{shared_profile_parent}/wechat-{alias}/` |
| 单账号回退 | 共享默认配置文件 |

## CLI `--account` 标志

所有发布脚本都接受 `--account <alias>`：

```bash
${BUN_X} {baseDir}/scripts/wechat-api.ts <file> --theme default --account ai-tools
${BUN_X} {baseDir}/scripts/wechat-article.ts --markdown <file> --theme default --account main
${BUN_X} {baseDir}/scripts/wechat-browser.ts --markdown <file> --images ./photos/ --account main
```

## 远程 API 发布

`wechat-api.ts` 支持 `remote-api` 模式，通过 SSH SOCKS5 动态端口转发将微信 API 调用隧道传输到 IP 在微信白名单上的服务器。Markdown 渲染、图片处理、草稿组装和 HTML 重写仍在本地进行；只有发往 `api.weixin.qq.com` 的外向 HTTPS 调用经过隧道。远端主机上不会写入任何文件，`AppSecret` 不会离开本地进程。远端主机只需要 `sshd` 和外网访问。

### 账号级配置

```md
default_theme: default
default_color: blue
default_publish_method: browser   # browser 仍是默认值

accounts:
  - name: 主账号
    alias: main
    default: true
    default_publish_method: remote-api
    default_author:
    app_id: your_wechat_app_id
    app_secret: your_wechat_app_secret
    remote_publish_host: 62.234.16.218
    remote_publish_user: root
    remote_publish_password: your_ssh_password
  - name: AI工具集
    alias: ai-tools
    default_publish_method: remote-api
    default_author: AI工具集
    app_id: your_ai_tools_app_id
    app_secret: your_ai_tools_app_secret
    remote_publish_host: ai-tools-server.example.com
    remote_publish_user: deploy
    remote_publish_port: 22
    remote_publish_identity_file: /home/me/.ssh/id_ed25519
    remote_publish_known_hosts_file: /home/me/.ssh/known_hosts
    remote_publish_strict_host_key_checking: accept-new
```

账号级 `remote_publish_*` 值覆盖顶层全局值。CLI `--remote-*` 标志优先于二者。

### CLI 用法

```bash
# 使用账号自身的 default_publish_method（此处为 remote-api）：
${BUN_X} {baseDir}/scripts/wechat-api.ts <file> --theme default --account ai-tools

# 无论 default_publish_method 是什么，强制启用远程模式：
${BUN_X} {baseDir}/scripts/wechat-api.ts <file> --theme default --account main --remote --remote-host other-server.example.com
```

### 安全注意事项

- 认证同时支持 SSH 密钥（`remote_publish_identity_file`）和密码（`remote_publish_password`，通过 sshpass）。生产环境推荐使用 SSH 密钥；受信任的私有服务器可使用密码。
- 仅读取带类型的 `remote_publish_*` 键；明确不支持原始 `ssh` / `scp` 选项。
- 隧道转发原始 TCP；对 `api.weixin.qq.com` 的 TLS 验证仍由本地进程端到端执行。
- 密码永远不会写入日志、错误消息或 stdout。如果同时设置了 `remote_publish_identity_file` 和 `remote_publish_password`，身份文件优先生效，密码被忽略。
