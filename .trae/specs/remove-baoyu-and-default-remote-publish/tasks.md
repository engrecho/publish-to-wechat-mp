# Tasks

## 阶段一：去除 baoyu 引用（代码与配置层）

- [x] Task 1: 重命名 skill 与 package.json
  - [x] SubTask 1.1: `SKILL.md` frontmatter `name: baoyu-post-to-wechat` → `name: post-to-wechat`；删除 `metadata.openclaw.homepage` 行或改为 `# homepage: <your-repo-url>` 占位
  - [x] SubTask 1.2: `scripts/package.json` 中 `"name": "baoyu-post-to-wechat-scripts"` → `"name": "post-to-wechat-scripts"`；新增 `wechat-chrome-cdp` / `wechat-md` 的 npm alias，删除 `baoyu-chrome-cdp` / `baoyu-md` 旧条目
  - [x] SubTask 1.3: 在 `scripts/` 目录运行 `rm -rf node_modules bun.lock && bun install` 重新生成 lockfile（验证 alias 生效）

- [x] Task 2: 更新代码中的 import 与字符串常量
  - [x] SubTask 2.1: `scripts/md-to-wechat.ts` 中 `from "baoyu-md"` → `from "wechat-md"`、`from "baoyu-chrome-cdp/mermaid"` → `from "wechat-chrome-cdp/mermaid"`
  - [x] SubTask 2.2: `scripts/cdp.ts` 中 `from 'baoyu-chrome-cdp'` → `from 'wechat-chrome-cdp'`，`envNames: ['BAOYU_CHROME_PROFILE_DIR', 'WECHAT_BROWSER_PROFILE_DIR']` → `envNames: ['WECHAT_BROWSER_PROFILE_DIR']`
  - [x] SubTask 2.3: `scripts/wechat-socks-http.ts` 第 107 行 `User-Agent: baoyu-skills-wechat-api` → `User-Agent: post-to-wechat-api`
  - [x] SubTask 2.4: `scripts/wechat-extend-config.ts` 中 EXTEND.md 搜索路径常量 `.baoyu-skills/baoyu-post-to-wechat/EXTEND.md` → `.post-to-wechat/EXTEND.md`，XDG 与 home 路径同步；`.baoyu-skills/.env` → `.post-to-wechat/.env`；错误提示文本中的 `.baoyu-skills` 同步替换
  - [x] SubTask 2.5: `scripts/wechat-api.ts` 第 518-519 行 usage 文本中 `.baoyu-skills/.env` → `.post-to-wechat/.env`
  - [x] SubTask 2.6: `scripts/check-permissions.ts` 第 190-191 行 `.baoyu-skills/.env` → `.post-to-wechat/.env`；第 224 行输出标题 `baoyu-post-to-wechat: Permission & Environment Check` → `post-to-wechat: Permission & Environment Check`

- [x] Task 3: 更新测试文件中的路径断言
  - [x] SubTask 3.1: `scripts/wechat-extend-config.test.ts` 第 75、81、120、306 行：`.baoyu-skills` → `.post-to-wechat`、`baoyu-post-to-wechat` → `post-to-wechat`
  - [x] SubTask 3.2: 运行 `bun test scripts/wechat-extend-config.test.ts` 验证通过
  - [x] SubTask 3.3: 运行 `bun test scripts/wechat-remote-publish.test.ts` 与 `scripts/wechat-socks-http.test.ts` 验证未受影响

## 阶段二：去除 baoyu 引用（文档层）

- [x] Task 4: 更新 SKILL.md 全文
  - [x] SubTask 4.1: 第 2 行 frontmatter `name`（已在 Task 1.1 处理，此处仅校验）
  - [x] SubTask 4.2: 第 48-50 行 EXTEND.md 搜索路径表格三行全部替换为 `.post-to-wechat/EXTEND.md`、`${XDG_CONFIG_HOME:-$HOME/.config}/post-to-wechat/EXTEND.md`、`$HOME/.post-to-wechat/EXTEND.md`
  - [x] SubTask 4.3: 第 68 行 `default_author: 宝玉` → `default_author:` 留空（注释说明「填写你的作者名」）
  - [x] SubTask 4.4: 第 73-82 行 `# Remote API publishing` 注释块中所有 `.baoyu-skills` 路径示例替换；新增 `# remote_publish_password:` 注释行并附安全说明
  - [x] SubTask 4.5: 第 110 行 `Shared profile at baoyu-skills/chrome-profile` → `Shared profile at post-to-wechat/chrome-profile`
  - [x] SubTask 4.6: 第 115、168 行 `.baoyu-skills/.env` → `.post-to-wechat/.env`
  - [x] SubTask 4.7: 第 162-167 行方法对比表中 `api` 行的 Requires 列改为 `API credentials (本机 IP allowlisted)`；`remote-api` 行改为 Recommended
  - [x] SubTask 4.8: 第 170 行「Remote API Method」段落补充密码认证说明与安全提示
  - [x] SubTask 4.9: 第 281-284 行 Troubleshooting 表格新增 `sshpass: command not found` 与 `errcode 40164` 两行（其中 40164 行已存在则只补充腾讯云 IP 示例）
  - [x] SubTask 4.10: 「Pre-flight Check」表格新增 `sshpass` 检测行
  - [x] SubTask 4.11: 「References」表格新增 `references/server-setup.md` 行
  - [x] SubTask 4.12: 通读 SKILL.md 全文确认无 `baoyu` / `宝玉` / `JimLiu` 残留

- [x] Task 5: 更新 references/api-setup.md
  - [x] SubTask 5.1: 第 10-11 行 `<cwd>/.baoyu-skills/.env` → `<cwd>/.post-to-wechat/.env`，`$HOME/.baoyu-skills/.env` → `$HOME/.post-to-wechat/.env`
  - [x] SubTask 5.2: 第 28-29 行 `A) Project-level: .baoyu-skills/.env` → `A) Project-level: .post-to-wechat/.env`，`B) User-level: ~/.baoyu-skills/.env` → `B) User-level: ~/.post-to-wechat/.env`

- [x] Task 6: 更新 references/multi-account.md
  - [x] SubTask 6.1: 第 21-25 行示例账号 `宝玉的技术分享` / `alias: baoyu` / `default_author: 宝玉` → `你的公众号` / `alias: main` / `default_author:` 留空
  - [x] SubTask 6.2: 第 40 行 `remote_publish_*` 字段列表新增 `remote_publish_password`
  - [x] SubTask 6.3: 第 67-68 行 `.baoyu-skills/.env` 与 `~/.baoyu-skills/.env` → `.post-to-wechat/.env` 与 `~/.post-to-wechat/.env`
  - [x] SubTask 6.4: 第 74-81 行 `.env` 多账号示例：`# Account: baoyu` → `# Account: main`，`WECHAT_BAOYU_APP_ID` → `WECHAT_MAIN_APP_ID`，`WECHAT_BAOYU_APP_SECRET` → `WECHAT_MAIN_APP_SECRET`
  - [x] SubTask 6.5: 第 99-100、145 行 `--account baoyu` → `--account main`
  - [x] SubTask 6.6: 第 105 行 Remote API 段落补充密码认证说明
  - [x] SubTask 6.7: 第 115-119 行第二个示例账号同样替换 `宝玉` / `baoyu`
  - [x] SubTask 6.8: 「Security Notes」段落新增「密码认证仅适用于受信任私有服务器」一条

- [x] Task 7: 更新 references/config/first-time-setup.md
  - [x] SubTask 7.1: 第 3 行 frontmatter `description: First-time setup flow for baoyu-post-to-wechat preferences` → `description: First-time setup flow for post-to-wechat preferences`
  - [x] SubTask 7.2: 第 89-93 行 Question 3「Default Publishing Method」选项中 `remote-api` 标为 (Recommended)，`api` 描述补充「需要本机 IP 在 WeChat 白名单内」；选 remote-api 后的提示文本新增「默认服务器：62.234.16.218 (root)，可在 EXTEND.md 中修改」
  - [x] SubTask 7.3: 第 138-140 行 `Project (.baoyu-skills/)` → `Project (.post-to-wechat/)`，`User (~/.baoyu-skills/)` → `User (~/.post-to-wechat/)`
  - [x] SubTask 7.4: 第 147-148 行保存路径表格 `.baoyu-skills/baoyu-post-to-wechat/EXTEND.md` → `.post-to-wechat/EXTEND.md`
  - [x] SubTask 7.5: 第 164-209 行 EXTEND.md 模板：所有 `.baoyu-skills` 路径替换；新增 `remote_publish_password:` 字段（注释说明）；`alias: [short key, e.g. "baoyu"]` → `alias: [short key, e.g. "main"]`；预填 `remote_publish_host: 62.234.16.218` 与 `remote_publish_user: root`（注释占位）
  - [x] SubTask 7.6: 在「After Setup」段落新增第 5 步：「如选 remote-api，请参阅 references/server-setup.md 完成服务器侧配置」

## 阶段三：默认走服务器发布（代码层）

- [x] Task 8: 扩展 RemotePublishConfig 支持 password
  - [x] SubTask 8.1: `scripts/wechat-remote-publish.ts` 的 `RemotePublishConfig` interface 新增 `password?: string` 字段
  - [x] SubTask 8.2: `NormalizedRemotePublishConfig` interface 同步新增 `password?: string` 字段
  - [x] SubTask 8.3: `normalizeRemoteConfig` 函数：当 `identityFile` 存在时忽略 `password`（置 undefined）；当 `identityFile` 不存在且 `password` 也未提供时，**不**在 `normalizeRemoteConfig` 抛错（延后到 `startSshTunnel` 抛），以保证 `normalizeRemoteConfig` 仅做格式校验
  - [x] SubTask 8.4: 修改 `buildSshArgs` 签名为返回 `{ command: string; args: string[] }`（前缀可能是 sshpass）；或者新增 `buildSshCommand` 函数返回完整命令数组。当 `password` 存在时返回 `["sshpass", "-p", password, "ssh", ...originalArgs]`，否则返回 `["ssh", ...originalArgs]`
  - [x] SubTask 8.5: 修改 `startSshTunnel` 中 `spawn` 调用：使用新的命令数组；日志 `console.error` 输出时将 password 替换为 `***`（仅显示 `sshpass -p *** ssh ...`）
  - [x] SubTask 8.6: 在 `startSshTunnel` 启动 ssh 前新增前置检查：若 `identityFile` 与 `password` 均未提供，直接抛 `Remote publish requires either remote_publish_password or remote_publish_identity_file (set in EXTEND.md or via --remote-password / --remote-identity-file).`，避免卡在交互式密码提示
  - [x] SubTask 8.7: 更新 `scripts/wechat-remote-publish.test.ts`：
    - 既有测试断言 `buildSshArgs` 返回值若改为新结构则同步更新
    - 新增测试 `buildSshArgs uses sshpass prefix when password is set`
    - 新增测试 `buildSshArgs ignores password when identityFile is also set`
    - 新增测试 `buildSshArgs emits no sshpass when neither password nor identityFile`（验证此前置由 startSshTunnel 抛错）
    - 新增测试 `startSshTunnel throws when neither password nor identityFile is provided`（mock spawn，仅验证抛错）
  - [x] SubTask 8.8: 运行 `bun test scripts/wechat-remote-publish.test.ts` 验证通过

- [x] Task 9: 扩展 wechat-extend-config.ts 解析 remote_publish_password
  - [x] SubTask 9.1: `WechatAccount` interface 新增 `remote_publish_password?: string`
  - [x] SubTask 9.2: `WechatExtendConfig` interface（顶层）同步新增 `remote_publish_password?: string`
  - [x] SubTask 9.3: `ResolvedAccount` interface 同步新增 `remote_publish_password?: string`
  - [x] SubTask 9.4: `resolveAccount` 函数中合并逻辑：账号级 `remote_publish_password` 覆盖全局；CLI 不在此层处理
  - [x] SubTask 9.5: 在配置解析层为 `remote_publish_password` 添加 redaction：若 `loadWechatExtendConfig` 在 debug 模式打印配置，password 必须显示为 `***`（检查现有代码是否有 debug 日志，如无则跳过）
  - [x] SubTask 9.6: 更新 `scripts/wechat-extend-config.test.ts`：新增测试 `resolveAccount merges remote_publish_password from account level`

- [x] Task 10: 扩展 wechat-api.ts CLI 支持 --remote-password
  - [x] SubTask 10.1: `CliArgs` interface 新增 `remotePassword?: string`
  - [x] SubTask 10.2: `parseArgs` 函数新增 `--remote-password <password>` 解析（与 `--remote-host` 等同模式），任一 `--remote-*` 标志仍隐含 `args.remote = true`
  - [x] SubTask 10.3: usage 文本（第 491 行附近）新增一行：`--remote-password <pw>   SSH password (via sshpass). Use only on trusted private servers.`
  - [x] SubTask 10.4: `buildRemoteConfig` 函数（若存在）或等价逻辑：CLI `remotePassword` 优先于 `resolved.remote_publish_password`，构造 `RemotePublishConfig` 时透传 `password` 字段
  - [x] SubTask 10.5: 验证 `useRemote` 分支调用 `withSshTunnel` 时传入的 config 包含 `password`（如未配置则 `undefined`，由 `startSshTunnel` 抛错）

- [x] Task 11: 默认 default_publish_method 改为 remote-api
  - [x] SubTask 11.1: 在 `wechat-extend-config.ts` 中找到 `default_publish_method` 的默认值（常量或 fallback），从 `"api"` 改为 `"remote-api"`
  - [x] SubTask 11.2: 验证 `wechat-api.ts` 中 `useRemote = args.remote || resolved.default_publish_method === "remote-api"` 逻辑在新默认下正确触发
  - [x] SubTask 11.3: 更新对应单测：原本断言「无配置时 default_publish_method 为 api」的测试改为 remote-api

- [x] Task 12: check-permissions.ts 新增 sshpass 检测
  - [x] SubTask 12.1: 在 `check-permissions.ts` 中加载 EXTEND.md（若已加载则复用），检查 `remote_publish_password` 是否存在
  - [x] SubTask 12.2: 若存在，调用 `which sshpass` 或 `command -v sshpass` 检测；缺失则输出 `⚠ sshpass not found (required for password-based SSH auth). Install: brew install hudochenkov/sshpass/sshpass (macOS) / apt install sshpass (Debian/Ubuntu)`，退出码仍为 0
  - [x] SubTask 12.3: 若不存在 `remote_publish_password`，跳过检测（不输出任何 sshpass 相关信息）

## 阶段四：新增服务器配置文档

- [x] Task 13: 创建 references/server-setup.md
  - [x] SubTask 13.1: 文档结构：
    - 标题：`# Server Setup for Remote API Publishing`
    - 章节 1：`## WeChat IP Allowlist` — 引导用户登录 https://mp.weixin.qq.com → 设置与开发 → 基本配置 → IP 白名单 → 添加 `62.234.16.218`
    - 章节 2：`## Verify SSH Reachability` — `ssh root@62.234.16.218` 应能非交互登录（密钥）或交互输入密码登录
    - 章节 3：`## Install sshpass (if using password auth)` — macOS: `brew install hudochenkov/sshpass/sshpass`；Ubuntu/Debian: `apt install sshpass`；验证：`sshpass -V`
    - 章节 4：`## Configure EXTEND.md` — 示例 EXTEND.md 片段（含 `remote_publish_host: 62.234.16.218` / `remote_publish_user: root` / `remote_publish_password: <your-password>`），并提示也可改用 `remote_publish_identity_file`
    - 章节 5：`## Security Notes` — 密码认证仅适用于受信任私有服务器；推荐生产环境用 SSH 密钥（`ssh-keygen` + `ssh-copy-id root@62.234.16.218`）；密码不应提交到 git（建议 `.gitignore` 包含 `.post-to-wechat/.env` 与 `.post-to-wechat/EXTEND.md` 或使用全局 `~/.post-to-wechat/`）
    - 章节 6：`## Troubleshooting` — `errcode 40164` / `Permission denied (password)` / `sshpass: command not found` 三个常见问题与解法

## 阶段五：集成验证

- [x] Task 14: 全量测试与 grep 验证
  - [x] SubTask 14.1: 在 `scripts/` 运行 `bun test` 全套测试，确认全部通过
  - [x] SubTask 14.2: 在 `/workspace` 运行 `grep -ri "baoyu" --exclude-dir=node_modules --exclude-dir=.trae --exclude=bun.lock .`，确认仅剩 `package.json` 中的 `npm:baoyu-chrome-cdp@...` 与 `npm:baoyu-md@...` alias 底层引用（这些是必要的，因为 npm alias 语法要求底层包名）
  - [x] SubTask 14.3: 在 `/workspace` 运行 `grep -r "宝玉" --exclude-dir=node_modules --exclude-dir=.trae .`，确认零结果
  - [x] SubTask 14.4: 在 `/workspace` 运行 `grep -r "JimLiu" --exclude-dir=node_modules --exclude-dir=.trae .`，确认零结果
  - [x] SubTask 14.5: 在 `/workspace` 运行 `grep -r "BAOYU_CHROME_PROFILE_DIR" --exclude-dir=node_modules --exclude-dir=.trae .`，确认零结果
  - [x] SubTask 14.6: 在 `/workspace` 运行 `grep -r "\.baoyu-skills" --exclude-dir=node_modules --exclude-dir=.trae .`，确认零结果
  - [x] SubTask 14.7: 手动模拟首次配置流程，确认写入 `.post-to-wechat/EXTEND.md` 路径正确
  - [x] SubTask 14.8: 手动执行 `bun scripts/wechat-api.ts --help`（或等价 usage 触发方式），确认 `--remote-password` 出现在 usage 文本中

# Task Dependencies

- Task 1 → Task 2, Task 3（重命名后才能改 import 与测试）
- Task 2 → Task 14（代码改完才能跑测试与 grep）
- Task 4, 5, 6, 7 可并行（文档独立）
- Task 8 → Task 9（RemotePublishConfig 先扩展，extend-config 才能引用 password 字段类型）— 实际上两者独立，可并行，但建议 Task 8 先行以确立类型定义
- Task 9 → Task 10（extend-config 解析 password 后，CLI 才能从 resolved config 取值）
- Task 10 → Task 11（CLI 与 default 都改完后才能完整验证 useRemote 流程）
- Task 8 → Task 12（check-permissions 检测 sshpass 依赖 remote_publish_password 配置存在，需先完成 Task 9 才能读取该字段）
- Task 13 可与 Task 4-7 并行（独立新文件）
- Task 14 依赖所有前序任务完成

# Parallelizable Work

- 文档组（Task 4, 5, 6, 7, 13）可一次性派 5 个 sub-agent 并行处理
- 代码组（Task 8, 9, 10, 11, 12）有依赖链，建议串行或在 Task 8 完成后派 Task 9+10 并行、Task 11+12 并行
- 阶段一（Task 1-3）必须先于阶段二/三/四完成
