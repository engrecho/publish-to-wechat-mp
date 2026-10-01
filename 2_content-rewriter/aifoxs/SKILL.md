---
name: aifoxs-ai-detect
description: ContentAny（cn.aifoxs.com）AI 痕迹检测（独立技能）。调用 aifoxs_detect.py 检测文本 AI 指数、逐段 AI/人工分布与内容分析报告。在 gzh-pipeline 中作为阶段②的外部检测环节，也可单独触发（"帮我测下 AI 指数 / AI 痕迹检测"）。
---

# aifoxs AI 痕迹检测（ContentAny）

检测改写稿的 AI 生成痕迹，避免文章因 AI 味过重被平台限流或影响原创认定。

## 1. 检测内容

- **全文 AI 指数**：AI 段占比（`< 20%` 视为"约 80% 概率偏人工"）
- **逐段分布**：每段 🟥AI / 🟦人工 标注与 AI 占比
- **内容分析报告**（正文 ≥500 字时自动生成）：可发布性、恢复流量池、优化 AI 味道、原创性/同质化/限流/敏感违规检测、内容优化建议

## 2. 调用方式

```bash
# 账号池模式（推荐，无需手动管理账号）
python3 aifoxs/aifoxs_detect.py -f work/<slug>/rewritten.md

# 只输出原始 JSON / 高频调用限速
python3 aifoxs/aifoxs_detect.py -f work/<slug>/rewritten.md --json
python3 aifoxs/aifoxs_detect.py -f work/<slug>/rewritten.md --interval 3
```

单账号、自动注册、强制重登等更多参数见 `aifoxs_api_docs.md` 第 6 节。

## 3. 通过标准与迭代

- **通过标准：全文 AI 指数 < 20%**
- 未通过：定位报告中的 🟥AI 段落，回到四层深度改写（重点观点层与句式层），针对性重写后复测
- 复测跟随阶段②的整体重改轮次（最多 3 轮），不单独设限

## 4. 账号池与熔断（脚本自动处理）

| 情况 | 脚本行为 |
|------|---------|
| 本地有可用账号（`.aifoxs_accounts.json`） | 直接复用（token 缓存于 `.aifoxs_session.json`） |
| 账号被风控 / 额度用尽 | 标记状态，自动切换下一个账号 |
| 所有账号不可用 | 自动注册新账号（新号自带免费检测额度） |
| **注册也被风控** | **当日熔断**：不再登录/注册/查询，明确提示用户缓一缓，可建议改用朱雀 AI 检测 |

## 5. 降级

熔断、全部账号不可用或网络异常时：跳过本检测，在自检报告中注明"aifoxs 检测未执行（原因）"，回退到仅本地自检。

## 6. 文件说明

| 文件 | 说明 |
|------|------|
| `aifoxs_detect.py` | 检测脚本（纯 Python 标准库，无第三方依赖） |
| `aifoxs_api_docs.md` | 接口逆向文档（账号体系/检测流程/错误码/脚本完整用法） |
