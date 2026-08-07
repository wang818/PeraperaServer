#!/usr/bin/env python3
"""
部署完成后发送通知邮件。

线上部署脚本 (deploy/deploy.sh) 在部署成功后调用本脚本，
向指定收件人发送一封「部署完成」通知邮件。

用法:
  python scripts/notify_deploy.py [--to 收件人] [--extra "额外说明"]

收件人优先级:
  1. 命令行参数 --to
  2. 环境变量 DEPLOY_NOTIFY_EMAIL
  3. 默认 wangjianvip83@gmail.com

依赖项目根目录的 .env（SMTP_* 配置）与可用的 git 仓库。
"""
import argparse
import asyncio
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 添加项目根目录到 Python 路径（与 init_db.py 保持一致）
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.email import send_email
from app.core.config import settings

DEFAULT_RECIPIENT = "wangjianvip83@gmail.com"
APP_URL = getattr(settings, "APP_BASE_URL", "https://perapera.cc")


def _git(rev: list[str]) -> str:
    """执行 git 命令并返回 stdout 去除空白；失败返回空串。"""
    try:
        return subprocess.run(
            ["git", *rev],
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
    except Exception:
        return ""


def _version_info() -> str:
    commit = _git(["rev-parse", "--short", "HEAD"])
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"])
    parts = []
    if branch:
        parts.append(f"分支 {branch}")
    if commit:
        parts.append(f"提交 {commit}")
    return " / ".join(parts)


def build_body(extra: str, version: str) -> str:
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S (GMT+8)")
    version_line = f"<li>版本：{version}</li>" if version else ""
    extra_line = f"<p>备注：{extra}</p>" if extra else ""
    return f"""
    <html>
      <body style="font-family: -apple-system, Segoe UI, Roboto, sans-serif; color:#222;">
        <h2>Perapera Server 部署完成</h2>
        <p>线上部署已成功完成，服务已重启并对外提供访问。</p>
        <ul>
          <li>部署时间：{now}</li>
          {version_line}
          <li>应用地址：<a href="{APP_URL}">{APP_URL}</a></li>
          <li>服务：perapera.service / nginx</li>
        </ul>
        {extra_line}
        <p style="color:#888;font-size:12px;">本邮件由部署脚本自动发送，无需回复。</p>
      </body>
    </html>
    """


async def main(to: str, extra: str) -> int:
    version = _version_info()
    subject = "Perapera Server 部署完成"
    body = build_body(extra, version)
    ok = await send_email(to, subject, body)
    if ok:
        print(f"[OK] 部署通知邮件已发送至 {to}")
        return 0
    print(f"[WARN] 部署通知邮件发送失败（收件人 {to}），请检查 SMTP 配置", file=sys.stderr)
    return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="部署完成后发送通知邮件")
    parser.add_argument(
        "--to",
        default=os.getenv("DEPLOY_NOTIFY_EMAIL", DEFAULT_RECIPIENT),
        help="收件人邮箱（默认 wangjianvip83@gmail.com）",
    )
    parser.add_argument("--extra", default="", help="额外说明，会显示在邮件正文中")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.to, args.extra)))
