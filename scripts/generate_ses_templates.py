#!/usr/bin/env python3
"""生成腾讯云 SES 控制台邮件模板（每语言一个 HTML 模板）。

背景：个人实名认证的 SES 账号无法走 SMTP 发信，必须走 SendEmail API，
而 API 只接受「控制台模板 + TemplateData」，且 TemplateData 值不能含 HTML。
因此方案是：每种语言一个控制台模板，模板内只有 {{captcha}} 一个变量，
其余文案（标题/正文/有效期/忽略提示）全部烘焙进模板，TemplateData = {"captcha": "123456"}。

用法：
    python3 scripts/generate_ses_templates.py

输出：
    scripts/ses_templates/<lang>.html   — 每语言一个模板文件

步骤：
    1. 运行本脚本生成模板文件
    2. 到 SES 控制台 → 邮件模板 → 创建模板，逐个粘贴文件内容（类型选 HTML）
    3. 创建后记下每个模板的 TemplateID，填入 .env 的 SES_TEMPLATE_IDS（JSON 映射）
"""
import sys
from pathlib import Path
from string import Template

# 允许从项目根目录导入 app 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402
from app.core.i18n import Language, get_translation  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent / "ses_templates"
STRUCTURE_FILE = Path(__file__).resolve().parent.parent / "app" / "templates" / "email_captcha.html"

# 验证码高亮样式（与控制台模板变量 {{captcha}} 对应）
CAPTCHA_SPAN = '<span style="font-size:24px;font-weight:700;color:#0a6cff;">{{captcha}}</span>'


def render_console_template(lang: str) -> str:
    """渲染单个语言的 SES 控制台模板 HTML"""
    structure = Template(STRUCTURE_FILE.read_text(encoding="utf-8"))
    body_sentence = get_translation("email_captcha_body", lang).replace("{captcha}", CAPTCHA_SPAN)
    return structure.substitute(
        app_name=settings.APP_NAME or settings.SMTP_FROM_NAME,
        title=get_translation("email_captcha_title", lang),
        body=body_sentence,
        validity=get_translation("email_captcha_validity", lang),
        ignore=get_translation("email_captcha_ignore", lang),
    )


def main() -> None:
    if not STRUCTURE_FILE.exists():
        print(f"错误: 模板结构文件不存在: {STRUCTURE_FILE}", file=sys.stderr)
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    languages = [e.value for e in Language]

    print(f"生成 {len(languages)} 个模板到 {OUT_DIR}/\n")
    for lang in languages:
        path = OUT_DIR / f"{lang}.html"
        path.write_text(render_console_template(lang), encoding="utf-8")
        print(f"  ✓ {path.name}")

    print("\n下一步:")
    print("  1. SES 控制台 → 邮件模板 → 创建模板（类型: HTML），逐个粘贴以上文件内容")
    print("  2. 每个模板创建后记下 TemplateID")
    print("  3. 填入 .env 的 SES_TEMPLATE_IDS，例如:")
    sample = ",".join(f'"{lang}":0' for lang in languages)
    print(f'     SES_TEMPLATE_IDS={{{sample}}}')
    print("     （把 0 替换为实际 TemplateID；语言键必须与上面文件名一致）")
    print("  4. 模板审核通过后即可用 SendEmail 发信（app 代码已就绪）")


if __name__ == "__main__":
    main()
