import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
import random
import string


def generate_captcha(length: int = 6) -> str:
    """生成指定长度的数字验证码"""
    return ''.join(random.choices(string.digits, k=length))


async def send_email(to_email: str, subject: str, body: str) -> bool:
    """异步发送邮件"""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD or not settings.SMTP_FROM_EMAIL:
        print("邮件配置未设置，跳过发送")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            use_tls=True,
            timeout=10
        )
        
        return True
    except Exception as e:
        print(f"发送邮件失败: {e}")
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
