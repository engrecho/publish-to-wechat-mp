# API 凭据设置

当 `WECHAT_APP_ID` / `WECHAT_APP_SECRET` 缺失时触发引导设置。由文章发布工作流的步骤 2 调用。

## 检测

按以下顺序查找凭据：

1. 环境变量 `WECHAT_APP_ID` / `WECHAT_APP_SECRET`
2. `<cwd>/.post-to-wechat/.env` 中包含 `WECHAT_APP_ID=...`
3. `$HOME/.post-to-wechat/.env` 中包含 `WECHAT_APP_ID=...`

如果都不存在，则运行下方的引导设置。

## 引导设置

向用户展示以下消息并询问保存位置：

```
未找到微信 API 凭据。

获取凭据的步骤：
1. 访问 https://mp.weixin.qq.com
2. 进入：开发 → 基本配置
3. 复制 AppID 和 AppSecret

选择保存位置？
A) 项目级：.post-to-wechat/.env（仅当前项目）
B) 用户级：~/.post-to-wechat/.env（所有项目）
```

用户选择位置后，收集值（优先使用用户输入工具，否则按 SKILL.md 中的用户输入工具规则回退为编号提示）并追加写入：

```
WECHAT_APP_ID=<用户输入>
WECHAT_APP_SECRET=<用户输入>
```

## 多账号变体

如果用户配置了多个账号（EXTEND.md 中有 `accounts:` 块），则改用带前缀的键 — 见 `multi-account.md` → "凭据解析"。
