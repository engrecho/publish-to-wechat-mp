#!/usr/bin/env bash
# publish-to-wechat-mp 项目部署脚本（仅部署 server/ 部分）
# 由 webhook-router.sh 调用
# 用法：bash deploy-wechat-mp.sh <branch> <action>
#   branch: git 分支名，默认 main
#   action: deploy(默认) / pull / restart

set -uo pipefail

BRANCH="${1:-main}"
ACTION="${2:-deploy}"

# ========== 项目配置 ==========
REPO="engrecho/publish-to-wechat-mp"
GHPROXY="https://ghproxy.com"
INSTALL_DIR="/www/wwwroot/wechat-mp"
SERVICE_NAME="wechat-publish"
LOG_FILE="/var/log/webhook-deploy.log"

log() {
  local ts
  ts=$(date '+%Y-%m-%d %H:%M:%S')
  echo "[$ts] [wechat-mp] $*" | tee -a "$LOG_FILE"
}

log "开始部署 (branch=$BRANCH action=$ACTION)"

# ========== pull ==========
if [ "$ACTION" = "pull" ] || [ "$ACTION" = "deploy" ]; then
  if [ -d "$INSTALL_DIR/.git" ]; then
    cd "$INSTALL_DIR"
    log "git fetch origin $BRANCH"
    git fetch origin "$BRANCH"
    git reset --hard "origin/$BRANCH"
  else
    log "首次 clone（用 ghproxy 代理）"
    mkdir -p "$(dirname "$INSTALL_DIR")"
    git clone "$GHPROXY/https://github.com/$REPO" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    git checkout "$BRANCH"
  fi
  log "代码已更新到 $(git rev-parse --short HEAD)"

  if [ "$ACTION" = "pull" ]; then
    log "pull 完成"
    exit 0
  fi
fi

# ========== deploy：npm install + 重启 ==========
cd "$INSTALL_DIR/server"

log "npm install --omit=dev"
npm install --omit=dev 2>&1 | tail -3 | tee -a "$LOG_FILE"

# ========== restart ==========
if [ "$ACTION" = "deploy" ] || [ "$ACTION" = "restart" ]; then
  if ! command -v pm2 &>/dev/null; then
    log "PM2 未安装"
    exit 1
  fi

  if pm2 describe "$SERVICE_NAME" &>/dev/null; then
    log "pm2 restart $SERVICE_NAME"
    pm2 restart "$SERVICE_NAME" --update-env
  else
    log "PM2 进程 $SERVICE_NAME 不存在（首次部署需要先用 deploy.sh 启动）"
    log "请先手动执行: bash $INSTALL_DIR/deploy.sh"
    exit 1
  fi

  pm2 save

  # 健康检查
  sleep 2
  if curl -sf "http://127.0.0.1:8080/health" | grep -q '"ok":true'; then
    log "健康检查通过"
  else
    log "健康检查失败，请检查日志: pm2 logs $SERVICE_NAME --lines 30"
    exit 1
  fi
fi

log "部署完成"
