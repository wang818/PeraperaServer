#!/usr/bin/env bash
#
# fix_da_ye_issues.sh
# ---------------------------------------------------------------------------
# 自动拉取当前仓库 label=DaYe 的 GitHub issue，把 issue 标题当作提示词交给
# reasonix 修复代码；验收标准为 python run.py 启动无报错，失败则再次调用
# reasonix 修复（最多 MAX_FIX_ATTEMPTS 次）。验收通过后自动 git commit 并
# push 到当前分支，关闭 issue 并写评论；最后复用 deploy/deploy.sh 的逻辑
# 直接发布上线。
#
# 用法:
#   sudo bash fix_da_ye_issues.sh
#
# 依赖:
#   - gh        已登录 (gh auth status)
#   - reasonix  CLI  (reasonix run --auto)
#   - python3 / venv
#
# 可选环境变量:
#   LABEL                目标 label            (默认 DaYe)
#   MAX_FIX_ATTEMPTS     reasonix 最大尝试次数 (默认 3)
#   VERIFY_TIMEOUT       验收时 run.py 最长运行秒数 (默认 45)
#   VERIFY_PORT          验收时使用的端口 (默认 18099，避开线上 8000)
#   REASONIX_CMD         reasonix 路径 (可选; 默认自动探测 reasonix 命令、
#                        npm 全局安装、~/.local/bin 等常见位置)
#   DEPLOY_NOTIFY_EMAIL  部署完成通知收件人   (默认 wangjianvip83@gmail.com)
#   ACME_HOME            acme.sh 安装目录     (默认 /root/.acme.sh)
#   ACME_CERT_DIR        acme.sh 证书目录     (默认 $ACME_HOME/perapera.cc_ecc；
#                        证书按 fullchain.cer + perapera.cc.key 读取)
# ---------------------------------------------------------------------------

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

LABEL="${LABEL:-DaYe}"
MAX_FIX_ATTEMPTS="${MAX_FIX_ATTEMPTS:-3}"
VERIFY_TIMEOUT="${VERIFY_TIMEOUT:-45}"
VERIFY_PORT="${VERIFY_PORT:-18099}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        log_error "缺少命令: $1"
        return 1
    fi
}

# 获取当前仓库的 owner/repo（优先 gh，失败时从 git remote 解析）
get_repo() {
    local repo
    repo="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || true)"
    if [ -z "$repo" ]; then
        repo="$(git remote get-url origin | sed -E 's#^([^@/]*@)?([^:/]+)[:/]([^/]+/[^/]+?)(\.git)?$#\3#')"
    fi
    if [ -z "$repo" ]; then
        log_error "无法确定 GitHub 仓库 (owner/repo)"
        return 1
    fi
    echo "$repo"
}

# 定位 reasonix 可执行文件；找不到则返回非零（不输出）
find_reasonix() {
    local candidate npm_prefix

    # 1) 显式指定的路径/命令
    if [ -n "${REASONIX_CMD:-}" ] && command -v "$REASONIX_CMD" >/dev/null 2>&1; then
        echo "$REASONIX_CMD"
        return 0
    fi

    # 2) 当前 PATH
    if command -v reasonix >/dev/null 2>&1; then
        command -v reasonix
        return 0
    fi

    # 3) 常见安装位置
    local candidates=(
        "/usr/local/bin/reasonix"
        "$HOME/.local/bin/reasonix"
        "$HOME/.reasonix/bin/reasonix"
        "$HOME/bin/reasonix"
        "$HOME/.cargo/bin/reasonix"
        "$HOME/go/bin/reasonix"
    )
    for candidate in "${candidates[@]}"; do
        if [ -x "$candidate" ]; then
            echo "$candidate"
            return 0
        fi
    done

    # 4) nvm 安装的 node 工具 (nvm 的 bin 通常不在 sudo 的 PATH 里)
    local nvm_dir="${NVM_DIR:-$HOME/.nvm}"
    local node_bin
    for node_bin in "$nvm_dir"/versions/node/*/bin/reasonix; do
        if [ -x "$node_bin" ]; then
            echo "$node_bin"
            return 0
        fi
    done

    # 5) npm 全局安装 (npm i -g reasonix)
    if command -v npm >/dev/null 2>&1; then
        npm_prefix="$(npm prefix -g 2>/dev/null || true)"
        if [ -n "$npm_prefix" ] && [ -x "$npm_prefix/bin/reasonix" ]; then
            echo "$npm_prefix/bin/reasonix"
            return 0
        fi
    fi

    # 6) sudo 场景: 检查调用者(SUDO_USER)的家目录，避免 sudo 后 PATH 变窄
    if [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != "root" ]; then
        local sudo_home
        sudo_home="$(getent passwd "$SUDO_USER" 2>/dev/null | cut -d: -f6 || true)"
        if [ -n "$sudo_home" ]; then
            local sub
            for sub in ".local/bin/reasonix" ".reasonix/bin/reasonix" "bin/reasonix" ".cargo/bin/reasonix" "go/bin/reasonix"; do
                if [ -x "$sudo_home/$sub" ]; then
                    echo "$sudo_home/$sub"
                    return 0
                fi
            done
            local node_bin2
            for node_bin2 in "$sudo_home"/.nvm/versions/node/*/bin/reasonix; do
                if [ -x "$node_bin2" ]; then
                    echo "$node_bin2"
                    return 0
                fi
            done
        fi
    fi

    return 1
}

# 调用 reasonix（非交互自动批准）
run_reasonix() {
    local prompt="$1"
    "$REASONIX_BIN" run --auto --dir "$PROJECT_DIR" "$prompt"
}

# 验收: 启动 python run.py，能稳定运行到超时被杀(退出码 124)即视为无报错。
# 使用独立端口避免与线上 8000 冲突；DEBUG=false 关闭 reload 子进程，让
# 启动报错立即以非零退出码暴露（若为 0/124 则启动成功）。
verify_app() {
    local log="$1"
    local py=""
    if [ -x "$PROJECT_DIR/venv/bin/python" ]; then
        py="$PROJECT_DIR/venv/bin/python"
    elif command -v python3 >/dev/null 2>&1; then
        py="$(command -v python3)"
    elif command -v python >/dev/null 2>&1; then
        py="$(command -v python)"
    else
        log_error "找不到 python 解释器"
        return 1
    fi

    log_info "验收: 启动 run.py (端口 ${VERIFY_PORT}, 最长 ${VERIFY_TIMEOUT}s) ..."
    timeout --kill-after=10s "${VERIFY_TIMEOUT}s" \
        env DEBUG=false PORT="$VERIFY_PORT" "$py" run.py >"$log" 2>&1
    local rc=$?

    if [ "$rc" -eq 124 ] || [ "$rc" -eq 0 ]; then
        if grep -Eiq "traceback \(most recent call last\)|application startup failed" "$log"; then
            log_error "验收失败: 日志中出现 Traceback / startup failed"
            return 1
        fi
        log_info "验收通过: python run.py 无报错"
        return 0
    fi

    log_error "验收失败: python run.py 退出码=${rc}"
    return 1
}

# 用 issue 标题作为提示词修复；验收失败则带上报错日志重试 reasonix
fix_one_issue() {
    local num="$1" title="$2" body="$3" log="$4"
    local attempt prompt

    for ((attempt = 1; attempt <= MAX_FIX_ATTEMPTS; attempt++)); do
        if [ "$attempt" -eq 1 ]; then
            prompt="你是本仓库的维护者。请阅读并解决下面的 GitHub issue，修改代码直到 python run.py 能正常启动。issue 标题: ${title}"
            if [ -n "$body" ]; then
                prompt="${prompt}"$'\n\n'"issue 描述:"$'\n'"${body}"
            fi
        else
            prompt="上一次修复后 python run.py 验收仍然失败。请根据报错日志继续修复该 issue。issue 标题: ${title}"
            prompt="${prompt}"$'\n\n'"最近报错日志:"$'\n'"$(tail -n 80 "$log")"
        fi

        log_info "[#${num}] 第 ${attempt}/${MAX_FIX_ATTEMPTS} 次调用 reasonix ..."
        if ! run_reasonix "$prompt"; then
            log_error "[#${num}] reasonix 执行失败"
            return 1
        fi

        if verify_app "$log"; then
            return 0
        fi
    done

    log_error "[#${num}] 连续 ${MAX_FIX_ATTEMPTS} 次尝试仍未通过验收"
    return 1
}

LAST_COMMIT_SHA=""

commit_and_push() {
    local num="$1" title="$2"
    local branch msg

    branch="$(git branch --show-current)"
    if [ -z "$branch" ]; then
        log_error "无法获取当前分支"
        return 1
    fi

    # 自动化提交需要 git 身份
    if ! git config user.email >/dev/null 2>&1; then
        git config user.email "reasonix-bot@perapera.cc"
        git config user.name "reasonix-bot"
        log_warn "未配置 git 身份, 已使用 reasonix-bot 作为默认提交者"
    fi

    git add -A
    if git diff --cached --quiet; then
        log_warn "[#${num}] 没有代码改动, 跳过提交与推送"
        LAST_COMMIT_SHA="$(git rev-parse HEAD)"
        return 0
    fi

    msg="fix: $(printf '%s' "$title" | tr '\n' ' ') (#${num})"
    git commit -m "$msg"

    # 先 rebase 拉取远端，避免 push 被拒
    if ! git pull --rebase origin "$branch"; then
        log_error "[#${num}] git pull --rebase 失败"
        return 1
    fi

    log_info "[#${num}] push 到 origin/${branch} ..."
    if ! git push origin "$branch"; then
        log_error "[#${num}] git push 失败"
        return 1
    fi

    LAST_COMMIT_SHA="$(git rev-parse HEAD)"
    return 0
}

close_issue() {
    local num="$1" title="$2"
    local branch comment

    branch="$(git branch --show-current)"
    comment="$(printf '✅ reasonix 已自动修复并验收通过（python run.py 无报错）。\n\n- issue: #%s %s\n- 分支: %s\n- 提交: %s\n\n由 fix_da_ye_issues.sh 自动处理并关闭。' \
        "$num" "$title" "$branch" "${LAST_COMMIT_SHA:-见分支 HEAD}")"

    log_info "[#${num}] 关闭 issue 并写评论 ..."
    gh issue close "$num" --repo "$REPO" --comment "$comment"
}

# 复用 deploy/deploy.sh 的逻辑，直接发布上线
deploy_release() {
    log_info "=== 开始发布上线 (复用 deploy/deploy.sh 的逻辑) ==="

    if [ "$EUID" -ne 0 ]; then
        log_error "发布上线需要 root 权限, 请使用: sudo bash fix_da_ye_issues.sh"
        return 1
    fi

    local DEPLOY_USER="www-data"
    local branch
    branch="$(git branch --show-current)"

    # 1. 安装系统依赖
    log_info "安装系统依赖..."
    yum install -y python3 python3-pip python3-devel postgresql-devel gcc nginx

    # 2. 创建部署用户（如果不存在）
    if ! id "$DEPLOY_USER" &>/dev/null; then
        log_info "创建部署用户: $DEPLOY_USER"
        useradd -r -s /bin/bash -d /var/www "$DEPLOY_USER"
    fi

    # 3. 部署目录
    log_info "部署目录: $PROJECT_DIR"
    mkdir -p "$PROJECT_DIR"
    cd "$PROJECT_DIR"

    # 4. 更新代码
    if [ -d "$PROJECT_DIR/.git" ]; then
        log_info "更新代码 (git pull origin ${branch}) ..."
        git pull origin "$branch"
    else
        log_error "$PROJECT_DIR 不是 git 仓库, 无法部署"
        return 1
    fi

    # 5. 创建虚拟环境
    log_info "准备 Python 虚拟环境..."
    python3 -m venv venv
    # shellcheck disable=SC1091
    source venv/bin/activate

    # 6. 安装 Python 依赖
    log_info "安装 Python 依赖..."
    pip install --upgrade pip
    pip install -r requirements.txt

    # 7. 配置环境变量
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        log_warn ".env 文件不存在, 从 .env.example 复制"
        if [ -f "$PROJECT_DIR/.env.example" ]; then
            cp .env.example .env
        fi
    fi

    # 8. 设置文件权限
    log_info "设置文件权限..."
    chown -R "$DEPLOY_USER":"$DEPLOY_USER" "$PROJECT_DIR"
    chmod -R 755 "$PROJECT_DIR"

    # 9. 配置 systemd 服务
    log_info "配置 systemd 服务..."
    cp "$PROJECT_DIR/deploy/perapera.service" /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable perapera.service

    # 10. 部署 SSL 证书（使用 acme.sh 签发的证书）
    log_info "部署 SSL 证书..."
    local ACL="${ACME_HOME:-/root/.acme.sh}/perapera.cc_ecc"
    if [ -n "${ACME_CERT_DIR:-}" ]; then
        ACL="$ACME_CERT_DIR"
    fi
    local SSL_DIR="/etc/nginx/ssl/perapera.cc"

    if [ ! -f "$ACL/fullchain.cer" ]; then
        log_error "未找到 acme.sh 证书: $ACL/fullchain.cer"
        log_error "也可通过环境变量 ACME_CERT_DIR 指定证书目录"
        return 1
    fi

    mkdir -p "$SSL_DIR"
    # 复制 fullchain（证书链）与私钥。nginx 建议私钥 600、证书 644
    install -m 644 "$ACL/fullchain.cer" "$SSL_DIR/fullchain.cer"
    install -m 644 "$ACL/ca.cer" "$SSL_DIR/ca.cer"
    install -m 600 "$ACL/perapera.cc.key" "$SSL_DIR/perapera.cc.key"
    chown -R root:root "$SSL_DIR"

    # 11. 配置 Nginx
    log_info "配置 Nginx..."
    cp "$PROJECT_DIR/deploy/perapera.conf" /etc/nginx/conf.d/perapera.conf
    nginx -t

    # 12. 启动服务
    log_info "启动服务..."
    systemctl restart perapera.service
    systemctl restart nginx

    # 13. 检查服务状态
    log_info "检查服务状态..."
    systemctl status perapera.service --no-pager
    systemctl status nginx --no-pager

    log_info "应用地址: https://perapera.cc"
    log_info "API 文档: https://perapera.cc/docs"

    # 14. 发送部署完成通知邮件（最佳努力, 失败不影响部署结果）
    log_info "发送部署完成通知邮件..."
    if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
        # shellcheck disable=SC1091
        source "$PROJECT_DIR/venv/bin/activate"
        ( cd "$PROJECT_DIR" && python "$PROJECT_DIR/scripts/notify_deploy.py" \
            --to "${DEPLOY_NOTIFY_EMAIL:-wangjianvip83@gmail.com}" ) \
            || log_warn "部署通知邮件发送失败（不影响部署结果）"
        deactivate 2>/dev/null || true
    else
        log_warn "未找到虚拟环境, 跳过部署通知邮件"
    fi

    log_info "=== 发布上线完成 ==="
}

main() {
    require_cmd gh || exit 1
    require_cmd git || exit 1
    require_cmd timeout || exit 1

    if ! REASONIX_BIN="$(find_reasonix)"; then
        log_error "找不到 reasonix 命令"
        log_error "  1) 安装 CLI: npm i -g reasonix  (或从官方下载页安装)"
        log_error "  2) 或指定路径后重跑: sudo -E env REASONIX_CMD=/path/to/reasonix bash fix_da_ye_issues.sh"
        exit 1
    fi
    log_info "使用 reasonix: $REASONIX_BIN"

    if [ ! -x "$PROJECT_DIR/venv/bin/python" ] \
        && ! command -v python3 >/dev/null 2>&1 \
        && ! command -v python >/dev/null 2>&1; then
        log_error "缺少 python 解释器"
        exit 1
    fi

    REPO="$(get_repo)" || exit 1
    log_info "GitHub 仓库: $REPO"
    log_info "当前分支: $(git branch --show-current)"

    local issue_list
    issue_list="$(gh issue list --repo "$REPO" --label "$LABEL" --state open \
        --json number --jq '.[].number')" || {
        log_error "gh 拉取 issue 失败, 请确认 gh 已登录且有仓库权限"
        exit 1
    }

    if [ -z "$issue_list" ]; then
        log_info "没有 label=${LABEL} 的 open issue, 无需处理"
        return 0
    fi

    local verify_log
    verify_log="$(mktemp /tmp/perapera-verify.XXXXXX.log)"
    trap 'rm -f "$verify_log"' EXIT

    local num title body
    while IFS= read -r num; do
        [ -n "$num" ] || continue

        log_info "---------------------------------------------"
        log_info "开始处理 issue #${num}"

        title="$(gh issue view "$num" --repo "$REPO" --json title -q .title)" || {
            log_error "拉取 issue #${num} 标题失败"
            exit 1
        }
        body="$(gh issue view "$num" --repo "$REPO" --json body -q .body || true)"

        log_info "issue 标题: $title"

        if ! fix_one_issue "$num" "$title" "$body" "$verify_log"; then
            log_error "issue #${num} 修复未达标, 中止流程 (不发布上线)"
            exit 1
        fi

        if ! commit_and_push "$num" "$title"; then
            log_error "issue #${num} 提交/推送失败, 中止流程"
            exit 1
        fi

        if ! close_issue "$num" "$title"; then
            log_error "关闭 issue #${num} 失败, 中止流程"
            exit 1
        fi
    done <<< "$issue_list"

    log_info "所有 label=${LABEL} 的 issue 处理完成"
    deploy_release
}

main "$@"
