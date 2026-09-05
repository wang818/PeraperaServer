"""
Scheduler — APScheduler 封装。

在 FastAPI lifespan 中启动/停止，负责每月1号重置免费用户月卡时长。
使用 AsyncIOScheduler 与 FastAPI 的事件循环集成。
"""
import logging
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

_scheduler: Optional[AsyncIOScheduler] = None


async def _reset_free_users_monthly_quota_job() -> None:
    """定时任务：每月1号重置免费用户月卡时长。"""
    from app.services.free_quota_service import reset_free_users_monthly_quota

    logger.info("定时任务触发：重置免费用户月度时长")
    try:
        async with AsyncSessionLocal() as db:
            processed = await reset_free_users_monthly_quota(db)
            await db.commit()
            logger.info(f"定时任务完成，处理 {processed} 个免费用户")
    except Exception as e:
        logger.error(f"重置免费用户月度时长失败: {type(e).__name__}: {e}", exc_info=True)


def start_scheduler() -> None:
    """启动 APScheduler（在 FastAPI lifespan 中调用）。"""
    global _scheduler

    if _scheduler is not None:
        logger.warning("scheduler 已启动，跳过")
        return

    _scheduler = AsyncIOScheduler(
        timezone=settings.SCHEDULER_TIMEZONE,
        job_defaults={"misfire_grace_time": 3600, "coalesce": True},
    )

    _scheduler.add_job(
        _reset_free_users_monthly_quota_job,
        trigger=CronTrigger(
            day=settings.MONTHLY_FREE_RESET_DAY,
            hour=settings.MONTHLY_FREE_RESET_HOUR,
            minute=settings.MONTHLY_FREE_RESET_MINUTE,
        ),
        id="reset_free_users_monthly_quota",
        name="每月重置免费用户月卡时长",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        f"scheduler 已启动，每月 {settings.MONTHLY_FREE_RESET_DAY} 号 "
        f"{settings.MONTHLY_FREE_RESET_HOUR:02d}:{settings.MONTHLY_FREE_RESET_MINUTE:02d} "
        f"（{settings.SCHEDULER_TIMEZONE}）重置免费用户月卡时长"
    )


def stop_scheduler() -> None:
    """停止 APScheduler（在 FastAPI lifespan 关闭时调用）。"""
    global _scheduler

    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("scheduler 已停止")
