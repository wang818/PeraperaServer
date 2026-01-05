from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class FontSize(str, enum.Enum):
    SMALL = "small"
    REGULAR = "regular"
    MEDIUM = "medium"
    LARGE = "large"


class ZhCharacter(str, enum.Enum):
    SIMPLIFIED = "simplified"
    TRADITIONAL = "traditional"


class Theme(str, enum.Enum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


class UserSetting(Base):
    """User settings model."""
    
    __tablename__ = "users_setting"
    
    id = Column(Integer, primary_key=True, index=True)
    user_uuid = Column(UUID(as_uuid=True), unique=True, index=True, nullable=False)
    
    app_lang = Column(String, default="en", nullable=False)
    app_explan_lang = Column(String, default="en", nullable=False)
    app_second_subtitle = Column(String, default="en", nullable=False)
    app_target_lang = Column(String, default="en", nullable=False)
    
    sub_youtube = Column(String, default="en", nullable=False)
    sub_second = Column(String, default="en", nullable=False)
    sub_both = Column(Boolean, default=True, nullable=False)
    sub_font_size = Column(Enum(FontSize), default=FontSize.REGULAR, nullable=False)
    sub_focus_mode = Column(Boolean, default=False, nullable=False)
    sub_jp_romaji = Column(Boolean, default=True, nullable=False)
    sub_jp_furigana = Column(Boolean, default=True, nullable=False)
    sub_jp_speech_part = Column(Boolean, default=True, nullable=False)
    sub_jp_semantic = Column(Boolean, default=True, nullable=False)
    sub_jp_gaya = Column(Boolean, default=True, nullable=False)
    sub_zh_pinyin = Column(Boolean, default=True, nullable=False)
    sub_zh_character = Column(Enum(ZhCharacter), default=ZhCharacter.SIMPLIFIED, nullable=False)
    
    echo_listen = Column(Boolean, default=False, nullable=False)
    echo_echo = Column(Boolean, default=False, nullable=False)
    echo_delay = Column(Boolean, default=False, nullable=False)
    echo_speak = Column(Boolean, default=False, nullable=False)
    echo_play = Column(Boolean, default=False, nullable=False)
    
    theme = Column(Enum(Theme), default=Theme.SYSTEM, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
