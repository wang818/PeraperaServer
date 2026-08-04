from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.core.email import generate_captcha, send_captcha_email
from app.core.config import settings
from app.models.user import User
from app.models.captcha import CaptchaRecord
from app.models.user_setting import UserSetting
from app.schemas.user import Token, CaptchaLogin
from app.core.dependencies import get_language
from app.core.i18n import get_translation
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class OptionalHTTPBearer(HTTPBearer):
    """
    HTTPBearer that works with or without the 'Bearer ' prefix.

    Swagger UI → paste just the raw token into the authorize dialog.
    curl       → both ``Authorization: Bearer <token>`` and
                 ``Authorization: <token>`` are accepted.
    """

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:
        authorization = request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )

        scheme, _, credentials = authorization.partition(" ")
        if scheme.lower() == "bearer":
            return HTTPAuthorizationCredentials(scheme="Bearer", credentials=credentials)

        # No "Bearer " prefix — treat the whole header value as the token
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=authorization)


oauth2_scheme = OptionalHTTPBearer()


@router.post("/login", response_model=Token)
async def login_with_captcha(
    login_data: CaptchaLogin,
    db: AsyncSession = Depends(get_db),
    lang: str = Depends(get_language)
):
    """使用邮箱和验证码登录，如果用户不存在则自动创建账户"""
    logger.info(f"尝试使用验证码登录: {login_data.email}, 语言: {lang}")
    
    # 验证验证码
    now = datetime.utcnow()

    # ── Apple 审核专用账号：固定验证码直接通过（无需先调用 sendCaptcha） ──
    is_review_account = (
        bool(settings.APPLE_REVIEW_EMAIL)
        and login_data.email == settings.APPLE_REVIEW_EMAIL
        and login_data.captcha == settings.APPLE_REVIEW_CAPTCHA
    )

    if not is_review_account:
        result = await db.execute(
            select(CaptchaRecord).where(
                and_(
                    CaptchaRecord.email == login_data.email,
                    CaptchaRecord.captcha == login_data.captcha,
                    CaptchaRecord.expires_at > now
                )
            ).order_by(CaptchaRecord.created_at.desc())
        )
        captcha_record = result.scalar_one_or_none()

        if not captcha_record:
            logger.warning(f"验证码无效或已过期: {login_data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=get_translation("invalid_or_expired_captcha", lang)
            )
    
    # 查询用户是否存在
    result = await db.execute(
        select(User).where(User.email == login_data.email)
    )
    user = result.scalar_one_or_none()
    
    # 如果用户不存在，自动创建账户
    if not user:
        logger.info(f"用户不存在，自动创建账户: {login_data.email}")
        
        # 生成用户名（使用邮箱前缀 + 随机数）
        import random
        email_prefix = login_data.email.split('@')[0]
        username = f"{email_prefix}_{random.randint(1000, 9999)}"
        
        # 确保用户名唯一
        while True:
            check_result = await db.execute(
                select(User).where(User.username == username)
            )
            if not check_result.scalar_one_or_none():
                break
            username = f"{email_prefix}_{random.randint(1000, 9999)}"
        
        # 创建新用户（使用随机密码，因为用户通过验证码登录）
        from app.core.security import get_password_hash
        random_password = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=32))
        
        user = User(
            email=login_data.email,
            username=username,
            hashed_password=get_password_hash(random_password),
            is_active=True,
            is_superuser=False
        )
        db.add(user)
        await db.flush()
        
        # 为新用户创建默认设置
        user_setting = UserSetting(
            user_uuid=user.uuid
        )
        db.add(user_setting)
        
        await db.commit()
        await db.refresh(user)
        logger.info(f"新用户创建成功: {user.email}, username: {user.username}")
    
    # 检查用户是否激活
    if not user.is_active:
        logger.warning(f"用户未激活: {login_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_translation("inactive_user", lang)
        )
    
    # 创建访问令牌
    access_token = create_access_token(data={"sub": str(user.id)})
    logger.info(f"登录成功: {user.email}")
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/sendCaptcha")
async def send_captcha(
    email: str,
    db: AsyncSession = Depends(get_db),
    lang: str = Depends(get_language)
):
    """发送验证码到指定邮箱，带频率限制"""
    from email_validator import validate_email, EmailNotValidError
    
    logger.info(f"请求发送验证码: {email}, 语言: {lang}")

    # ── Apple 审核专用账号：固定验证码、不发邮件、跳过频率限制 ──
    if settings.APPLE_REVIEW_EMAIL and email == settings.APPLE_REVIEW_EMAIL:
        logger.info(f"检测到 Apple 审核账号，使用固定验证码（不发邮件）: {email}")
        review_captcha = settings.APPLE_REVIEW_CAPTCHA
        review_expiry = datetime.utcnow() + timedelta(days=settings.APPLE_REVIEW_CAPTCHA_DAYS)
        captcha_record = CaptchaRecord(
            email=email,
            captcha=review_captcha,
            send_count=1,
            created_at=datetime.utcnow(),
            expires_at=review_expiry,
        )
        db.add(captcha_record)
        await db.commit()
        return {
            "message": "Apple 审核账号验证码已设置（固定值，未发送邮件）",
            "email": email,
            "send_count": 1,
        }

    # 验证邮箱格式
    try:
        validate_email(email)
    except EmailNotValidError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_translation("invalid_email_format", lang)
        )
    
    now = datetime.utcnow()
    
    # 查询该邮箱今天的发送记录
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(CaptchaRecord).where(
            and_(
                CaptchaRecord.email == email,
                CaptchaRecord.created_at >= today_start
            )
        ).order_by(CaptchaRecord.created_at.desc())
    )
    records = result.scalars().all()
    
    # 计算今天发送次数
    send_count = len(records)
    
    # 检查频率限制
    if send_count > 0:
        last_record = records[0]
        time_since_last = now - last_record.created_at
        
        if send_count < 3:
            # 前三次直接发送，无需等待
            pass
        elif 3 <= send_count < 5:
            # 3-5次，需要间隔15分钟
            if time_since_last < timedelta(minutes=15):
                wait_seconds = int((timedelta(minutes=15) - time_since_last).total_seconds())
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=get_translation("wait_before_requesting", lang, seconds=wait_seconds)
                )
        else:
            # 5次以后，需要间隔1小时
            if time_since_last < timedelta(hours=1):
                wait_seconds = int((timedelta(hours=1) - time_since_last).total_seconds())
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=get_translation("wait_before_requesting", lang, seconds=wait_seconds)
                )
    
    # 生成6位验证码
    captcha = generate_captcha(6)
    
    # 发送邮件
    email_sent = await send_captcha_email(email, captcha, lang)
    
    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_translation("failed_to_send_email", lang)
        )
    
    # 保存验证码记录
    captcha_record = CaptchaRecord(
        email=email,
        captcha=captcha,
        send_count=send_count + 1,
        created_at=now,
        expires_at=now + timedelta(minutes=10)
    )
    db.add(captcha_record)
    await db.commit()
    
    return {
        "message": get_translation("captcha_sent_successfully", lang),
        "email": email,
        "send_count": send_count + 1
    }


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    lang: str = Depends(get_language)
) -> User:
    """Get current authenticated user."""
    from app.core.security import decode_access_token

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=get_translation("could_not_validate_credentials", lang),
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user
