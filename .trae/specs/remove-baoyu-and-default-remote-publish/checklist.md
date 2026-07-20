# Checklist

## 阶段一：去除 baoyu 引用（代码与配置层）

- [x] SKILL.md frontmatter `name` 为 `post-to-wechat`，无 `baoyu-post-to-wechat` 残留
- [x] SKILL.md `metadata.openclaw.homepage` 已删除或改为占位，无 `JimLiu/baoyu-skills` URL
- [x] `scripts/package.json` 的 `name` 字段为 `post-to-wechat-scripts`
- [x] `scripts/package.json` 的 dependencies 使用 `wechat-chrome-cdp` / `wechat-md` 作为 key，value 形如 `npm:baoyu-chrome-cdp@^0.1.1` / `npm:baoyu-md@^0.1.1`
- [x] `scripts/bun.lock` 已重新生成，`node_modules/wechat-chrome-cdp` 与 `node_modules/wechat-md` 目录存在
- [x] `scripts/md-to-wechat.ts` 中所有 `from "baoyu-md"` 改为 `from "wechat-md"`，`from "baoyu-chrome-cdp/mermaid"` 改为 `from "wechat-chrome-cdp/mermaid"`
- [x] `scripts/cdp.ts` 中 `from 'baoyu-chrome-cdp'` 改为 `from 'wechat-chrome-cdp'`
- [x] `scripts/cdp.ts` 中 `envNames` 数组不含 `BAOYU_CHROME_PROFILE_DIR`，仅含 `WECHAT_BROWSER_PROFILE_DIR`
- [x] `scripts/wechat-socks-http.ts` 中 `User-Agent` 为 `post-to-wechat-api`
- [x] `scripts/wechat-extend-config.ts` 中 EXTEND.md 搜索路径常量为 `.post-to-wechat/EXTEND.md`、`${XDG_CONFIG_HOME:-$HOME/.config}/post-to-wechat/EXTEND.md`、`$HOME/.post-to-wechat/EXTEND.md`
- [x] `scripts/wechat-extend-config.ts` 中 `.env` 路径常量为 `.post-to-wechat/.env`、`$HOME/.post-to-wechat/.env`
- [x] `scripts/wechat-extend-config.ts` 中所有错误提示文本不含 `.baoyu-skills`
- [x] `scripts/wechat-api.ts` 中 usage 文本不含 `.baoyu-skills`
- [x] `scripts/check-permissions.ts` 中 `.env` 路径为 `.post-to-wechat/.env`，输出标题为 `post-to-wechat: Permission & Environment Check`
- [x] `scripts/wechat-extend-config.test.ts` 中路径常量与断言文本均使用 `.post-to-wechat`，无 `.baoyu-skills` / `baoyu-post-to-wechat`
- [x] `bun test scripts/wechat-extend-config.test.ts` 通过
- [x] `bun test scripts/wechat-remote-publish.test.ts` 通过
- [x] `bun test scripts/wechat-socks-http.test.ts` 通过

## 阶段二：去除 baoyu 引用（文档层）

- [x] SKILL.md 中 EXTEND.md 搜索路径表格三行均使用 `.post-to-wechat/` 命名
- [x] SKILL.md 中 `default_author` 示例不含 `宝玉`，留空或使用通用占位
- [x] SKILL.md 中 Remote API publishing 注释段路径示例不含 `.baoyu-skills`
- [x] SKILL.md 第 110 行 chrome-profile 路径示例为 `post-to-wechat/chrome-profile`
- [x] SKILL.md 全文不含 `baoyu` / `宝玉` / `JimLiu` 字样（除 npm alias 必要的底层包名外）
- [x] `references/api-setup.md` 中所有 `.baoyu-skills` 路径替换为 `.post-to-wechat`
- [x] `references/multi-account.md` 中示例账号名不含 `宝玉的技术分享`，alias 不含 `baoyu`
- [x] `references/multi-account.md` 中 `WECHAT_BAOYU_*` 环境变量示例替换为 `WECHAT_MAIN_*`（或等价通用名）
- [x] `references/multi-account.md` 中 `remote_publish_*` 字段列表包含 `remote_publish_password`
- [x] `references/multi-account.md` 中 Security Notes 段落新增「密码认证仅适用于受信任私有服务器」说明
- [x] `references/config/first-time-setup.md` frontmatter `description` 不含 `baoyu-post-to-wechat`
- [x] `references/config/first-time-setup.md` Question 3 中 `remote-api` 标记为 (Recommended)
- [x] `references/config/first-time-setup.md` 保存路径表格使用 `.post-to-wechat/`
- [x] `references/config/first-time-setup.md` EXTEND.md 模板包含 `remote_publish_password:` 字段
- [x] `references/config/first-time-setup.md` EXTEND.md 模板中 `alias` 示例不含 `baoyu`
- [x] `references/config/first-time-setup.md` EXTEND.md 模板预填 `remote_publish_host: 62.234.16.218` 与 `remote_publish_user: root`（注释占位）
- [x] `references/config/first-time-setup.md` After Setup 段落新增「请参阅 references/server-setup.md」提示

## 阶段三：默认走服务器发布（代码层）

- [x] `scripts/wechat-remote-publish.ts` 的 `RemotePublishConfig` interface 包含 `password?: string` 字段
- [x] `scripts/wechat-remote-publish.ts` 的 `NormalizedRemotePublishConfig` interface 包含 `password?: string` 字段
- [x] `normalizeRemoteConfig` 函数在 `identityFile` 存在时忽略 `password`
- [x] `buildSshArgs`（或新 `buildSshCommand`）在 `password` 存在且 `identityFile` 不存在时返回 `["sshpass", "-p", password, "ssh", ...]`
- [x] `startSshTunnel` 的 `console.error` 日志中 password 显示为 `***`，不出现明文
- [x] `startSshTunnel` 在 `identityFile` 与 `password` 均未提供时抛出明确错误，错误信息不含密码但含「set in EXTEND.md or via --remote-password / --remote-identity-file」
- [x] `scripts/wechat-remote-publish.test.ts` 新增 4 个测试：sshpass prefix、identityFile 优先、无认证字段不 emit sshpass、startSshTunnel 抛错
- [x] `bun test scripts/wechat-remote-publish.test.ts` 全部通过
- [x] `scripts/wechat-extend-config.ts` 的 `WechatAccount` / `WechatExtendConfig` / `ResolvedAccount` interface 均包含 `remote_publish_password?: string`
- [x] `resolveAccount` 函数正确合并账号级 `remote_publish_password` 覆盖全局
- [x] `scripts/wechat-extend-config.test.ts` 新增 `resolveAccount merges remote_publish_password from account level` 测试并通过
- [x] `scripts/wechat-api.ts` 的 `CliArgs` interface 包含 `remotePassword?: string`
- [x] `scripts/wechat-api.ts` 的 `parseArgs` 支持 `--remote-password <password>` 解析
- [x] `scripts/wechat-api.ts` usage 文本包含 `--remote-password` 说明
- [x] `scripts/wechat-api.ts` 中 `buildRemoteConfig`（或等价逻辑）正确构造包含 `password` 的 `RemotePublishConfig`，优先级 CLI > 账号级 > 全局
- [x] `wechat-extend-config.ts` 中 `default_publish_method` 默认值为 `"remote-api"`
- [x] 对应单测断言「无配置时 default_publish_method 为 remote-api」通过
- [x] `scripts/check-permissions.ts` 在 `remote_publish_password` 存在时检测 sshpass
- [x] `scripts/check-permissions.ts` 在 sshpass 缺失时输出 warning 但退出码仍为 0
- [x] `scripts/check-permissions.ts` 在 `remote_publish_password` 不存在时不输出任何 sshpass 相关信息

## 阶段四：新增服务器配置文档

- [x] `references/server-setup.md` 文件存在
- [x] `references/server-setup.md` 包含 `## WeChat IP Allowlist` 章节，引导添加 `62.234.16.218`
- [x] `references/server-setup.md` 包含 `## Verify SSH Reachability` 章节
- [x] `references/server-setup.md` 包含 `## Install sshpass (if using password auth)` 章节，覆盖 macOS 与 Linux 安装命令
- [x] `references/server-setup.md` 包含 `## Configure EXTEND.md` 章节，含 `remote_publish_host: 62.234.16.218` 示例
- [x] `references/server-setup.md` 包含 `## Security Notes` 章节，说明密码认证适用范围与 SSH 密钥推荐
- [x] `references/server-setup.md` 包含 `## Troubleshooting` 章节，覆盖 `errcode 40164` / `Permission denied (password)` / `sshpass: command not found`
- [x] SKILL.md 的 References 表格包含 `references/server-setup.md` 行

## 阶段五：集成验证

- [x] `bun test`（在 scripts/ 目录）全套测试通过
- [x] `grep -ri "baoyu" --exclude-dir=node_modules --exclude-dir=.trae --exclude=bun.lock /workspace` 输出仅包含 `package.json` 中的 `npm:baoyu-chrome-cdp@...` 与 `npm:baoyu-md@...`（必要的 alias 底层名）
- [x] `grep -r "宝玉" --exclude-dir=node_modules --exclude-dir=.trae /workspace` 零结果
- [x] `grep -r "JimLiu" --exclude-dir=node_modules --exclude-dir=.trae /workspace` 零结果
- [x] `grep -r "BAOYU_CHROME_PROFILE_DIR" --exclude-dir=node_modules --exclude-dir=.trae /workspace` 零结果
- [x] `grep -r "\.baoyu-skills" --exclude-dir=node_modules --exclude-dir=.trae /workspace` 零结果
- [x] 手动执行 `bun scripts/wechat-api.ts --help`（或等价方式触发 usage）确认 `--remote-password` 出现在 usage 文本中
- [x] 手动模拟首次配置流程，确认 EXTEND.md 写入 `.post-to-wechat/EXTEND.md` 路径
- [x] SKILL.md 的 Troubleshooting 表格包含 `sshpass: command not found` 与 `errcode 40164` 两行
- [x] SKILL.md 的 Pre-flight Check 表格包含 sshpass 检测行
