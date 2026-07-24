#!/usr/bin/env bash
# webhook 脚本安装器（一次性运行）
# 在服务器上执行：bash webhook/install-webhook.sh
# 会把 webhook/*.sh 安装到 /www/server/panel/script/，并初始化日志和 access_key

set -euo pipefail

SCRIPT_DIR="/www/server/panel/script"
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()   { echo -e "${RED}[ERR]${NC} $*"; exit 1; }

# 1. 创建脚本目录
mkdir -p "$SCRIPT_DIR"

# 2. 复制脚本
for f in webhook-router.sh deploy-aibuddy.sh deploy-wechat-mp.sh; do
  if [ ! -f "$SOURCE_DIR/$f" ]; then
    err "源文件不存在: $SOURCE_DIR/$f"
  fi
  cp "$SOURCE_DIR/$f" "$SCRIPT_DIR/$f"
  chmod +x "$SCRIPT_DIR/$f"
  info "已安装 $SCRIPT_DIR/$f"
done

# 3. 初始化 access_key 文件
ACCESS_KEY_FILE="$SCRIPT_DIR/.webhook-access-key"
if [ ! -f "$ACCESS_KEY_FILE" ]; then
  read -rp "请输入宝塔 webhook 的 access_key（从宝塔面板 webhook 配置页复制）: " ACCESS_KEY
  if [ -z "$ACCESS_KEY" ]; then
    warn "未输入 access_key，跳过鉴权（不推荐）。可稍后手动写入 $ACCESS_KEY_FILE"
  else
    echo -n "$ACCESS_KEY" > "$ACCESS_KEY_FILE"
    chmod 600 "$ACCESS_KEY_FILE"
    info "access_key 已写入 $ACCESS_KEY_FILE"
  fi
else
  info "access_key 已存在，跳过"
fi

# 4. 初始化日志文件
touch /var/log/webhook-deploy.log
chmod 644 /var/log/webhook-deploy.log
info "日志文件: /var/log/webhook-deploy.log"

# 5. 输出配置指引
echo ""
echo -e "${GREEN}========== 安装完成 ==========${NC}"
echo ""
echo "已安装的文件："
ls -l "$SCRIPT_DIR"/{webhook-router.sh,deploy-aibuddy.sh,deploy-wechat-mp.sh} 2>/dev/null
echo ""
echo -e "${YELLOW}【下一步：在宝塔面板配置 webhook】${NC}"
echo ""
echo "1. 登录宝塔面板 → 软件商店 → 安装「宝塔WebHook」插件"
echo "2. 打开 WebHook 插件 → 添加 hook"
echo "3. 填写："
echo "   名称:    deploy-router"
echo "   执行脚本: bash $SCRIPT_DIR/webhook-router.sh \"\$1\""
echo "           （注意 \$1 要转义，宝塔会自动传入 query string）"
echo "4. 保存后会获得一个 URL，形如："
echo "   https://tencent.bajiaolu.cn:11416/hook?access_key=<你的key>"
echo ""
echo -e "${YELLOW}【GitHub 仓库配置 Webhook】${NC}"
echo ""
echo "在每个 GitHub 仓库（engrecho/AI-buddy、engrecho/publish-to-wechat-mp）的"
echo "Settings → Webhooks → Add webhook 中填写："
echo ""
echo "  Payload URL: https://tencent.bajiaolu.cn:11416/hook?access_key=<key>&project=aibuddy"
echo "                （AI-buddy 仓库用 project=aibuddy）"
echo "  Payload URL: https://tencent.bajiaolu.cn:11416/hook?access_key=<key>&project=wechat-mp"
echo "                （publish-to-wechat-mp 仓库用 project=wechat-mp）"
echo "  Content type: application/json"
echo "  Which events: Just the push event"
echo ""
echo -e "${YELLOW}【手动触发测试】${NC}"
echo ""
echo "  curl 'https://tencent.bajiaolu.cn:11416/hook?access_key=<key>&project=wechat-mp&action=pull'"
echo "  curl 'https://tencent.bajiaolu.cn:11416/hook?access_key=<key>&project=wechat-mp&action=deploy'"
echo "  curl 'https://tencent.bajiaolu.cn:11416/hook?access_key=<key>&project=wechat-mp&action=restart'"
echo ""
echo -e "${YELLOW}【支持的参数】${NC}"
echo ""
echo "  project  必填，aibuddy / wechat-mp"
echo "  branch   可选，默认 main"
echo "  action   可选，deploy(默认) / pull / restart"
echo "  access_key 必填，与 $ACCESS_KEY_FILE 中一致"
echo ""
echo -e "${YELLOW}【日志查看】${NC}"
echo ""
echo "  tail -f /var/log/webhook-deploy.log"
