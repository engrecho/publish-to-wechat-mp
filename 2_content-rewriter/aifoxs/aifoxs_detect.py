#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ContentAny (cn.aifoxs.com) AI 检测脚本
=====================================
根据 https://cn.aifoxs.com/ai-detect 前端 JS 逆向得到的接口流程实现：

  [登录/注册]  →  [校验账号 CheckUserAccount]  →  [分段检测 rewrite/checkAiWord]  →  [内容分析报告 contentcheckforindex]

用法示例：
    python3 aifoxs_detect.py -e 你的邮箱@xx.com -p 你的密码 -t "待检测的正文内容"
    python3 aifoxs_detect.py -e ... -p ... -f content.txt              # 从文件读入正文
    python3 aifoxs_detect.py -e ... -p ... -t "正文" --register        # 自动注册新账号（会被反滥用拦截时需换邮箱/IP）
    python3 aifoxs_detect.py -e ... -p ... -t "正文" --json            # 输出原始 JSON
    python3 aifoxs_detect.py -e ... -p ... -t "正文" --no-save-report  # 不保存报告文件
    python3 aifoxs_detect.py -e ... -p ... -t "正文" --interval 3      # 检测接口间隔 3 秒，避免频繁调用触发限流
    python3 aifoxs_detect.py -e ... -p ... -t "正文" --refresh-login   # 强制重新登录（忽略本地缓存 token）

说明：脚本会把登录 token + 稳定 device_id 缓存到本地 .aifoxs_session.json，
      后续运行优先复用登录态，不再每次重新登录，从而避免触发账号“多处登录”风控与登录限流。
"""

import argparse
import json
import os
import re
import sys
import time
import uuid
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime

BASE_URL = "https://cn.aifoxs.com"
API_BASE = BASE_URL + "/v1/api"

# 速率限制关键词（与前端 activationPolicy 一致）
RATE_LIMIT_RE = re.compile(r"频繁|稍后再试|操作过快|操作太快|请求过快|排队|人数过多")

# ============================================================
# 1. HTTP 请求封装
# ============================================================

class AifoxsAPI:
    def __init__(self, timeout=120, session_file=None):
        self.timeout = timeout
        self.token = ""
        self.device_id = ""
        self.session_file = session_file or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), ".aifoxs_session.json")

    def _is_rate_limited(self, r):
        msg = str(r.get("msg") or "")
        return bool(RATE_LIMIT_RE.search(msg))

    def _extract_retry_seconds(self, r):
        """从错误信息里提取建议等待秒数（默认 20s）"""
        msg = str(r.get("msg") or "")
        m = re.search(r"(\d+)\s*秒", msg)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass
        return 20

    def _call_with_retry(self, fn, *args, max_retry=3, base_wait=20, verbose=None, **kwargs):
        """对限流和网络错误做重试：命中限流/网络异常 → 等待后重试"""
        for attempt in range(max_retry + 1):
            r = fn(*args, **kwargs)
            if r.get("code") == 200 or not (self._is_rate_limited(r) or r.get("code") == -1):
                return r
            wait = self._extract_retry_seconds(r)
            if r.get("code") == -1:
                wait = 5
            if verbose:
                print(f"      请求异常（{r.get('msg')}），等待 {wait}s 后重试 ({attempt + 1}/{max_retry})...")
            time.sleep(wait)
        return r

    def _request(self, path, data=None, json_body=False, extra_headers=None):
        """发送 POST 请求。
        data: 若为 dict 且 json_body=True 则 JSON 序列化；
               否则按 form-urlencoded 编码。
        """
        url = API_BASE + path
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Origin": BASE_URL,
            "Referer": BASE_URL + "/ai-detect",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "language": "zh-cn",
        }
        if extra_headers:
            headers.update(extra_headers)

        if data is None:
            body = b""
            headers["Content-Type"] = "application/json"
        elif json_body:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        else:
            body = urllib.parse.urlencode(data, doseq=True).encode("utf-8")
            headers.setdefault("Content-Type", "application/x-www-form-urlencoded")

        # 检测类接口需要带 token（与前端一致：token 为空字符串也要带上）
        if self.token:
            headers["token"] = self.token
        else:
            headers["token"] = ""

        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
        except Exception as e:
            return {"code": -1, "msg": f"网络错误: {e}"}
        try:
            return json.loads(raw)
        except Exception:
            return {"code": -1, "msg": f"响应解析失败: {raw[:200]}"}

    # ---------------- 会话持久化（避免频繁登录触发多处登录/限流） ----------------
    def _load_session(self, email):
        """读取指定账号的本地缓存会话（device_id + token）"""
        try:
            with open(self.session_file, "r", encoding="utf-8") as f:
                store = json.load(f)
            s = store.get("accounts", {}).get(email, {}) or {}
            self.device_id = s.get("device_id") or ""
            self.token = s.get("token") or ""
        except Exception:
            self.device_id = ""
            self.token = ""

    def _save_session(self, email):
        try:
            store = {}
            try:
                with open(self.session_file, "r", encoding="utf-8") as f:
                    store = json.load(f)
            except Exception:
                pass
            store.setdefault("accounts", {})[email] = {
                "device_id": self.device_id,
                "token": self.token,
                "saved_at": datetime.now().isoformat(),
            }
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump(store, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _clear_session(self, email=None):
        self.token = ""
        try:
            with open(self.session_file, "r", encoding="utf-8") as f:
                store = json.load(f)
            if email and store.get("accounts"):
                store["accounts"].pop(email, None)
                with open(self.session_file, "w", encoding="utf-8") as f:
                    json.dump(store, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def login_with_retry(self, email, password, max_retry=4, base_wait=30, verbose=None):
        """登录并缓存会话。遇到 429/限流时指数退避重试。"""
        waits = [base_wait, base_wait * 2, base_wait * 3]
        for attempt in range(max_retry):
            r = self.login(email, password)
            if r.get("code") == 200:
                return r
            if not (r.get("code") == 429 or self._is_rate_limited(r)):
                return r
            wait = self._extract_retry_seconds(r)
            if wait <= 0:
                wait = waits[attempt] if attempt < len(waits) else waits[-1]
            if verbose:
                print(f"      登录限流（{r.get('msg')}），等待 {wait}s 后重试 ({attempt + 1}/{max_retry})...")
            time.sleep(wait)
        return r

    def ensure_login(self, email, password, force=False, verbose=None):
        """优先复用本地缓存的 token（按账号独立）；失效才重新登录（复用稳定 device_id）。
        返回 (user, ok)。"""
        self._load_session(email)
        # 1) 尝试复用本地 token
        if not force and self.token:
            if verbose:
                print("检测到本地登录态，正在校验 token 是否有效...")
            gu = self.get_user()
            if gu.get("code") == 200 and gu.get("data"):
                data = gu.get("data")
                if verbose:
                    print(f"      token 有效，复用会话：用户={data.get('nick_name') or data.get('email')}, "
                          f"AI检测额度={data.get('current_ai_detect_count')}, "
                          f"深度检测额度={data.get('current_deep_detect_count')}")
                return data, True
            else:
                if verbose:
                    print(f"      token 已失效（code={gu.get('code')} msg={gu.get('msg')}），重新登录...")
                self._clear_session(email)

        # 2) 重新登录：device_id 稳定（每个账号首次生成后持久化，不再每次新建）
        if not self.device_id:
            self.device_id = str(uuid.uuid4())
        lr = self.login_with_retry(email, password, verbose=verbose)
        if lr.get("code") != 200:
            return None, False
        self._save_session(email)
        return lr.get("data") or {}, True

    # ---------------- 账号 ----------------
    def register(self, email, password, nick_name):
        """邮箱注册（前端走 form-urlencoded，无需验证码）"""
        return self._request("/user/add", {
            "email": email,
            "nick_name": nick_name,
            "password": password,
        })

    def login(self, email, password):
        """邮箱登录（JSON body，复用稳定 device_id）。返回 token 与用户信息。"""
        device_id = self.device_id or str(uuid.uuid4())
        if not self.device_id:
            self.device_id = device_id
        r = self._request("/user/login", {
            "email": email,
            "password": password,
            "device_id": device_id,
        }, json_body=True)
        if r.get("code") == 200 and r.get("token"):
            self.token = r["token"]
        return r

    def get_user(self):
        """获取当前用户信息（复用稳定 device_id）"""
        return self._request("/user/get", {"device_id": self.device_id or str(uuid.uuid4())}, json_body=True)

    def logout(self):
        return self._request("/user/logout")

    def get_captcha_config(self):
        """获取验证码配置（说明站点确实接了阿里云验证码，但邮箱注册/登录不强制）"""
        return self._request("/user/getCaptchaConfig")

    # ---------------- AI 检测（每天免费检测 / AI指数检测） ----------------
    def check_user_account(self, content):
        """校验账号与检测额度。返回 document_id / max_work / min_word_count / checkAiWord"""
        return self._request("/CheckUserAccount", {"content": content})

    def check_ai_word(self, segments):
        """分段 AI 检测。segments: [{document_id, order_number, content, checkAiWord:""}]"""
        return self._request("/rewrite/checkAiWord", segments, json_body=True)

    def content_check_for_index(self, content, content_type=1):
        """内容分析与质量报告（需 500+ 字）。返回 markdown 报告。"""
        return self._request("/contentcheckforindex", {
            "content": content,
            "type": content_type,
        })

    # ---------------- 深度检测（会员功能，新号可能无额度） ----------------
    def check_deep_detect_account(self, content):
        """深度检测额度校验（会员）。返回 contentId"""
        return self._request("/CheckDeepDetectionAccount", {"content": content})

    def deep_detect_submit(self, content, title="", content_id=""):
        """提交深度检测任务（rewritetools, type=11）。"""
        params = {"content": content, "type": "11", "title": title}
        if content_id:
            params["contentId"] = content_id
        return self._request("/rewrite/rewritetools", params)

    def query_task(self, task_id, task_name="add_task_3"):
        """轮询任务结果。200=完成(data为markdown) / 405=处理中(带 nextDelayMs)"""
        return self._request("/queryTask", {"taskId": task_id, "taskName": task_name})


# ============================================================
# 1.5 账号池自动管理（本地缓存 + 额度/风控/注册熔断）
# ============================================================

# 账号状态
ACC_ACTIVE = "active"        # 可用
ACC_BANNED = "banned"        # 账号被风控（多处登录 402）
ACC_OUT_OF_QUOTA = "out_of_quota"  # 额度用尽
ACC_RATE_LIMITED = "rate_limited"  # 登录/检测被限流（当日暂停）
ACC_LOGIN_FAILED = "login_failed"  # 登录失败（密码错误等）

# 注册被反滥用/风控的特征文案
REGISTER_ABUSE_RE = re.compile(r"反复注册|注册过于频繁|注册太频繁|频繁注册|被限制|风控|操作过快|请稍后")
DEFAULT_PASSWORD = "Aifoxs2026"


def _ts(s):
    """把 ISO 时间字符串转成可排序的时间戳（空串按最小值处理）"""
    if not s:
        return 0
    try:
        return datetime.fromisoformat(s).timestamp()
    except Exception:
        return 0


class AccountPool:
    """账号池：账号密码保存在本地 .aifoxs_accounts.json。

    规则：
    - 有可用账号（active 且额度>0）→ 直接复用
    - 没有可用 → 注册新账号（每个账号限一次注册）
    - 账号被风控 / 额度用尽 → 标记状态，换下一个账号
    - 注册也被风控 → 当日熔断，不再登录/注册/查询，提示用户去朱雀AI检测
    """

    def __init__(self, accounts_file=None):
        self.file = accounts_file or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), ".aifoxs_accounts.json")
        self.data = self._load()

    def _load(self):
        try:
            with open(self.file, "r", encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict):
                return d
        except Exception:
            pass
        return {"accounts": {}, "register_blocked_until": ""}

    def _save(self):
        try:
            with open(self.file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            try:
                os.chmod(self.file, 0o600)
            except Exception:
                pass
        except Exception:
            pass

    # ---------- 账号 ----------
    def add_account(self, email, password, nick_name=None, status=ACC_ACTIVE):
        acc = self.data["accounts"].get(email) or {}
        acc.update({
            "password": password,
            "nick_name": nick_name or acc.get("nick_name") or "",
            "status": status,
            "registered_at": acc.get("registered_at") or datetime.now().isoformat(),
            "last_used_at": acc.get("last_used_at") or "",
        })
        self.data["accounts"][email] = acc
        self._save()
        return acc

    def get_account(self, email):
        return self.data["accounts"].get(email)

    def mark(self, email, status, last_error=""):
        acc = self.data["accounts"].get(email)
        if not acc:
            return
        acc["status"] = status
        if last_error:
            acc["last_error"] = last_error
        acc["last_used_at"] = datetime.now().isoformat()
        self._save()

    def candidates(self):
        """返回候选账号 [(email, acc)]，按状态优先级排序（active > login_failed > rate_limited 已过期 > 其他）"""
        now = datetime.now()
        items = []
        for email, acc in self.data["accounts"].items():
            status = acc.get("status", ACC_ACTIVE)
            # 当日限流到期后恢复
            if status == ACC_RATE_LIMITED and acc.get("rate_limited_until"):
                try:
                    until = datetime.fromisoformat(acc["rate_limited_until"])
                    if now > until:
                        status = ACC_ACTIVE
                        acc["status"] = ACC_ACTIVE
                except Exception:
                    pass
            items.append((email, acc, status))
        order = {ACC_ACTIVE: 0, ACC_LOGIN_FAILED: 1, ACC_RATE_LIMITED: 2,
                 ACC_OUT_OF_QUOTA: 3, ACC_BANNED: 4}
        items.sort(key=lambda x: (order.get(x[2], 9),
                                  x[1].get("last_used_at") or ""), reverse=False)
        # 同状态内最近使用过的排前面（last_used_at 为 ISO 字符串，倒序）
        items.sort(key=lambda x: (order.get(x[2], 9),
                                  -_ts(x[1].get("last_used_at") or "")))
        return [(e, a) for e, a, s in items if s in (ACC_ACTIVE, ACC_LOGIN_FAILED, ACC_RATE_LIMITED)]

    def count(self):
        return len(self.data.get("accounts", {}))

    # ---------- 注册熔断 ----------
    def is_register_blocked(self):
        until = self.data.get("register_blocked_until") or ""
        if not until:
            return False
        try:
            return datetime.now() < datetime.fromisoformat(until)
        except Exception:
            return False

    def block_register_today(self, reason=""):
        """当日熔断：注册也被风控后，当天不再登录/注册/查询"""
        end_of_day = datetime.now().replace(hour=23, minute=59, second=59, microsecond=0)
        self.data["register_blocked_until"] = end_of_day.isoformat()
        self.data["register_block_reason"] = reason
        self._save()

    def blocked_info(self):
        return {
            "register_blocked_until": self.data.get("register_blocked_until", ""),
            "register_block_reason": self.data.get("register_block_reason", ""),
        }


# ============================================================
# 2. 分段算法（忠实移植自前端 assets/aiRepeatSplit-XBF1r3TK.js）
# ============================================================

CN_RE = re.compile(r"[\u4e00-\u9fa5]")


def word_count(t):
    """前端 a()：含中文按字符数，否则按空白分隔单词数"""
    if CN_RE.search(t):
        return len(t)
    return len([w for w in re.split(r"\s+", t) if w])


def normalize_newlines(t):
    if t is None:
        return ""
    return (str(t).replace("\r\n", "\n").replace("\r", "\n")
                  .replace("<br/>", "\n").replace("<br>", "\n")
                  .replace("</br>", "\n"))


def split_lines(t):
    return re.split(r"\r?\n|\r", t)


def split_sentences(t):
    """前端 A()：按句号/问号/感叹号切句（排除小数点的前后数字场景）"""
    out, buf = [], ""
    for i, ch in enumerate(t):
        buf += ch
        if ch in "。！？.!?":
            prev = t[i - 1] if i > 0 else ""
            nxt = t[i + 1] if i + 1 < len(t) else ""
            if not (ch == "." and (prev.isdigit() or nxt.isdigit())):
                out.append(buf)
                buf = ""
    if buf:
        out.append(buf)
    return out


def split_commas(t):
    """前端 v()：按中文逗号/分号、英文逗号切分"""
    out, buf = [], ""
    for i, ch in enumerate(t):
        buf += ch
        if ch in "，；":
            out.append(buf)
            buf = ""
        elif ch == ",":
            prev = t[i - 1] if i > 0 else ""
            nxt = t[i + 1] if i + 1 < len(t) else ""
            if not (prev.isdigit() and nxt.isdigit()):
                out.append(buf)
                buf = ""
    if buf:
        out.append(buf)
    return out


def merge_pieces(pieces, low, high, cnt=word_count):
    """前端 T()：把碎片合并成 low~high 字数的块"""
    items = [p.strip() for p in pieces]
    items = [p for p in items if p]
    if not items:
        return []
    merged = []
    cur = items[0]
    for it in items[1:]:
        if cnt(cur + it) <= high:
            cur += it
        else:
            merged.append(cur)
            cur = it
    merged.append(cur)
    # 短块与上一块合并
    result = []
    for it in merged:
        if result and cnt(it) < low and cnt(result[-1] + it) <= high:
            result[-1] = result[-1] + it
        else:
            result.append(it)
    return result


def split_chunks(t, size):
    """前端 y()：按固定字符数切块"""
    return [t[i:i + size] for i in range(0, len(t), size)]


def split_max_chunk(t, limit):
    """前端 _()：把长文本切成 ≤limit 字符的块（按句子合并）"""
    if not t:
        return []
    if len(t) <= limit:
        return [t]
    sents = [s for s in split_sentences(t) if s.strip()]
    if not sents:
        return split_chunks(t, limit)
    result, cur = [], ""
    for s in sents:
        if len(s) > limit * 1.5:
            if cur:
                result.append(cur)
                cur = ""
            result.extend(split_chunks(s, limit))
            continue
        if len(s) > limit:
            if cur:
                result.append(cur)
                cur = ""
            result.extend(split_chunks(s, limit))
            continue
        if cur:
            if len(cur) + len(s) <= limit:
                cur += s
            else:
                result.append(cur)
                cur = s
        else:
            cur = s
    if cur:
        result.append(cur)
    return result


def split_content(content, min_word_count=20):
    """前端 E()：主分段函数。返回分段列表（每段>0字符，一般≤400字符）"""
    text = normalize_newlines(content or "")
    lines = [ln for ln in split_lines(text) if ln.strip()]
    if not lines:
        return []

    s = 150
    f = min(220, max(s + 20, 180))   # 180
    u = min(32, max(24, int(s * 0.2)))  # 30
    output = []

    for line in lines:
        if word_count(line) > s:
            for sent in split_sentences(line):
                d = sent.strip()
                if not d:
                    continue
                if len(d) > s:
                    pieces = split_commas(d)
                    for chunk in merge_pieces(pieces, u, f):
                        c = chunk.strip()
                        if c:
                            output.append(c)
                else:
                    output.append(sent)
        else:
            output.append(line)

    if not output:
        if text.strip() and not lines:
            output = [text]
        elif text.strip() and lines:
            output = list(lines)

    final = []
    for c in output:
        if c.strip():
            final.extend(split_max_chunk(c, 400))
    return [s for s in final if s.strip()]


def compute_evaluation(segments, min_word_count=20, pre_ai=False):
    """前端 Ie()：根据分段结果计算整体 AI 指数评估"""
    valid = [s for s in segments if len(s["text"]) > min_word_count] or segments
    total = len(valid) or 1
    ai_count = len([s for s in valid if s["type"] == "ai"])
    ai_percent = round(ai_count / total * 100)
    full_text_ai = round(ai_count / total * 10000) / 100
    if ai_percent < 20:
        deep_status = "模型参考：约 80% 概率偏人工"
    else:
        deep_status = f"AIGC 段落占比约 {ai_percent}%"
    return {
        "aiDensity": 0,
        "fullTextAi": full_text_ai,
        "deepStatus": deep_status,
        "limitFlow": 0,
        "isWater": False,
        "isSensitive": False,
        "hasSensitive": False,
        "aiPercent": ai_percent,
    }


def parse_check_ai_word(s):
    """前端 O()：解析 checkAiWord 字段（可能是字符串/JSON/对象）"""
    if s is None or s == "":
        return {}
    if isinstance(s, dict):
        return s
    if isinstance(s, str):
        try:
            arr = json.loads(s)
            if isinstance(arr, list) and arr and isinstance(arr[0], dict):
                return arr[0]
            if isinstance(arr, dict):
                return arr
        except Exception:
            return {}
    return {}


# ============================================================
# 3. 检测主流程
# ============================================================

def detect(api, content, verbose=True, interval=0):
    """执行完整 AI 检测流程，返回结构化结果 dict
    interval: 检测接口之间的请求间隔秒数（避免频繁调用触发限流）
    """
    def _pause():
        if interval > 0:
            time.sleep(interval)

    content = (content or "").strip()
    if not content:
        return {"code": -1, "msg": "内容为空"}

    # ① 校验账号与额度（限流自动重试）
    r = api._call_with_retry(api.check_user_account, content, verbose=verbose)
    if r.get("code") != 200:
        return r
    _pause()
    data = r.get("data") or {}
    document_id = str(data.get("document_id") or "") if data.get("document_id") else ""
    if not document_id and r.get("msg"):
        document_id = str(r["msg"]).strip()
    if not document_id:
        return {"code": -1, "msg": "账号校验未返回文档ID", "raw": r}
    max_work = max(1, int(data.get("max_work") or 1))
    min_word_count = max(4, int(data.get("min_word_count") or 20))
    pre_check = parse_check_ai_word(data.get("checkAiWord"))
    if verbose:
        print(f"[1/3] 账号校验通过: document_id={document_id}, max_work={max_work}, min_word={min_word_count}")
        if pre_check.get("isAi") is not None:
            print(f"      预检: isAi={pre_check.get('isAi')}, person={pre_check.get('personScore')}, ai={pre_check.get('aiBotScore')}")

    # ② 分段
    segments = split_content(content, min_word_count)
    if not segments:
        return {"code": -1, "msg": "有效内容过少，请增加内容后重试"}
    if verbose:
        print(f"[2/3] 内容已拆分为 {len(segments)} 段，开始分段 AI 检测...")

    # ③ 分段检测（短段直接用预检结果，长段调用 checkAiWord）
    results = []  # [{text, type, ai_percent, checkAiWord}]
    batch = []
    pending = []
    for idx, seg in enumerate(segments):
        if word_count(seg) > min_word_count:
            batch.append({"document_id": document_id, "order_number": idx, "content": seg, "checkAiWord": ""})
            pending.append((idx, seg))
        else:
            is_ai = pre_check.get("isAi") == 1
            results.append({"text": seg, "type": "ai" if is_ai else "human",
                            "ai_percent": 50 if is_ai else 0,
                            "checkAiWord": pre_check})

    # 按 max_work 分批请求
    for i in range(0, len(batch), max_work):
        chunk = batch[i:i + max_work]
        rr = api._call_with_retry(api.check_ai_word, chunk, verbose=verbose)
        _pause()
        if rr.get("code") == 401:
            return {"code": 401, "msg": "请先登录"}
        if rr.get("code") == 402:
            return {"code": 402, "msg": rr.get("msg") or "账号被风控（多处登录违规）"}
        if rr.get("code") == 403:
            return {"code": 403, "msg": rr.get("msg") or "权限或额度不足"}
        if rr.get("code") != 200:
            # 失败时按预检兜底
            for item in chunk:
                is_ai = pre_check.get("isAi") == 1
                results.append({"text": item["content"], "type": "ai" if is_ai else "human",
                                "ai_percent": 50 if is_ai else 0, "checkAiWord": pre_check})
            continue
        data_list = rr.get("data") or []
        for item in data_list:
            ca = parse_check_ai_word(item.get("checkAiWord"))
            is_ai = ca.get("isAi") == 1
            if isinstance(ca.get("personScore"), (int, float)) and isinstance(ca.get("aiBotScore"), (int, float)):
                p = ca["personScore"] + ca["aiBotScore"]
                ai_percent = round(ca["aiBotScore"] / p * 100) if p else (50 if is_ai else 0)
            else:
                ai_percent = 50 if is_ai else 0
            results.append({"text": item.get("content", ""), "type": "ai" if is_ai else "human",
                            "ai_percent": ai_percent, "checkAiWord": ca})

    # 结果已按提交顺序排列
    results = [r for r in results if r["text"]]

    evaluation = compute_evaluation(results, min_word_count)

    # ④ 内容分析报告（全文合并，需 500+ 字）
    joined = "\r\n".join([r["text"] for r in results])
    report_md = ""
    if len(joined.replace(" ", "")) >= 500:
        if verbose:
            print("[3/3] 内容 ≥500 字，生成内容分析报告...")
        cr = api._call_with_retry(api.content_check_for_index, joined, 1, verbose=verbose)
        if cr.get("code") == 200:
            d = cr.get("data") or {}
            report_md = d.get("data") or ""
        elif verbose:
            print(f"      内容分析报告生成失败: code={cr.get('code')} msg={cr.get('msg')}")
    else:
        if verbose:
            print("[3/3] 内容 <500 字，跳过内容分析报告（仅返回分段检测）")

    return {
        "code": 200,
        "document_id": document_id,
        "total_segments": len(results),
        "ai_segments": len([r for r in results if r["type"] == "ai"]),
        "human_segments": len([r for r in results if r["type"] == "human"]),
        "ai_percent": evaluation["aiPercent"],
        "full_text_ai": evaluation["fullTextAi"],
        "evaluation": evaluation,
        "segments": results,
        "report_markdown": report_md,
    }


# ============================================================
# 4. 主入口
# ============================================================

def run_with_pool(content, interval=0, verbose=True, pool=None, register=True):
    """账号池自动调度：复用可用账号 → 额度/风控判断 → 注册新账号 → 注册风控则当日熔断。

    返回 (result, api)。result 带 account 字段标识实际使用的账号。
    """
    pool = pool or AccountPool()
    if verbose:
        print(f"[账号池] 本地账号数: {pool.count()}")

    # ① 遍历本地账号池，找可用的账号
    for email, acc in pool.candidates():
        password = acc.get("password") or ""
        if not password:
            continue
        if verbose:
            print(f"[账号] 尝试本地账号 {email} ...")
        api = AifoxsAPI()
        user, ok = api.ensure_login(email, password, verbose=verbose)
        if not ok:
            if verbose:
                print(f"      {email} 登录失败，标记为登录失败，换下一个账号")
            pool.mark(email, ACC_LOGIN_FAILED, "登录失败")
            continue
        quota = int(user.get("current_ai_detect_count") or 0)
        if quota <= 0:
            if verbose:
                print(f"      {email} AI检测额度用尽（{quota}），标记为额度用尽，换下一个账号")
            pool.mark(email, ACC_OUT_OF_QUOTA, "AI检测额度用尽")
            continue
        if verbose:
            print(f"      账号可用：{email}，AI检测额度={quota}")
        result = detect(api, content, verbose=verbose, interval=interval)
        code = result.get("code")
        if code == 200:
            result["account"] = email
            return result, api
        if code == 402:
            if verbose:
                print(f"      {email} 被风控（{result.get('msg')}），标记为风控，换下一个账号")
            pool.mark(email, ACC_BANNED, result.get("msg", "账号风控"))
            continue
        if code == 403:
            if verbose:
                print(f"      {email} 额度/权限不足，标记为额度用尽，换下一个账号")
            pool.mark(email, ACC_OUT_OF_QUOTA, result.get("msg", "额度不足"))
            continue
        if code in (429, -1) or isinstance(code, int) and code >= 500:
            if verbose:
                print(f"      {email} 触发限流/服务异常，标记为限流暂停，换下一个账号")
            pool.mark(email, ACC_RATE_LIMITED, result.get("msg", "限流"))
            continue
        # 其他错误直接返回
        result["account"] = email
        return result, api

    # ② 本地账号池没有可用账号
    if not register:
        return {"code": -3, "msg": "本地账号池无可用账号，且未开启自动注册",
                "account": None}, None

    # ③ 检查注册熔断：注册也被风控则当日不再操作
    if pool.is_register_blocked():
        info = pool.blocked_info()
        return {"code": -4,
                "msg": (f"所有账号不可用，且注册被风控（{info.get('register_block_reason') or '注册过于频繁'}）。"
                        f"今日已熔断，不再尝试登录/注册/查询（截至 {info.get('register_blocked_until')}）。"
                        f"请缓一缓，明日再试，或前往朱雀AI检测。"),
                "account": None}, None

    # ④ 注册新账号
    email = f"aifoxs.pool.{int(time.time())}@aifoxs.cn"
    nick = f"pooluser{int(time.time()) % 100000}"
    if verbose:
        print(f"[注册] 尝试注册新账号 {email} ...")
    api = AifoxsAPI()
    rr = api.register(email, DEFAULT_PASSWORD, nick)
    if rr.get("code") != 200:
        reason = rr.get("msg") or "注册被风控"
        if verbose:
            print(f"      注册被风控：{reason}")
        pool.block_register_today(reason)
        return {"code": -4,
                "msg": (f"注册也被风控（{reason}）。今日已熔断，不再尝试登录/注册/查询。"
                        f"请缓一缓，明日再试，或前往朱雀AI检测。"),
                "account": None}, None

    pool.add_account(email, DEFAULT_PASSWORD, nick)
    if verbose:
        print(f"      注册成功，开始登录...")
    user, ok = api.ensure_login(email, DEFAULT_PASSWORD, verbose=verbose)
    if not ok:
        pool.mark(email, ACC_LOGIN_FAILED, "注册后登录失败")
        return {"code": -3, "msg": "新账号注册成功但登录失败", "account": email}, api
    if verbose:
        print(f"      新账号可用：{email}，AI检测额度={user.get('current_ai_detect_count')}")
    result = detect(api, content, verbose=verbose, interval=interval)
    if result.get("code") == 200:
        result["account"] = email
    else:
        result["account"] = email
    return result, api


def main():
    parser = argparse.ArgumentParser(
        description="ContentAny AI 检测脚本（cn.aifoxs.com），支持账号池自动管理")
    parser.add_argument("-e", "--email", help="登录邮箱（不传则自动从账号池管理）")
    parser.add_argument("-p", "--password", help="登录密码（配合 -e）")
    parser.add_argument("-t", "--text", help="待检测正文（直接传入）")
    parser.add_argument("-f", "--file", help="待检测正文文件路径")
    parser.add_argument("-n", "--nickname", help="注册用户名（配合 --register）")
    parser.add_argument("--register", action="store_true",
                        help="单账号模式下先注册再登录")
    parser.add_argument("--json", action="store_true", help="输出原始 JSON")
    parser.add_argument("--no-save-report", action="store_true", help="不保存 Markdown 报告文件")
    parser.add_argument("--refresh-login", action="store_true",
                        help="强制重新登录（忽略本地缓存的 token）")
    parser.add_argument("--interval", type=float, default=0,
                        help="检测接口之间的请求间隔秒数（默认 0，频繁调用可设 3~5 秒避免限流）")
    parser.add_argument("--out-dir", default=".", help="报告保存目录（默认当前目录）")
    parser.add_argument("--account-file", default=None,
                        help="账号池文件路径（默认 .aifoxs_accounts.json）")
    parser.add_argument("--no-auto-register", action="store_true",
                        help="账号池模式下禁用自动注册新账号")
    args = parser.parse_args()

    content = args.text or ""
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            content = f.read().strip()
    if not content:
        print("错误：请通过 -t 或 -f 提供待检测内容", file=sys.stderr)
        sys.exit(2)

    # ---------- 单账号模式（显式提供 -e/-p） ----------
    if args.email and args.password:
        api = AifoxsAPI()

        if args.register:
            nick = args.nickname or f"user_{int(time.time()) % 100000}"
            print(f"[注册] {args.email} / {nick} ...")
            rr = api.register(args.email, args.password, nick)
            print(f"      注册返回: code={rr.get('code')} msg={rr.get('msg')}")
            if rr.get("code") != 200:
                print("警告：注册失败，尝试直接登录（若账号已存在可忽略）")

        print(f"[登录] {args.email} ...")
        user, ok = api.ensure_login(args.email, args.password,
                                    force=args.refresh_login, verbose=True)
        if not ok:
            print(f"登录失败，请稍后再试（若持续提示“请求过于频繁”，说明该账号/IP 登录频率过高，"
                  f"请间隔 1~2 分钟再运行，或换网络后重试）", file=sys.stderr)
            sys.exit(1)
        print(f"      登录成功: 用户={user.get('nick_name') or user.get('email')}, "
              f"AI检测额度={user.get('current_ai_detect_count')}, "
              f"深度检测额度={user.get('current_deep_detect_count')}")
        result = detect(api, content, interval=args.interval)
    # ---------- 账号池自动管理模式 ----------
    else:
        pool = AccountPool(accounts_file=args.account_file)
        result, api = run_with_pool(content, interval=args.interval,
                                    verbose=True, pool=pool,
                                    register=not args.no_auto_register)
        if result.get("code") not in (200,) and result.get("code") == -4:
            print(f"检测失败: {result.get('msg')}", file=sys.stderr)
            sys.exit(3)

    if result.get("code") != 200:
        print(f"检测失败: {result.get('msg')}", file=sys.stderr)
        if "raw" in result:
            print(json.dumps(result["raw"], ensure_ascii=False, indent=2))
        sys.exit(1)

    # 输出
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("\n================ 检测结果 ================")
        if result.get("account"):
            print(f"使用账号  : {result['account']}")
        print(f"总段数      : {result['total_segments']}")
        print(f"疑似AI段    : {result['ai_segments']}")
        print(f"人工段      : {result['human_segments']}")
        print(f"AI指数占比  : {result['ai_percent']}%")
        print(f"全文AI指数  : {result['full_text_ai']}%")
        print(f"深度状态    : {result['evaluation']['deepStatus']}")
        print("------------------------------------------")
        print("分段明细:")
        for i, seg in enumerate(result["segments"]):
            marker = "🟥AI" if seg["type"] == "ai" else "🟦人工"
            print(f"  [{i}] {marker} {seg['ai_percent']}% | {seg['text'][:50]}{'...' if len(seg['text']) > 50 else ''}")
        if result["report_markdown"]:
            print("------------------------------------------")
            print("内容分析报告（Markdown）已生成")

    # 保存报告
    if result.get("report_markdown") and not args.no_save_report:
        os.makedirs(args.out_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        md_path = os.path.join(args.out_dir, f"aifoxs_report_{ts}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(result["report_markdown"])
        print(f"\n报告已保存: {md_path}")
        # 同时保存结构化 JSON
        json_path = os.path.join(args.out_dir, f"aifoxs_result_{ts}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"结构化结果: {json_path}")


if __name__ == "__main__":
    main()
