#!/usr/bin/env bash
# post-to-wechat 服务器端部署脚本
# 用法：在服务器上执行 bash deploy.sh
# 会自动：检测环境 → clone 仓库（用 ghproxy 代理）→ npm install → 配置 .env → PM2 启动 → 输出验证命令
# 宝塔反向代理 + 微信 IP 白名单需手动配置（脚本末尾会提示）

set -euo pipefail

# ========== 配置 ==========
REPO="engrecho/publish-to-wechat-mp"
BRANCH="main"
GHPROXY="https://ghproxy.com"
INSTALL_DIR="/www/wwwroot/post-to-wechat"   # 宝塔默认站点目录，可改
SERVICE_NAME="wechat-publish"
PORT=8080

# ========== 颜色 ==========
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()   { echo -e "${RED}[ERR]${NC} $*"; exit 1; }

# ========== 步骤 1：检测环境 ==========
info "步骤 1/6：检测环境"

if ! command -v node &>/dev/null; then
  err "Node.js 未安装。请先用宝塔面板「软件商店 → Node.js 管理器」安装 Node.js 18+，或执行: curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt install -y nodejs"
fi

NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
  err "Node.js 版本过低 (当前 v$NODE_VERSION)，需要 18+。请升级。"
fi
ok "Node.js $(node -v)"

if ! command -v git &>/dev/null; then
  err "git 未安装。请执行: apt install -y git"
fi
ok "git $(git --version | awk '{print $3}')"

if ! command -v pm2 &>/dev/null; then
  warn "PM2 未安装，正在安装..."
  npm install -g pm2
fi
ok "PM2 $(pm2 --version)"

# ========== 步骤 2：clone / pull 仓库 ==========
info "步骤 2/6：拉取代码"

if [ -d "$INSTALL_DIR/.git" ]; then
  info "目录已存在，执行 git pull..."
  cd "$INSTALL_DIR"
  git fetch origin "$BRANCH"
  git reset --hard "origin/$BRANCH"
else
  info "首次部署，clone 仓库（使用 ghproxy 代理）..."
  mkdir -p "$(dirname "$INSTALL_DIR")"
  git clone "$GHPROXY/https://github.com/$REPO" "$INSTALL_DIR"
  cd "$INSTALL_DIR"
  git checkout "$BRANCH"
fi
ok "代码已更新到 $(git rev-parse --short HEAD)"

# ========== 步骤 3：安装依赖 ==========
info "步骤 3/6：安装服务器端依赖"
cd "$INSTALL_DIR/server"
npm install --omit=dev
ok "依赖安装完成"

# ========== 步骤 4：配置 .env ==========
info "步骤 4/6：配置 .env"
ENV_FILE="$INSTALL_DIR/server/.env"

if [ -f "$ENV_FILE" ]; then
  warn ".env 已存在，保留现有配置。如需重新配置，请先删除: rm $ENV_FILE"
else
  echo "请填入以下信息（按回车确认）："
  read -rp "WECHAT_APP_ID（微信公众号 AppID）: " WECHAT_APP_ID
  read -rp "WECHAT_APP_SECRET（微信公众号 AppSecret）: " WECHAT_APP_SECRET
  read -rp "PUBLISH_API_TOKEN（客户端访问本服务的 token，建议 32 位随机字符串，留空则自动生成）: " PUBLISH_API_TOKEN
  PUBLISH_API_TOKEN="${PUBLISH_API_TOKEN:-$(openssl rand -hex 16)}"

  cat > "$ENV_FILE" <<EOF
# 微信公众号 API 凭据
WECHAT_APP_ID=$WECHAT_APP_ID
WECHAT_APP_SECRET=$WECHAT_APP_SECRET

# 客户端访问本服务用的 API token
PUBLISH_API_TOKEN=$PUBLISH_API_TOKEN

# 监听端口
PORT=$PORT
EOF
  chmod 600 "$ENV_FILE"
  ok ".env 已生成"
  echo ""
  echo -e "${YELLOW}========================================${NC}"
  echo -e "${YELLOW}请记下以下信息（客户端 EXTEND.md 需要填）:${NC}"
  echo -e "${YELLOW}  server_publish_url: https://<你的域名>/publish${NC}"
  echo -e "${YELLOW}  server_publish_token: $PUBLISH_API_TOKEN${NC}"
  echo -e "${YELLOW}========================================${NC}"
fi

# ========== 步骤 5：PM2 启动 ==========
info "步骤 5/6：PM2 启动"
cd "$INSTALL_DIR/server"

if pm2 describe "$SERVICE_NAME" &>/dev/null; then
  warn "PM2 进程已存在，重启..."
  pm2 restart "$SERVICE_NAME" --update-env
else
  pm2 start index.js --name "$SERVICE_NAME"
fi
pm2 save
ok "PM2 服务已启动"

# ========== 步骤 6：验证 ==========
info "步骤 6/6：验证服务"
sleep 2

if curl -sf "http://127.0.0.1:$PORT/health" | grep -q '"ok":true'; then
  ok "健康检查通过：http://127.0.0.1:$PORT/health → {\"ok\":true}"
else
  err "健康检查失败，请检查日志: pm2 logs $SERVICE_NAME --lines 30"
fi

PM2_STATUS=$(pm2 jlist | grep -o "\"name\":\"$SERVICE_NAME\"[^}]*\"status\":\"[^\"]*\"" | grep -o '"status":"[^"]*"' | head -1)
ok "PM2 状态：$PM2_STATUS"

# ========== 总结 ==========
echo ""
echo -e "${GREEN}========== 部署完成 ==========${NC}"
echo ""
echo "本地服务已启动：http://127.0.0.1:$PORT"
echo ""
echo -e "${YELLOW}【还需手动完成的 3 件事】${NC}"
echo ""
echo "1. 微信公众号 IP 白名单："
echo "   登录 https://mp.weixin.qq.com → 设置与开发 → 基本配置 → IP 白名单"
echo "   添加本服务器出口 IP：$(curl -s https://ifconfig.me 2>/dev/null || echo '<查看服务器公网 IP>')"
echo ""
echo "2. 宝塔反向代理："
echo "   宝塔面板 → 网站 → 添加站点（域名如 tencent.bajiaolu.cn）→ 申请 SSL"
echo "   → 站点设置 → 反向代理 → 添加："
echo "     代理名称: wechat-publish"
echo "     目标URL:  http://127.0.0.1:$PORT"
echo "     发送域名: \$host"
echo ""
echo "3. 客户端配置 ~/.post-to-wechat/EXTEND.md："
echo "   default_publish_method: server-api"
echo "   server_publish_url: https://<你的域名>/publish"
echo "   server_publish_token: <上面显示的 PUBLISH_API_TOKEN>"
echo "   server_publish_timeout: 60"
echo ""
echo -e "${BLUE}【常用运维命令】${NC}"
echo "  查看日志:   pm2 logs $SERVICE_NAME"
echo "  重启服务:   pm2 restart $SERVICE_NAME"
echo "  停止服务:   pm2 stop $SERVICE_NAME"
echo "  查看状态:   pm2 status"
echo "  更新代码:   cd $INSTALL_DIR && git pull && cd server && npm install --omit=dev && pm2 restart $SERVICE_NAME"
echo ""
