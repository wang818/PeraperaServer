from fastapi import APIRouter
from app.core.support_lang import get_support_lang

router = APIRouter()


@router.get("/support_lang")
async def get_supported_languages():
    """Get list of supported languages."""
    return get_support_lang()
