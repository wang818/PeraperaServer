import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
import random
import string
import logging

logger = logging.getLogger(__name__)


def generate_captcha(length: int = 6) -> str:
    """生成指定长度的数字验证码"""
    return ''.join(random.choices(string.digits, k=length))


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


async def send_captcha_email(to_email: str, captcha: str) -> bool:
    """发送验证码邮件"""
    subject = "您的验证码"
    body = f"""
    <html>
        <body>
            <h2>验证码</h2>
            <p>您的验证码是: <strong style="font-size: 24px; color: #007bff;">{captcha}</strong></p>
            <p>验证码有效期为10分钟，请勿泄露给他人。</p>
            <br>
            <p>如果这不是您的操作，请忽略此邮件。</p>
        </body>
    </html>
    """
    return await send_email(to_email, subject, body)
