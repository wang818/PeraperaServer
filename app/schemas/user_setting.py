from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.models.user_setting import FontSize, ZhCharacter, Theme


class UserSettingBase(BaseModel):
    """Base user setting schema."""
    app_lang: str = "en"
    app_explan_lang: str = "en"
    app_second_subtitle: str = "en"
    app_target_lang: str = "en"
    
    sub_youtube: str = "en"
    sub_second: str = "en"
    sub_both: bool = True
    sub_font_size: FontSize = FontSize.REGULAR
    sub_focus_mode: bool = False
    sub_jp_romaji: bool = True
    sub_jp_furigana: bool = True
    sub_jp_speech_part: bool = True
    sub_jp_semantic: bool = True
    sub_jp_gaya: bool = True
    sub_zh_pinyin: bool = True
    sub_zh_character: ZhCharacter = ZhCharacter.SIMPLIFIED
    
    echo_listen: bool = False
    echo_echo: bool = False
    echo_delay: bool = False
    echo_speak: bool = False
    echo_play: bool = False
    
    theme: Theme = Theme.SYSTEM


class UserSettingCreate(UserSettingBase):
    """Schema for creating user setting."""
    user_uuid: UUID


class UserSettingUpdate(BaseModel):
    """Schema for updating user setting."""
    app_lang: Optional[str] = None
    app_explan_lang: Optional[str] = None
    app_second_subtitle: Optional[str] = None
    app_target_lang: Optional[str] = None
    
    sub_youtube: Optional[str] = None
    sub_second: Optional[str] = None
    sub_both: Optional[bool] = None
    sub_font_size: Optional[FontSize] = None
    sub_focus_mode: Optional[bool] = None
    sub_jp_romaji: Optional[bool] = None
    sub_jp_furigana: Optional[bool] = None
    sub_jp_speech_part: Optional[bool] = None
    sub_jp_semantic: Optional[bool] = None
    sub_jp_gaya: Optional[bool] = None
    sub_zh_pinyin: Optional[bool] = None
    sub_zh_character: Optional[ZhCharacter] = None
    
    echo_listen: Optional[bool] = None
    echo_echo: Optional[bool] = None
    echo_delay: Optional[bool] = None
    echo_speak: Optional[bool] = None
    echo_play: Optional[bool] = None
    
    theme: Optional[Theme] = None


class UserSettingInDB(UserSettingBase):
    """Schema for user setting in database."""
    id: int
    user_uuid: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserSettingResponse(UserSettingBase):
    """Schema for user setting response."""
    id: int
    user_uuid: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True
