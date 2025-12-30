from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.core.email import generate_captcha, send_captcha_email
from app.models.user import User
from app.models.captcha import CaptchaRecord
from app.schemas.user import Token

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Login endpoint to get access token."""
    # Query user by username
    result = await db.execute(
        select(User).where(User.username == form_data.username)
    )
    user = result.scalar_one_or_none()
    
    # Verify user and password
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/sendCaptcha")
async def send_captcha(
    email: str,
    db: AsyncSession = Depends(get_db)
):
    """发送验证码到指定邮箱，带频率限制"""
    from email_validator import validate_email, EmailNotValidError
    
    # 验证邮箱格式
    try:
        validate_email(email)
    except EmailNotValidError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
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
                    detail=f"Please wait {wait_seconds} seconds before requesting another captcha"
                )
        else:
            # 5次以后，需要间隔1小时
            if time_since_last < timedelta(hours=1):
                wait_seconds = int((timedelta(hours=1) - time_since_last).total_seconds())
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Please wait {wait_seconds} seconds before requesting another captcha"
                )
    
    # 生成6位验证码
    captcha = generate_captcha(6)
    
    # 发送邮件
    email_sent = await send_captcha_email(email, captcha)
    
    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send email"
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
        "message": "Captcha sent successfully",
        "email": email,
        "send_count": send_count + 1
    }


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    from app.core.security import decode_access_token
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_access_token(token)
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
