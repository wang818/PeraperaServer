from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.core.database import Base


class CaptchaRecord(Base):
    """验证码发送记录模型"""
    __tablename__ = "captcha_records"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    captcha = Column(String, nullable=False)
    send_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
