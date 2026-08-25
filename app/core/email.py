import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
import random
import string
import json
import logging

logger = logging.getLogger(__name__)


def generate_captcha(length: int = 6) -> str:
    """生成指定长度的数字验证码"""
    return ''.join(random.choices(string.digits, k=length))


async def send_email_ses(to_email: str, subject: str, template_id: int, template_data: dict) -> bool:
    """通过腾讯云 SES SendEmail API 发送（模板方式）"""
    try:
        from tencentcloud.common import credential
        from tencentcloud.common.profile.client_profile import ClientProfile
        from tencentcloud.common.profile.http_profile import HttpProfile
        from tencentcloud.ses.v20201002 import ses_client, models
    except ImportError:
        logger.warning("未安装 tencentcloud-sdk-python，无法走 SES")
        return False

    if not (settings.SES_SECRET_ID and settings.SES_SECRET_KEY and settings.SES_FROM_EMAIL):
        logger.warning("SES 配置不完整（SES_SECRET_ID/SES_SECRET_KEY/SES_FROM_EMAIL），跳过 SES")
        return False

    try:
        cred = credential.Credential(settings.SES_SECRET_ID, settings.SES_SECRET_KEY)
        http_profile = HttpProfile()
        http_profile.endpoint = "ses.tencentcloudapi.com"
        client_profile = ClientProfile()
        client_profile.httpProfile = http_profile
        client = ses_client.SesClient(cred, settings.SES_REGION, client_profile)

        req = models.SendEmailRequest()
        req.FromEmailAddress = settings.SES_FROM_EMAIL
        req.Subject = subject
        req.Destination = [to_email]
        req.TriggerType = 1  # 触发类邮件（验证码）

        req.Template = models.Template()
        req.Template.TemplateID = template_id
        req.Template.TemplateData = json.dumps(template_data)

        resp = client.SendEmail(req)
        logger.info(f"SES 发送成功 -> {to_email}, TemplateID={template_id}, MessageId={resp.MessageId}")
        return True
    except Exception as e:
        logger.error(f"SES 发送失败: {type(e).__name__}: {e}", exc_info=True)
        return False


async def send_email(to_email: str, subject: str, body: str) -> bool:
    """异步发送邮件"""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD or not settings.SMTP_FROM_EMAIL:
        logger.warning("邮件配置未设置，跳过发送")
        return False
    
    logger.info(f"准备发送邮件到: {to_email}, 主题: {subject}")
    logger.debug(f"SMTP配置 - Host: {settings.SMTP_HOST}, Port: {settings.SMTP_PORT}, User: {settings.SMTP_USER}")
    
    try:
        msg = MIMEMultipart()
        msg['From'] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        logger.debug("邮件内容已构建完成")
        
        # 尝试使用 STARTTLS (端口 587)
        try:
            logger.info(f"尝试通过 STARTTLS 连接 {settings.SMTP_HOST}:{settings.SMTP_PORT}")
            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                start_tls=True,
                timeout=15
            )
            logger.info(f"邮件发送成功 (STARTTLS 587) -> {to_email}")
            return True
        except Exception as e1:
            logger.warning(f"STARTTLS (587) 发送失败: {type(e1).__name__}: {e1}")
            
            # 如果 587 失败，尝试使用 SSL (端口 465)
            try:
                logger.info(f"尝试通过 SSL 连接 {settings.SMTP_HOST}:465")
                await aiosmtplib.send(
                    msg,
                    hostname=settings.SMTP_HOST,
                    port=465,
                    username=settings.SMTP_USER,
                    password=settings.SMTP_PASSWORD,
                    use_tls=True,
                    timeout=15
                )
                logger.info(f"邮件发送成功 (SSL 465) -> {to_email}")
                return True
            except Exception as e2:
                logger.error(f"SSL (465) 发送也失败: {type(e2).__name__}: {e2}")
                return False
        
    except Exception as e:
        logger.error(f"发送邮件失败: {type(e).__name__}: {e}", exc_info=True)
        return False


async def send_captcha_email(to_email: str, captcha: str, lang: str = "en") -> bool:
    """发送验证码邮件：优先腾讯云 SES（模板方式），失败回退 SMTP"""
    from app.core.i18n import get_translation
    
    subject = get_translation("email_subject_captcha", lang)
    
    # ── 优先走 SES SendEmail API（个人实名账号 SMTP 发不出去）──
    template_id = None
    if settings.SES_TEMPLATE_IDS:
        try:
            template_map = json.loads(settings.SES_TEMPLATE_IDS)
            template_id = template_map.get(lang)
        except json.JSONDecodeError:
            logger.warning(f"SES_TEMPLATE_IDS 解析失败: {settings.SES_TEMPLATE_IDS}")

    if template_id:
        template_data = {
            "app_name": settings.APP_NAME or settings.SMTP_FROM_NAME,
            "captcha": captcha,
        }
        sent = await send_email_ses(to_email, subject, int(template_id), template_data)
        if sent:
            return True
        logger.warning(f"SES 发送失败，回退 SMTP: {to_email}")

    # ── 回退：SMTP 直发 ──
    body = f"""
    <html>
        <body>
            <h2>{get_translation("email_captcha_title", lang)}</h2>
            <p>{get_translation("email_captcha_body", lang, captcha=captcha, app_name=settings.APP_NAME or settings.SMTP_FROM_NAME)}</p>
            <p>{get_translation("email_captcha_validity", lang)}</p>
            <br>
            <p>{get_translation("email_captcha_ignore", lang)}</p>
        </body>
    </html>
    """
    return await send_email(to_email, subject, body)
