# ContentAny (cn.aifoxs.com) AI 检测接口文档

> 本文档通过抓取 `https://cn.aifoxs.com/ai-detect` 前端 JS 代码逆向 + 真实接口请求验证得出。
> 验证账号：邮箱注册 + 邮箱登录均实测通过（新注册账号自带 AI 检测额度，每天免费检测）。
>
> **更新（2026-08-31）**：配套脚本 `aifoxs_detect.py` 已加入**账号池自动管理**（本地缓存账号 / 额度用尽自动注册 / 风控自动切换 / 注册被风控当日熔断）。完整用法见第 6 节。

---

## 0. 总体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│  账号体系                                                        │
│  注册: POST /v1/api/user/add              (form, 无验证码)        │
│  登录: POST /v1/api/user/login            (json, 返回 JWT token)  │
│  鉴权: 请求头 token: <JWT>                                        │
├─────────────────────────────────────────────────────────────────────┤
│  AI检测(每天免费检测 / AI指数检测) - 普通账号可用                  │
│  ① POST /v1/api/CheckUserAccount       校验账号/额度 → document_id│
│  ② POST /v1/api/rewrite/checkAiWord    分段AI检测(可并发)         │
│  ③ POST /v1/api/contentcheckforindex   内容分析报告(≥500字)       │
├─────────────────────────────────────────────────────────────────────┤
│  深度检测(会员) - 普通新号无额度(code=403)                         │
│  ① POST /v1/api/CheckDeepDetectionAccount  校验额度 → contentId   │
│  ② POST /v1/api/rewrite/rewritetools       提交任务(type=11)      │
│  ③ POST /v1/api/queryTask                  轮询结果               │
├─────────────────────────────────────────────────────────────────────┤
│  辅助                                                                 │
│  POST /v1/api/user/get       获取用户信息                            │
│  POST /v1/api/user/getCaptchaConfig  验证码配置(仅手机验证码场景用)  │
│  POST /v1/api/user/logout    退出登录                                │
└─────────────────────────────────────────────────────────────────────┘
```

- **Base URL**: `https://cn.aifoxs.com`
- **API 前缀**: `/v1/api`
- **统一响应格式**: `{"code": 200, "msg": "...", "data": {...}, "token": "..."}`
  - `code=200` 成功；`401` 未登录；`402` 账号异常；`403` 无权限/额度；`405` 任务处理中；`429/500/503` 限流或服务错误

---

## 1. 账号体系

### 1.1 邮箱注册

```
POST /v1/api/user/add
Content-Type: application/x-www-form-urlencoded
language: zh-cn

body: email=aifoxs.test@gmail.com&nick_name=testuser&password=Test123456
```

**请求头**
| 字段 | 值 |
|---|---|
| Content-Type | application/x-www-form-urlencoded |
| language | zh-cn |

**响应**
```json
{"code": 200, "msg": "操作成功!"}
```

**说明**
- 邮箱注册**不触发**阿里云验证码（前端 `LoginDialog-CWKT9qtX.js` 的 `add` 请求无验证码参数）。
- 站点的阿里云验证码（`prefix=3vwk6z`, `sceneId=7veu2kyt`, `enabled=true`）**仅用于手机验证码发送场景**。
- 后端有 IP 级反滥用：短时间内多次注册会返回 `{"code":500,"msg":"检测到反复注册，如果遇到问题，请到设置中心找客服解决！"}`。等一段时间或换网络后可恢复。

### 1.2 邮箱登录

```
POST /v1/api/user/login
Content-Type: application/json
language: zh-cn

body: {"email":"aifoxs.test@gmail.com","password":"Test123456","device_id":"<uuid4>"}
```

**响应**
```json
{
  "code": 200,
  "msg": "操作成功!",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "data": {
    "id": "3f73ff34-2480-44b1-9b10-29cd531862e5",
    "email": "aifoxs.test@gmail.com",
    "phone": null,
    "nick_name": "testuser",
    "member_end_date": null,
    "current_ai_detect_count": 16000,
    "current_deep_detect_count": 0
  }
}
```

**说明**
- `device_id` 为 UUID v4，前端存于 localStorage `lw_client_device_id`。
- `token` 为 JWT，后续所有检测接口放入请求头 `token`。
- `current_ai_detect_count` = 普通 AI 检测剩余次数（新号 16000）；`current_deep_detect_count` = 深度检测次数（新号 0）。

### 1.3 其他账号接口

| 接口 | 方法 | 说明 |
|---|---|---|
| `/v1/api/user/get` | POST | 用 `token` 换取用户信息（body: `{"device_id":"..."}`） |
| `/v1/api/user/logout` | POST | 退出登录 |
| `/v1/api/user/getCaptchaConfig` | POST | 返回 `{prefix, sceneId, enabled}`（验证码仅手机场景用） |
| `/v1/api/user/registerByPhone` | POST | 手机号注册（需短信验证码 + 验证码） |
| `/v1/api/user/sendPhoneCode` | POST | 发送手机验证码（需阿里云验证码） |
| `/v1/api/url` | POST | 获取页面配置链接（type=1 隐私政策 / type=2 用户协议） |

---

## 2. AI 检测主流程（每天免费检测 / AI指数检测）

对应前端页面 `/ai-detect` 的「AI指数检测」按钮。普通新号即可用（`current_ai_detect_count` 扣减）。

### 2.1 ① 校验账号与额度

```
POST /v1/api/CheckUserAccount
Content-Type: application/x-www-form-urlencoded
language: zh-cn
token: <JWT>

body: content=<urlencoded 全文>
```

**响应**
```json
{
  "code": 200,
  "data": {
    "document_id": "CB6E73BF0B35E6EBFA2867BA69BC8F27",
    "max_work": 16,
    "min_word_count": 20,
    "checkAiWord": "[{\"isAi\": 0, \"checkCount\": 1, \"personScore\": 0.51, \"aiBotScore\": 0.49}]"
  }
}
```

| 字段 | 含义 |
|---|---|
| `document_id` | 本次检测文档 ID，后续分段检测必填（也可能放在 `msg` 里） |
| `max_work` | 单批最大并发段数（示例 16） |
| `min_word_count` | 最小分段字数（示例 20），低于此字数的段直接用预检结果 |
| `checkAiWord` | 预检结果（JSON 字符串）：`isAi=0/1`、`personScore`/`aiBotScore` 为 0~1 概率 |

**错误**
- `{"code":401,"msg":"请先登录"}` 未带有效 token
- `{"code":403,"msg":"会员已到期,该功能不可用"}` 深度检测额度不足（普通账号调 CheckDeepDetectionAccount 时出现）

### 2.2 ② 分段 AI 检测

```
POST /v1/api/rewrite/checkAiWord
Content-Type: application/json
language: zh-cn
token: <JWT>

body: [
  {"document_id":"CB6E73BF0B35E6EBFA2867BA69BC8F27","order_number":0,"content":"<段落1>","checkAiWord":""},
  {"document_id":"CB6E73BF0B35E6EBFA2867BA69BC8F27","order_number":1,"content":"<段落2>","checkAiWord":""}
]
```

**响应**
```json
{
  "code": 200,
  "msg": "success",
  "data": [
    {
      "document_id": "CB6E73BF0B35E6EBFA2867BA69BC8F27",
      "order_number": 0,
      "content": "<段落1>",
      "checkAiWord": "[{\"isAi\": 1, \"checkCount\": 1, \"personScore\": 0.0002, \"aiBotScore\": 0.9998}]"
    }
  ]
}
```

**注意**
- `checkAiWord` 字段在响应里是 **JSON 字符串**，需要二次 `json.loads`（可能有多元素数组，取第一个）。
- 段级 AI 占比 = `aiBotScore / (personScore + aiBotScore) × 100`。
- 按 `max_work` 分批提交；前端会把短段（≤min_word_count）跳过，直接用 2.1 的预检结果。

### 2.3 ③ 内容分析与质量报告

```
POST /v1/api/contentcheckforindex
Content-Type: application/x-www-form-urlencoded
language: zh-cn
token: <JWT>

body: content=<urlencoded 全文>&type=1
```

**响应**
```json
{
  "msg": "SUCCESS",
  "code": 200,
  "data": {
    "data": "\n## AI检测、内容质量分析和优化，流量预测\n...<markdown 报告>..."
  }
}
```

**注意**
- 正文需 ≥ **500 字**，否则返回 `{"data":{"data":"字数低于500字，不做任何检测操作"}}`。
- 报告为 **Markdown 字符串**，包含：是否可发布、资质提醒、恢复流量池、优化AI味道、冷启动流量预测、原创性/同质化/限流/敏感违规检测、内容优化建议等章节。

### 2.4 前端评估计算（脚本已复刻）

整体 AI 指数（页面右侧「AI指数」）由前端对分段结果自行计算：
- 取长度 > `min_word_count` 的段；AI 段占比即整体 AI 指数
- `AI指数 < 20%` → "约 80% 概率偏人工"；否则 → "AIGC 段落占比约 X%"

---

## 3. 深度检测流程（会员）

对应 `useDeepDetectJob-BsjhRQzB.js` / `qualityDetect-DbkKq4Bn.js`。普通新号 `current_deep_detect_count=0`，第一步即返回 `403 会员已到期`。

### 3.1 校验额度
```
POST /v1/api/CheckDeepDetectionAccount
body: content=<urlencoded>
→ {"code":200, "data":{"contentId":"..."}}
```

### 3.2 提交任务
```
POST /v1/api/rewrite/rewritetools
body: content=<urlencoded>&type=11&title=<标题>&contentId=<contentId>
→ {"code":200, "data":{"taskId":"...","taskName":"add_task_3","taskRequestTime":3000}}
```
若 `data` 直接为字符串（markdown）则为同步完成。

### 3.3 轮询结果
```
POST /v1/api/queryTask
body: taskId=<taskId>&taskName=<taskName>
→ 200: data=markdown 完成
→ 405: data.taskRequestTime=建议等待ms，data.showMessage=提示 → 继续轮询
→ 500: 查询任务失败
```

---

## 4. 限流与错误码

| code | 含义 | 处理 |
|---|---|---|
| 200 | 成功 | - |
| 401 | 未登录/token 失效 | 重新登录 |
| 402 | 账号异常/多处登录 | 联系客服 |
| 403 | 会员到期/无额度/权限不足 | 开通会员或换账号 |
| 405 | 任务处理中（仅 queryTask） | 按 `data.taskRequestTime` 延时后重查 |
| 429/500/503 | 限流/排队 | 按提示等待（如"请稍后20秒重试"）后重试 |

**限流特征**：`CheckUserAccount` 等在请求过快时返回形如 `{"msg":"你操作过快或者人数过多正在排队，请稍后20秒重试！"}` 的提示，脚本已做自动等待重试（最多 3 次）。

---

## 5. 已验证结论

| 项 | 结论 |
|---|---|
| 邮箱注册 | ✅ 可用，无需验证码（有 IP 反滥用） |
| 邮箱登录 | ✅ 可用，返回 JWT token |
| 检测需登录 | ✅ 必须（无 token 返回 401） |
| 免费检测额度 | ✅ 新号 16000 次（CheckUserAccount 体系） |
| 深度检测 | ⚠️ 会员专属，新号不可用 |
| 阿里云验证码 | 存在（enabled=true），但仅手机验证码场景强制，邮箱登录/注册不强制 |

---

## 6. 配套脚本（含账号池自动管理）

- **`aifoxs_detect.py`**：Python 实现完整检测流程（账号池 → 登录 → 校验 → 分段 → 分段AI检测 → 内容报告），输出结构化 JSON 并保存 Markdown 报告。仅用标准库，无第三方依赖。

### 6.1 账号池模式（推荐，无需手动管理账号）

不传 `-e/-p` 时脚本自动进入账号池模式，账号与密码保存在本地 `.aifoxs_accounts.json`（脚本同目录，权限 600）：

```bash
# 账号池模式：自动复用本地账号 → 额度用尽/风控自动换号 → 不足自动注册
python3 aifoxs_detect.py -f 文本文件.txt

# 直接传文本
python3 aifoxs_detect.py -t "待检测正文"

# 检测接口间隔 3 秒（高频/批量调用建议）
python3 aifoxs_detect.py -f 文本.txt --interval 3

# 只输出原始 JSON
python3 aifoxs_detect.py -f 文本.txt --json

# 禁用自动注册（本地无可用账号时直接失败）
python3 aifoxs_detect.py -f 文本.txt --no-auto-register
```

**账号池自动管理规则**：

| 情况 | 处理 |
|---|---|
| 本地有可用账号（登录成功且额度>0） | 直接复用（优先复用缓存 token，不重复登录） |
| 账号被风控（402 多处登录） | 标记 `banned`，自动切换下一个账号 |
| 额度用尽（403 / 额度为 0） | 标记 `out_of_quota`，自动切换下一个账号 |
| 登录/检测被限流（429） | 标记 `rate_limited`（当日暂停），切换下一个账号 |
| 所有账号不可用 | 自动注册新账号（`aifoxs.pool.<时间戳>@aifoxs.cn` / 密码 `Aifoxs2026`） |
| **注册也被风控** | **当日熔断**：不再尝试登录/注册/查询，明确提示用户缓一缓，建议前往朱雀AI检测 |

**状态文件**：
- `.aifoxs_accounts.json` — 账号池（email → password/status/last_error/registered_at）
- `.aifoxs_session.json` — 登录会话缓存（token + 稳定 device_id，避免频繁登录触发"多处登录"风控）

### 6.2 单账号模式（显式指定账号）

```bash
# 基础用法
python3 aifoxs_detect.py -e 邮箱 -p 密码 -f 文本文件.txt

# 直接传文本
python3 aifoxs_detect.py -e 邮箱 -p 密码 -t "待检测正文"

# 自动注册
python3 aifoxs_detect.py -e 邮箱 -p 密码 -t "正文" --register --nickname 用户名

# 输出原始 JSON
python3 aifoxs_detect.py -e 邮箱 -p 密码 -f 文本.txt --json

# 不保存报告
python3 aifoxs_detect.py -e 邮箱 -p 密码 -f 文本.txt --no-save-report

# 强制重新登录（忽略本地缓存 token）
python3 aifoxs_detect.py -e 邮箱 -p 密码 -f 文本.txt --refresh-login
```

### 6.3 输出

- 控制台：使用账号 / 总段数 / 疑似AI段 / 人工段 / AI指数占比 / 全文AI指数 / 分段明细。
- 默认保存到 `--out-dir`（默认当前目录）：
  - `aifoxs_report_<时间戳>.md` — 内容分析报告（需正文 ≥500 字）
  - `aifoxs_result_<时间戳>.json` — 结构化结果（`segments[]` 每段含 `type`/`ai_percent`）
