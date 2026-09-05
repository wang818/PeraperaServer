"""
Business Service — 用户时长变动流水记录。

提供统一的流水写入入口，供充值（entitlement_service）、
消费/赠送（quota_service）等业务链路调用。

所有方法只 `db.add` 不 `commit`，由调用方在业务事务中统一提交，
保证流水与时长字段的原子性。
"""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business import (
    BusinessRecord,
    CHANGE_RECHARGE_POINTS,
    CHANGE_RECHARGE_MEMBER,
    CHANGE_FREE_GIFT,
    CHANGE_VIDEO_CONSUMPTION,
    CHANGE_SYSTEM_DEDUCTION,
    DURATION_MONTHLY,
    DURATION_POINT,
)

logger = logging.getLogger(__name__)


async def add_record(
    db: AsyncSession,
    user_id: int,
    change_type: str,
    duration_type: str,
    amount: int,
    balance_after: int,
    source: str = None,
    description: str = None,
) -> BusinessRecord:
    """新增一条时长变动流水（不 commit）。

    Args:
        db: 数据库会话。
        user_id: 用户 ID。
        change_type: 变动类型（CHANGE_* 常量）。
        duration_type: 时长类型（DURATION_MONTHLY / DURATION_POINT）。
        amount: 变动分钟数（正增负减）。
        balance_after: 变动后余额（分钟）。
        source: 关联来源（product_id / URL / 操作者）。
        description: 说明。
    """
    record = BusinessRecord(
        user_id=user_id,
        change_type=change_type,
        duration_type=duration_type,
        amount=amount,
        balance_after=balance_after,
        source=source,
        description=description,
    )
    db.add(record)
    logger.debug(
        f"写入时长流水 user={user_id} type={change_type}/{duration_type} "
        f"amount={amount} balance_after={balance_after}"
    )
    return record


# 便捷封装，减少业务侧拼写常量的心智负担

async def record_recharge_points(db, user_id, amount, balance_after, source=None, description=None):
    """充值点数（点卡时长增加）"""
    return await add_record(
        db, user_id, CHANGE_RECHARGE_POINTS, DURATION_POINT,
        amount, balance_after, source, description,
    )


async def record_recharge_member(db, user_id, amount, balance_after, source=None, description=None):
    """充值会员（月卡时长增加）"""
    return await add_record(
        db, user_id, CHANGE_RECHARGE_MEMBER, DURATION_MONTHLY,
        amount, balance_after, source, description,
    )


async def record_free_gift(db, user_id, duration_type, amount, balance_after, source=None, description=None):
    """免费赠送（月卡或点卡时长增加）"""
    return await add_record(
        db, user_id, CHANGE_FREE_GIFT, duration_type,
        amount, balance_after, source, description,
    )


async def record_video_consumption(db, user_id, duration_type, amount, balance_after, source=None, description=None):
    """视频消费（时长扣减，amount 应为负数）"""
    return await add_record(
        db, user_id, CHANGE_VIDEO_CONSUMPTION, duration_type,
        amount, balance_after, source, description,
    )


async def record_system_deduction(db, user_id, duration_type, amount, balance_after, source=None, description=None):
    """系统扣除（时长扣减，amount 应为负数）"""
    return await add_record(
        db, user_id, CHANGE_SYSTEM_DEDUCTION, duration_type,
        amount, balance_after, source, description,
    )
