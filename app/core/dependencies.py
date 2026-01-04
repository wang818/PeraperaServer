from typing import Optional
from fastapi import Header
from app.core.i18n import get_language_from_header, Language


async def get_language(
    accept_language: Optional[str] = Header(None, alias="Accept-Language")
) -> str:
    """
    从请求头获取语言参数
    
    Args:
        accept_language: Accept-Language header
    
    Returns:
        语言代码 (en, zh, ja, ko)
    """
    return get_language_from_header(accept_language)
