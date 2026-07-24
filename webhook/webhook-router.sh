#!/usr/bin/env bash
# webhook 路由入口脚本（在宝塔 webhook 配置里调用此脚本）
# 用法（在宝塔 webhook 脚本框里填一行）：
#   bash /www/server/panel/script/webhook-router.sh "$1"
#
# 参数传递：
# - 宝塔 webhook 会把 query string 作为 $1 传入
# - 也支持手动 curl 触发：curl "https://domain:port/hook?access_key=xxx&project=aibuddy&action=deploy"
#
# 支持的参数（query string 格式：key=value&key=value）：
#   project  必填，要部署的项目，如 aibuddy / wechat-mp
#   branch   可选，要部署的分支，默认 main
#   action   可选，执行动作：deploy(默认) / pull / restart
#
# 路由表（项目 → 部署脚本）：
#   aibuddy    → /www/server/panel/script/deploy-aibuddy.sh
#   wechat-mp  → /www/server/panel/script/deploy-wechat-mp.sh
#
# 日志：/var/log/webhook-deploy.log

set -uo pipefail

# ========== 配置 ==========
LOG_FILE="/var/log/webhook-deploy.log"
SCRIPT_DIR="/www/server/panel/script"
ACCESS_KEY_FILE="/www/server/panel/script/.webhook-access-key"  # 存放 access_key 的文件

# ========== 颜色（日志用，终端可见） ==========
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
  local ts
  ts=$(date '+%Y-%m-%d %H:%M:%S')
  echo -e "[$ts] $*" | tee -a "$LOG_FILE"
}

# ========== 解析参数 ==========
# 宝塔 webhook 把 query string 作为 $1 传入，格式可能是：
#   1. "access_key=xxx&project=aibuddy&branch=main&action=deploy"
#   2. JSON 字符串（GitHub push event payload）
#   3. 空（直接命令行调用）

RAW_INPUT="${1:-}"

# 尝试解析 query string 形式
parse_query() {
  local input="$1"
  local pair key value

  # 清空全局变量
  QUERY_PROJECT=""
  QUERY_BRANCH=""
  QUERY_ACTION=""
  QUERY_ACCESS_KEY=""

  # 如果是 JSON（以 { 开头），尝试用 jq 或 python 提取
  if [[ "$input" =~ ^\{ ]]; then
    if command -v jq &>/dev/null; then
      # GitHub push event payload，提取 ref 字段判断分支
      local ref
      ref=$(echo "$input" | jq -r '.ref // empty' 2>/dev/null)
      if [[ -n "$ref" ]]; then
        QUERY_BRANCH="${ref#refs/heads/}"
      fi
      # repository.name 可作为 project 提示（但不权威，仍以 URL query 为准）
    fi
    # JSON 形式不携带 project/access_key（这些在 URL query 里），直接返回
    return
  fi

  # query string 形式：按 & 分割
  for pair in ${input//&/ }; do
    key="${pair%%=*}"
    value="${pair#*=}"
    # URL decode（简化版，处理 %XX）
    value=$(printf '%b' "${value//%/\\x}")
    case "$key" in
      project)    QUERY_PROJECT="$value" ;;
      branch)     QUERY_BRANCH="$value" ;;
      action)     QUERY_ACTION="$value" ;;
      access_key) QUERY_ACCESS_KEY="$value" ;;
    esac
  done
}

parse_query "$RAW_INPUT"

# 默认值
PROJECT="${QUERY_PROJECT:-}"
BRANCH="${QUERY_BRANCH:-main}"
ACTION="${QUERY_ACTION:-deploy}"
ACCESS_KEY="${QUERY_ACCESS_KEY:-}"

# ========== 鉴权 ==========
if [ -f "$ACCESS_KEY_FILE" ]; then
  EXPECTED_KEY=$(cat "$ACCESS_KEY_FILE" | tr -d '[:space:]')
  if [ -n "$EXPECTED_KEY" ] && [ "$ACCESS_KEY" != "$EXPECTED_KEY" ]; then
    log "${RED}[REJECT]${NC} access_key 不匹配 (project=$PROJECT)"
    exit 1
  fi
fi

# ========== 路由 ==========
log "${BLUE}[START]${NC} project=$PROJECT branch=$BRANCH action=$ACTION"

case "$PROJECT" in
  aibuddy)
    DEPLOY_SCRIPT="$SCRIPT_DIR/deploy-aibuddy.sh"
    ;;
  wechat-mp)
    DEPLOY_SCRIPT="$SCRIPT_DIR/deploy-wechat-mp.sh"
    ;;
  "")
    log "${RED}[ERR]${NC} 缺少 project 参数。URL 应为：?access_key=xxx&project=aibuddy"
    log "${YELLOW}[TIP]${NC} 支持的 project: aibuddy / wechat-mp"
    exit 1
    ;;
  *)
    log "${RED}[ERR]${NC} 未知 project: $PROJECT"
    log "${YELLOW}[TIP]${NC} 支持的 project: aibuddy / wechat-mp"
    exit 1
    ;;
esac

if [ ! -f "$DEPLOY_SCRIPT" ]; then
  log "${RED}[ERR]${NC} 部署脚本不存在: $DEPLOY_SCRIPT"
  log "${YELLOW}[TIP]${NC} 请先从仓库拉取脚本到服务器"
  exit 1
fi

# ========== 调用具体部署脚本 ==========
log "${BLUE}[CALL]${NC} $DEPLOY_SCRIPT $BRANCH $ACTION"
if bash "$DEPLOY_SCRIPT" "$BRANCH" "$ACTION" 2>&1 | tee -a "$LOG_FILE"; then
  log "${GREEN}[DONE]${NC} $PROJECT 部署完成 (branch=$BRANCH action=$ACTION)"
else
  log "${RED}[FAIL]${NC} $PROJECT 部署失败 (branch=$BRANCH action=$ACTION)"
  exit 1
fi
