"""
Free Quota Service — 免费用户月度时长管理。

每月1号定时任务：清空免费用户的月卡 token（monthly_card_minutes），
再赠送 FREE_MONTHLY_MINUTES 分钟的免费月卡时长。

免费用户定义：月卡（monthly_expire_at）与年卡（annual_expire_at）均为空或已过期。

本模块只 `add` / 修改字段，不 `commit` —— 由调用方（scheduler 任务）统一提交。
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User
from app.services import business_service

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_active(expires_at) -> bool:
    """判断过期时间是否仍有效（未过期）。"""
    if expires_at is None:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at > _now()


def is_free_user(user: User) -> bool:
    """判断用户是否为免费用户（无有效月卡且无有效年卡）。"""
    return (not _is_active(user.monthly_expire_at)) and (not _is_active(user.annual_expire_at))


async def reset_free_users_monthly_quota(db: AsyncSession) -> int:
    """重置所有免费用户的月卡时长：清空后赠送固定免费时长。

    返回处理的免费用户数量。调用方负责 commit。
    """
    result = await db.execute(select(User))
    users = result.scalars().all()

    grant = settings.FREE_MONTHLY_MINUTES
    processed = 0

    for user in users:
        if not is_free_user(user):
            continue

        # 清空月卡 token（无论当前多少），再赠送固定免费时长
        user.monthly_card_minutes = grant

        # 记流水：免费赠送，月卡时长
        await business_service.record_free_gift(
            db, user.id, "monthly", grant, grant,
            source="monthly_free_reset",
            description=f"每月免费时长重置：清空后赠送 {grant} 分钟",
        )
        processed += 1

    logger.info(f"免费用户月度时长重置完成，处理 {processed} 个免费用户，每人赠送 {grant} 分钟")
    return processed
