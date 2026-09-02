#!/bin/bash

# 部署脚本 - Perapera Server
# 使用方法: bash deploy.sh

set -e

echo "=== Perapera Server 部署脚本 ==="

# 配置变量
PROJECT_NAME="PeraperaServer"
DEPLOY_USER="www-data"
DEPLOY_PATH="/var/www/$PROJECT_NAME"
REPO_URL="git@github.com:wang818/PeraperaServer.git"  # 修改为你的 Git 仓库地址

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then 
    echo_error "请使用 root 用户或 sudo 运行此脚本"
    exit 1
fi

# 1. 安装系统依赖
echo_info "安装系统依赖..."
yum install -y python3 python3-pip python3-devel postgresql-devel gcc nginx

# 2. 创建部署用户（如果不存在）
if ! id "$DEPLOY_USER" &>/dev/null; then
    echo_info "创建部署用户: $DEPLOY_USER"
    useradd -r -s /bin/bash -d /var/www $DEPLOY_USER
fi

# 3. 创建部署目录
echo_info "创建部署目录: $DEPLOY_PATH"
mkdir -p $DEPLOY_PATH
cd $DEPLOY_PATH

# 4. 克隆或更新代码
if [ -d "$DEPLOY_PATH/.git" ]; then
    echo_info "更新代码..."
    # 用 fetch + rebase 代替 git pull --rebase：
    # 仓库配置了 pull.rebase=true 时 git pull origin main 会报
    # "Cannot rebase onto multiple branches"。分开执行不受影响。
    git fetch origin main
    git rebase origin/main
else
    echo_info "克隆代码..."
    # git clone $REPO_URL $DEPLOY_PATH
    echo_warn "请手动上传代码到 $DEPLOY_PATH"
fi

# 5. 创建虚拟环境
echo_info "创建 Python 虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 6. 安装 Python 依赖
echo_info "安装 Python 依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 7. 配置环境变量
if [ ! -f "$DEPLOY_PATH/.env" ]; then
    echo_warn ".env 文件不存在，请创建并配置"
    if [ -f "$DEPLOY_PATH/.env.example" ]; then
        cp .env.example .env
        echo_info "已从 .env.example 创建 .env 文件，请修改配置"
    fi
fi

# 8. 设置文件权限
echo_info "设置文件权限..."
chown -R $DEPLOY_USER:$DEPLOY_USER $DEPLOY_PATH
chmod -R 755 $DEPLOY_PATH

# 9. 配置 systemd 服务
echo_info "配置 systemd 服务..."
cp $DEPLOY_PATH/deploy/perapera.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable perapera.service

# 10. 部署 SSL 证书（使用 acme.sh 签发的证书）
echo_info "部署 SSL 证书..."
ACME_HOME="${ACME_HOME:-/root/.acme.sh}"
ACME_CERT_DIR="$ACME_HOME/perapera.cc_ecc"
SSL_DIR="/etc/nginx/ssl/perapera.cc"

if [ ! -f "$ACME_CERT_DIR/fullchain.cer" ]; then
    echo_error "未找到 acme.sh 证书: $ACME_CERT_DIR/fullchain.cer"
    echo_error "也可通过环境变量 ACME_CERT_DIR 指定证书目录"
    exit 1
fi

mkdir -p $SSL_DIR
# 复制 fullchain（证书链）与私钥。nginx 建议私钥 600、证书 644
install -m 644 "$ACME_CERT_DIR/fullchain.cer" "$SSL_DIR/fullchain.cer"
install -m 644 "$ACME_CERT_DIR/ca.cer" "$SSL_DIR/ca.cer"
install -m 600 "$ACME_CERT_DIR/perapera.cc.key" "$SSL_DIR/perapera.cc.key"
chown -R root:root "$SSL_DIR"

# 11. 配置 Nginx
echo_info "配置 Nginx..."
cp $DEPLOY_PATH/deploy/perapera.conf /etc/nginx/conf.d/perapera.conf
nginx -t

# 12. 启动服务
echo_info "启动服务..."
systemctl restart perapera.service
systemctl restart nginx

# 13. 检查服务状态
echo_info "检查服务状态..."
systemctl status perapera.service --no-pager
systemctl status nginx --no-pager

echo_info "=== 部署完成 ==="
echo_info "应用地址: https://perapera.cc"
echo_info "API 文档: https://perapera.cc/docs"
echo_info ""
echo_warn "请确保："
echo_warn "1. 修改 .env 文件中的配置"
echo_warn "2. 域名 DNS 已正确解析到服务器 IP"
echo_warn "3. 配置防火墙开放 80/443 端口"

# 14. 发送部署完成通知邮件（最佳努力，失败不影响部署结果）
echo_info "发送部署完成通知邮件..."
if [ -f "$DEPLOY_PATH/venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$DEPLOY_PATH/venv/bin/activate"
    ( cd "$DEPLOY_PATH" && python "$DEPLOY_PATH/scripts/notify_deploy.py" \
        --to "${DEPLOY_NOTIFY_EMAIL:-wangjianvip83@gmail.com}" ) \
        || echo_warn "部署通知邮件发送失败（不影响部署结果）"
    deactivate 2>/dev/null || true
else
    echo_warn "未找到虚拟环境，跳过部署通知邮件"
fi
