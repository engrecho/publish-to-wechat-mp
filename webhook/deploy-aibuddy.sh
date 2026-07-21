#!/usr/bin/env bash
# AI-buddy 项目部署脚本
# 由 webhook-router.sh 调用
# 用法：bash deploy-aibuddy.sh <branch> <action>
#   branch: git 分支名，默认 main
#   action: deploy(默认) / pull / restart

set -uo pipefail

BRANCH="${1:-main}"
ACTION="${2:-deploy}"

# ========== 项目配置 ==========
REPO="engrecho/AI-buddy"
GHPROXY="https://ghproxy.com"
INSTALL_DIR="/www/wwwroot/aibuddy"
SERVICE_NAME="aibuddy"
LOG_FILE="/var/log/webhook-deploy.log"

log() {
  local ts
  ts=$(date '+%Y-%m-%d %H:%M:%S')
  echo "[$ts] [aibuddy] $*" | tee -a "$LOG_FILE"
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

  # 如果是 pull-only，到此结束
  if [ "$ACTION" = "pull" ]; then
    log "pull 完成"
    exit 0
  fi
fi

# ========== deploy：构建 + 重启 ==========
cd "$INSTALL_DIR"

# AI-buddy 是 PHP 项目，按宝塔常规做法部署
# 如果项目有 composer.json，执行 composer install
if [ -f "composer.json" ]; then
  log "执行 composer install"
  if command -v composer &>/dev/null; then
    composer install --no-dev --optimize-autoloader 2>&1 | tee -a "$LOG_FILE"
  else
    log "composer 未安装，跳过"
  fi
fi

# 如果有 npm 依赖（前端构建）
if [ -f "package.json" ]; then
  log "执行 npm install + 构建"
  npm install --omit=dev 2>&1 | tail -3 | tee -a "$LOG_FILE"
  if [ -f "package.json" ] && grep -q '"build"' package.json; then
    npm run build 2>&1 | tail -3 | tee -a "$LOG_FILE"
  fi
fi

# ========== restart ==========
if [ "$ACTION" = "deploy" ] || [ "$ACTION" = "restart" ]; then
  # 如果是 PHP 项目，宝塔会自动 reload php-fpm；这里可显式触发
  if command -v systemctl &>/dev/null; then
    log "reload php-fpm"
    systemctl reload php-fpm 2>/dev/null || true
  fi

  # 如果有 PM2 进程（Node.js 部分），重启
  if command -v pm2 &>/dev/null; then
    if pm2 describe "$SERVICE_NAME" &>/dev/null; then
      log "pm2 restart $SERVICE_NAME"
      pm2 restart "$SERVICE_NAME" --update-env
    fi
  fi

  # 如果有 nginx 站点，reload
  if command -v nginx &>/dev/null; then
    log "nginx reload"
    nginx -t 2>&1 | tee -a "$LOG_FILE" && nginx -s reload
  fi
fi

log "部署完成"
