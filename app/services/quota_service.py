"""
Quota Service — 字幕识别时长配额管理

负责：
- 查询 YouTube 视频时长（用于计费）
- 月卡过期后用年卡补充月卡时长（refill）
- 校验用户剩余时长是否足够，不足则报错
- 下载成功后扣除时长（优先扣月卡，其次点卡）

时长单位统一为「分钟」存储在 users 表：
- monthly_card_minutes：月卡时长（月卡充值时设为 1800，年卡补充时 +1800）
- point_card_minutes ：点卡时长（每次充值 +180）
"""
import asyncio
import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

import yt_dlp

from app.core.config import settings
from app.core.i18n import get_translation
from app.models.user import User
from app.models.business import DURATION_MONTHLY, DURATION_POINT
from app.services import business_service

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_active(expires_at: Optional[datetime]) -> bool:
    """判断某个过期时间是否有效（未过期）。"""
    if expires_at is None:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at > _now()


async def get_video_duration_seconds(url: str) -> Optional[int]:
    """查询 YouTube 视频时长（秒）。

    通过 yt-dlp 拉取视频元信息获取 duration 字段。
    在线程池中执行（yt-dlp 为同步阻塞调用），并设置超时。
    失败时返回 None（由调用方决定如何报错）。
    """
    loop = asyncio.get_running_loop()

    def _extract() -> Optional[int]:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "format": "bestaudio",
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            duration = info.get("duration")
            if isinstance(duration, (int, float)):
                return int(duration)
            return None

    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, _extract), timeout=30
        )
    except Exception as e:
        logger.warning(f"获取视频时长失败 url={url}: {e}")
        return None


async def ensure_monthly_refill(db: AsyncSession, user: User) -> None:
    """月卡过期且年卡仍有效时，补充月卡时长。

    - 若月卡未过期：不做任何事。
    - 若月卡已过期、且年卡未过期：月卡时长 += 1800 分钟，月卡周期重置为 now+30 天。
    """
    if _is_active(user.monthly_expire_at):
        return

    if _is_active(user.annual_expire_at):
        user.monthly_card_minutes = (user.monthly_card_minutes or 0) + settings.MONTHLY_REFILL_MINUTES
        user.monthly_expire_at = _now() + timedelta(days=settings.MONTHLY_DURATION_DAYS)
        # 记流水：免费赠送，月卡时长（年卡有效自动补充）
        await business_service.record_free_gift(
            db, user.id, DURATION_MONTHLY, settings.MONTHLY_REFILL_MINUTES,
            user.monthly_card_minutes, source="annual_refill",
            description=f"年卡有效，月卡过期自动补充 {settings.MONTHLY_REFILL_MINUTES} 分钟",
        )
        logger.info(
            f"年卡有效，已为 user={user.id} 补充月卡时长 "
            f"{settings.MONTHLY_REFILL_MINUTES} 分钟，月卡有效期重置为 {user.monthly_expire_at}"
        )


async def check_quota_available(
    db: AsyncSession, user: User, duration_seconds: int, lang: str
) -> int:
    """校验用户剩余字幕识别时长是否足够。

    返回扣除所需的分钟数（向上取整）。时长不足时抛出 403。
    会先执行月卡补充（ensure_monthly_refill）。调用方负责提交事务。
    """
    needed = math.ceil(duration_seconds / 60.0)

    await ensure_monthly_refill(db, user)

    # 月卡时长只要有值即可用（不再要求月卡未过期）
    monthly_minutes = user.monthly_card_minutes or 0
    point_minutes = user.point_card_minutes or 0
    total = monthly_minutes + point_minutes

    if total < needed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=get_translation(
                "quota_insufficient", lang, needed=needed, total=total
            ),
        )

    return needed


async def consume_quota(db: AsyncSession, user: User, duration_seconds: int, video_url: Optional[str] = None) -> None:
    """下载成功后扣除用户时长。

    优先扣除月卡时长，不足部分再扣点卡时长。
    会先执行月卡补充（ensure_monthly_refill）以保证状态一致。
    调用方负责提交事务。
    """
    needed = math.ceil(duration_seconds / 60.0)

    await ensure_monthly_refill(db, user)

    # 优先扣月卡（只要有值即可扣）
    if user.monthly_card_minutes:
        take = min(needed, user.monthly_card_minutes)
        user.monthly_card_minutes -= take
        needed -= take
        # 记流水：视频消费，月卡时长扣减
        await business_service.record_video_consumption(
            db, user.id, DURATION_MONTHLY, -take, user.monthly_card_minutes,
            source=video_url, description=f"视频消费扣减 {take} 分钟",
        )

    # 剩余扣点卡
    if needed > 0:
        user.point_card_minutes = (user.point_card_minutes or 0) - needed
        # 记流水：视频消费，点数时长扣减
        await business_service.record_video_consumption(
            db, user.id, DURATION_POINT, -needed, user.point_card_minutes,
            source=video_url, description=f"视频消费扣减 {needed} 分钟",
        )

    logger.info(
        f"扣除字幕识别时长完成 user={user.id}，"
        f"月卡剩余={user.monthly_card_minutes}，点卡剩余={user.point_card_minutes}"
    )
