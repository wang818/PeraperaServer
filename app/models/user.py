from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class User(Base):
    """User model."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, index=True, default=uuid.uuid4, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ── 订阅 / 字幕识别时长配额字段 ──
    # 年卡过期时间（cc.perapera.pro.yearly 充值后设置）
    annual_expire_at = Column(DateTime(timezone=True), nullable=True)
    # 月卡过期时间（cc.perapera.pro.monthly 充值后设置）
    monthly_expire_at = Column(DateTime(timezone=True), nullable=True)
    # 点卡时长（单位：分钟），cc.perapera.base.monthly 每次充值 +180 分钟
    point_card_minutes = Column(Integer, default=0, nullable=False)
    # 月卡时长（单位：分钟），月卡充值时设为 1800，年卡有效且月卡过期时补充 1800
    monthly_card_minutes = Column(Integer, default=0, nullable=False)
