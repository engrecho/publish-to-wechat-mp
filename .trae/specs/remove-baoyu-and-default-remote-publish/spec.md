# Remove baoyu References & Default to Server-Relayed Publishing Spec

## Why

本仓库代码从 `https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-post-to-wechat` 复制而来，代码与文档中残留 60+ 处 `baoyu` / `宝玉` / `JimLiu` 引用（skill 名、配置目录、npm 包名、User-Agent、示例账号、示例作者、环境变量等），需要全部清除以脱离原仓库品牌。

同时，微信公众号「公众号设置 → IP 白名单」限制了可调用 API 的来源 IP。当前 `remote-api`（SSH SOCKS5 隧道）模式虽已实现但非默认。需要把它设为默认发布方式，并预填用户的腾讯云服务器（62.234.16.218, root，密码认证），让所有 WeChat API 流量都从该服务器出口，从而满足白名单要求。

## What Changes

### 一、去除 baoyu 相关引用

- **BREAKING**：Skill 重命名 `baoyu-post-to-wechat` → `post-to-wechat`（SKILL.md frontmatter `name` 字段、package.json `name` 字段、所有文档标题）
- **BREAKING**：EXTEND.md 配置目录从 `.baoyu-skills/baoyu-post-to-wechat/` 改为 `.post-to-wechat/`，环境变量文件从 `.baoyu-skills/.env` 改为 `.post-to-wechat/.env`（XDG 路径同步调整：`${XDG_CONFIG_HOME:-$HOME/.config}/post-to-wechat/EXTEND.md` 与 `$HOME/.post-to-wechat/EXTEND.md`）
- **BREAKING**：npm 依赖通过 npm alias 重命名导入：`baoyu-chrome-cdp` → `wechat-chrome-cdp`（`"wechat-chrome-cdp": "npm:baoyu-chrome-cdp@^0.1.1"`），`baoyu-md` → `wechat-md`（同上）。代码中所有 `from "baoyu-chrome-cdp"` / `from "baoyu-md"` / `from "baoyu-chrome-cdp/mermaid"` 改为对应新名
- HTTP User-Agent 从 `baoyu-skills-wechat-api` 改为 `post-to-wechat-api`
- 环境变量 `BAOYU_CHROME_PROFILE_DIR` 删除，仅保留 `WECHAT_BROWSER_PROFILE_DIR`
- SKILL.md 中 `homepage` URL（`https://github.com/JimLiu/baoyu-skills#baoyu-post-to-wechat`）删除或改为占位说明
- 所有示例中的 `宝玉` / `宝玉的技术分享` / `alias: baoyu` 替换为通用示例（如 `你的公众号` / `alias: main` / `default_author:` 留空）
- `references/multi-account.md`、`references/api-setup.md`、`references/config/first-time-setup.md` 中所有 `.baoyu-skills/` 路径与 `WECHAT_BAOYU_*` 环境变量示例替换为新命名
- 测试文件 `wechat-extend-config.test.ts`、`check-permissions.ts` 中的路径常量与断言文本同步更新
- `bun.lock` 重新生成以反映新包名与 alias

### 二、默认走腾讯云服务器发布（解决 IP 白名单）

- **BREAKING**：默认 `default_publish_method` 从 `api` 改为 `remote-api`。`references/config/first-time-setup.md` 的首次配置选项中 `remote-api` 标记为 Recommended，`api` 标注「需要本机 IP 在白名单内」
- **BREAKING**：`wechat-remote-publish.ts` 的 `RemotePublishConfig` / `NormalizedRemotePublishConfig` 新增 `password?: string` 字段；`buildSshArgs` 在 `password` 存在时通过 `sshpass -p <password> ssh ...` 调用（仍只绑定 loopback、仍走 SOCKS5、TLS 仍端到端本地校验）
- 新增 `remote_publish_password` EXTEND.md 键与 `--remote-password` CLI 标志（任一 `--remote-*` 标志仍隐含 `--remote`）。优先级：CLI > 账号级 > 全局 > 默认。密码不在任何日志、错误信息、troubleshooting 表格中明文出现
- 首次配置流程在用户选择 `remote-api` 后，提示输入 `remote_publish_host` / `remote_publish_user` / `remote_publish_password`（密码用 masked input），并默认预填 `62.234.16.218` / `root` 作为示例占位
- `references/config/first-time-setup.md` 的 EXTEND.md 模板新增 `remote_publish_password:` 字段；`references/multi-account.md` 的账号级示例同步补充
- SKILL.md 的 Troubleshooting 表格补充：`sshpass: command not found` → 安装 `sshpass`（macOS: `brew install sshpass` 或 `brew install hudochenkov/sshpass/sshpass`；Ubuntu/Debian: `apt install sshpass`）
- SKILL.md 与 `references/multi-account.md` 的「Remote API Method」说明补充：**安全提示——密码认证仅适用于受信任的私有服务器与开发环境；生产环境推荐使用 SSH 密钥（设 `remote_publish_identity_file` 而非 `remote_publish_password`）**
- 新增 `references/server-setup.md` 文档：说明如何把腾讯云服务器 IP（62.234.16.218）添加到微信公众号 IP 白名单（公众号后台 → 设置与开发 → 基本配置 → IP 白名单），以及验证 SSH 可达性的步骤
- 在 SKILL.md「Pre-flight Check」中新增一项：检测 `sshpass` 是否安装（仅当 `remote_publish_password` 配置存在时）

### 三、配置优先级与兼容性

- 既有 `remote_publish_identity_file`（SSH 密钥）配置完全保留并优先生效：若同时配置了 `identity_file` 与 `password`，使用 `identity_file` 并忽略 `password`
- `default_publish_method: api` / `browser` 仍然可用，只是不再是默认推荐
- 已存在的 `.baoyu-skills/` 旧目录**不自动迁移**——在 SKILL.md Troubleshooting 中提示用户手动迁移到 `.post-to-wechat/`，避免静默破坏既有配置

## Impact

- **Affected specs**: 无（本项目无既有 spec 文档，本次为首个 spec）
- **Affected code**:
  - `SKILL.md` — frontmatter、homepage、所有路径、示例、Troubleshooting、首次配置引用
  - `scripts/package.json` — name 字段、dependencies alias
  - `scripts/bun.lock` — 重新生成
  - `scripts/wechat-remote-publish.ts` — `RemotePublishConfig` / `NormalizedRemotePublishConfig` 新增 `password`，`buildSshArgs` 支持 sshpass
  - `scripts/wechat-remote-publish.test.ts` — 新增 sshpass 路径测试，更新既有测试断言
  - `scripts/wechat-socks-http.ts` — User-Agent 改名
  - `scripts/wechat-extend-config.ts` — 路径常量改名、新增 `remote_publish_password` 解析
  - `scripts/wechat-extend-config.test.ts` — 路径断言、新字段测试
  - `scripts/wechat-api.ts` — 新增 `--remote-password` CLI 标志、usage 文本、`buildRemoteConfig` 透传 password
  - `scripts/check-permissions.ts` — `.baoyu-skills/.env` → `.post-to-wechat/.env`、输出标题改名、新增 sshpass 检测
  - `scripts/md-to-wechat.ts` — `from "baoyu-md"` → `from "wechat-md"`，`from "baoyu-chrome-cdp/mermaid"` → `from "wechat-chrome-cdp/mermaid"`
  - `scripts/cdp.ts` — `from "baoyu-chrome-cdp"` → `from "wechat-chrome-cdp"`，删除 `BAOYU_CHROME_PROFILE_DIR` 环境变量
  - `references/api-setup.md` — 路径替换
  - `references/multi-account.md` — 路径、示例账号、环境变量名、remote_publish_password 说明
  - `references/config/first-time-setup.md` — frontmatter description、默认方法、EXTEND.md 模板新增 password 字段、保存路径替换
  - `references/server-setup.md` — **新增**
  - `README.md` — 当前为空，本次仍保持空（用户未要求创建 README）
- **Affected external systems**:
  - 用户的微信公众号「IP 白名单」需添加 `62.234.16.218`（文档说明，不在代码内执行）
  - 用户本地机器需安装 `sshpass`（若使用密码认证）

## ADDED Requirements

### Requirement: Skill 与配置目录改名

系统 SHALL 将 skill 标识符从 `baoyu-post-to-wechat` 重命名为 `post-to-wechat`，所有 EXTEND.md 配置目录从 `.baoyu-skills/baoyu-post-to-wechat/` 改为 `.post-to-wechat/`，所有 `.env` 文件路径从 `.baoyu-skills/.env` 改为 `.post-to-wechat/.env`。XDG 路径与 home 路径同步调整。代码、文档、测试中断言的字符串全部同步更新，不留任何 `baoyu` 残留（除 npm alias 底层依赖名 `npm:baoyu-chrome-cdp@...` 在 package.json / bun.lock 中保留，因为这是底层包的真实名字）。

#### Scenario: 用户首次运行 skill

- **WHEN** 用户在干净环境首次调用 `post-to-wechat` skill
- **THEN** 系统在 `<cwd>/.post-to-wechat/EXTEND.md`、`${XDG_CONFIG_HOME:-$HOME/.config}/post-to-wechat/EXTEND.md`、`$HOME/.post-to-wechat/EXTEND.md` 三个路径依次查找 EXTEND.md
- **AND** 均未找到时进入首次配置流程，写入 `<cwd>/.post-to-wechat/EXTEND.md` 或 `$HOME/.post-to-wechat/EXTEND.md`
- **AND** `.env` 文件（如需要）写入 `.post-to-wechat/.env`

#### Scenario: 旧配置目录不自动迁移

- **WHEN** 用户存在历史 `.baoyu-skills/baoyu-post-to-wechat/EXTEND.md` 但无 `.post-to-wechat/EXTEND.md`
- **THEN** 系统不读取旧路径，按"首次配置"处理
- **AND** SKILL.md Troubleshooting 表格提示用户手动迁移：`mv .baoyu-skills/baoyu-post-to-wechat/EXTEND.md .post-to-wechat/EXTEND.md`

### Requirement: npm 依赖通过 alias 重命名

系统 SHALL 通过 npm alias 机制在 package.json 中将 `baoyu-chrome-cdp` 重命名为 `wechat-chrome-cdp`、`baoyu-md` 重命名为 `wechat-md`，使代码中所有 `import ... from "baoyu-chrome-cdp*"` / `from "baoyu-md*"` 改写为新名。底层包仍从 npm registry 拉取原包，但应用代码与文档中不再出现 `baoyu` 字样。

#### Scenario: 安装依赖

- **WHEN** 执行 `bun install` 或 `npm install`
- **THEN** package.json 中的 `"wechat-chrome-cdp": "npm:baoyu-chrome-cdp@^0.1.1"` 与 `"wechat-md": "npm:baoyu-md@^0.1.1"` 被解析
- **AND** `node_modules/wechat-chrome-cdp/` 与 `node_modules/wechat-md/` 目录被创建（指向原包内容）
- **AND** 代码中 `from "wechat-chrome-cdp"` 与 `from "wechat-md"` 正常 resolve

### Requirement: 默认发布方式改为 remote-api

系统 SHALL 将 EXTEND.md 中未指定 `default_publish_method` 时的默认值从 `api` 改为 `remote-api`。首次配置流程的「Default Publishing Method」选项中 `remote-api` 标记为 (Recommended)。

#### Scenario: 用户首次配置未显式选择

- **WHEN** 用户首次配置时未选择 publish method 或选择 "use defaults"
- **THEN** EXTEND.md 写入 `default_publish_method: remote-api`
- **AND** 后续发布流程使用 SSH SOCKS5 隧道

#### Scenario: 用户显式选择 api 或 browser

- **WHEN** 用户在首次配置或 EXTEND.md 中显式设置 `default_publish_method: api` 或 `browser`
- **THEN** 系统尊重该选择，使用对应方式发布
- **AND** Troubleshooting 提示：若选 `api` 需本机 IP 在 WeChat 白名单内

### Requirement: SSH 密码认证支持

系统 SHALL 在 `RemotePublishConfig` / `NormalizedRemotePublishConfig` 中新增 `password?: string` 字段，在 `buildSshArgs` 中当 `password` 存在且 `identityFile` 不存在时，通过 `sshpass -p <password>` 前缀调用 ssh。密码不得出现在任何日志、错误信息、stdout 输出中。

#### Scenario: 仅配置密码

- **WHEN** EXTEND.md 设置 `remote_publish_password: mypass` 且未设置 `remote_publish_identity_file`
- **THEN** `buildSshArgs` 返回的命令前缀为 `sshpass -p mypass`，后接原有 ssh 参数
- **AND** `[wechat-remote-publish] Starting SSH SOCKS5 tunnel: ssh ...` 日志中不出现 `mypass`，仅显示 `sshpass -p *** ssh ...`

#### Scenario: 同时配置密码与密钥

- **WHEN** EXTEND.md 同时设置 `remote_publish_password` 与 `remote_publish_identity_file`
- **THEN** 系统优先使用 `identityFile`，忽略 `password`
- **AND** 日志显示 `ssh -i <identityFile> ...`，不出现 sshpass

#### Scenario: 密码错误

- **WHEN** 配置的密码不正确，ssh 认证失败
- **THEN** `waitForSocksReady` 超时后抛出 `SOCKS proxy on 127.0.0.1:... not ready within 10000ms` 错误
- **AND** 错误信息附带的 ssh stderr 末 5 行中可能包含 `Permission denied (password)` 但**不**包含用户密码本身

### Requirement: remote_publish_password 配置键与 --remote-password CLI 标志

系统 SHALL 在 EXTEND.md 中支持 `remote_publish_password` 键（账号级与全局均支持），在 `wechat-api.ts` 中支持 `--remote-password <password>` CLI 标志。优先级：CLI > 账号级 > 全局。

#### Scenario: CLI 标志覆盖配置

- **WHEN** EXTEND.md 设置 `remote_publish_password: config_pass` 且 CLI 传入 `--remote-password cli_pass`
- **THEN** 系统使用 `cli_pass` 作为 SSH 密码
- **AND** `cli_pass` 不被记录到任何持久化日志

#### Scenario: 配置缺失但启用了 remote 模式

- **WHEN** 用户启用 `--remote` 但既未配置 `remote_publish_password` 也未配置 `remote_publish_identity_file`
- **THEN** 系统抛出明确错误：`Remote publish requires either remote_publish_password or remote_publish_identity_file (set in EXTEND.md or via --remote-password / --remote-identity-file).`
- **AND** 不尝试启动 ssh（避免卡在交互式密码提示）

### Requirement: 预填腾讯云服务器默认值

系统 SHALL 在首次配置流程的 `remote-api` 选项 description 中提示「默认服务器：62.234.16.218 (root)，可在 EXTEND.md 中修改」，并在 EXTEND.md 模板中预填 `remote_publish_host: 62.234.16.218` 与 `remote_publish_user: root` 作为注释占位（用户需手动取消注释并填密码）。

#### Scenario: 用户选 remote-api 并接受默认服务器

- **WHEN** 用户在首次配置中选择 `remote-api` 并在 host 提示时直接回车
- **THEN** EXTEND.md 写入 `remote_publish_host: 62.234.16.218` 与 `remote_publish_user: root`
- **AND** `remote_publish_password:` 留空，提示用户手填
- **AND** Troubleshooting 提示：需在微信公众号后台 IP 白名单中添加 `62.234.16.218`

### Requirement: 服务器配置文档

系统 SHALL 新增 `references/server-setup.md` 文档，说明：(1) 如何在微信公众号后台添加 `62.234.16.218` 到 IP 白名单；(2) 如何验证 SSH 可达性（`ssh root@62.234.16.218`）；(3) 如何安装 sshpass；(4) 安全注意事项（密码认证仅适用于受信任私有服务器，推荐生产环境用 SSH 密钥）。

#### Scenario: 用户首次配置时被引导阅读

- **WHEN** 用户首次选择 `remote-api` 后
- **THEN** 首次配置流程在写入 EXTEND.md 后提示：「请参阅 references/server-setup.md 完成服务器侧配置（IP 白名单、SSH 可达性、sshpass 安装）」

### Requirement: sshpass 环境检测

系统 SHALL 在 `check-permissions.ts` 中新增 sshpass 检测项：仅当 EXTEND.md 中存在 `remote_publish_password` 时检测，缺失则提示 `brew install sshpass` 或 `apt install sshpass`。不强制阻断（仅 warning）。

#### Scenario: 配置了密码但未装 sshpass

- **WHEN** 用户配置了 `remote_publish_password` 但本地未安装 `sshpass`
- **THEN** `check-permissions.ts` 输出 `⚠ sshpass not found (required for password-based SSH auth). Install: brew install sshpass / apt install sshpass`
- **AND** 退出码仍为 0（仅 warning，不阻断发布）

## MODIFIED Requirements

### Requirement: HTTP User-Agent

`wechat-socks-http.ts` 中默认 `User-Agent` header 从 `baoyu-skills-wechat-api` 改为 `post-to-wechat-api`。

### Requirement: Chrome profile 环境变量

`scripts/cdp.ts` 中 `envNames: ['BAOYU_CHROME_PROFILE_DIR', 'WECHAT_BROWSER_PROFILE_DIR']` 改为 `envNames: ['WECHAT_BROWSER_PROFILE_DIR']`，删除 `BAOYU_CHROME_PROFILE_DIR`。

### Requirement: Troubleshooting 表格

SKILL.md 的 Troubleshooting 表格新增两行：
- `sshpass: command not found` → 安装 sshpass（macOS: `brew install hudochenkov/sshpass/sshpass`；Ubuntu/Debian: `apt install sshpass`）
- `Remote API call returns errcode 40164 (invalid IP)` → 在微信公众号「设置与开发 → 基本配置 → IP 白名单」添加远端服务器出口 IP（如 `62.234.16.218`）

### Requirement: Pre-flight Check 表格

SKILL.md 的 Pre-flight Check 表格新增一行：
- sshpass（仅当配置了 `remote_publish_password`）→ `brew install sshpass` / `apt install sshpass`

## REMOVED Requirements

### Requirement: BAOYU_CHROME_PROFILE_DIR 环境变量

**Reason**: 与 `WECHAT_BROWSER_PROFILE_DIR` 重复且带 baoyu 品牌，删除以简化。
**Migration**: 依赖 `BAOYU_CHROME_PROFILE_DIR` 的用户改用 `WECHAT_BROWSER_PROFILE_DIR`。

### Requirement: 旧路径 `.baoyu-skills/` 自动读取

**Reason**: 路径名变更，不自动读取以避免混淆。
**Migration**: 用户手动迁移 `mv .baoyu-skills/baoyu-post-to-wechat/EXTEND.md .post-to-wechat/EXTEND.md` 与 `mv .baoyu-skills/.env .post-to-wechat/.env`。
