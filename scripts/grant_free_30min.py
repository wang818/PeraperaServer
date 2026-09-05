#!/usr/bin/env python3
"""一次性脚本：给所有现有用户每人补偿 30 分钟免费月卡时长。

用法：
    venv/bin/python scripts/grant_free_30min.py

行为：
    - 遍历所有用户，每人 monthly_card_minutes += 30 分钟（累加，不清空）
    - 记 business 流水（free_gift / monthly，source=backfill_free_30min）
    - 幂等：用 source 去重，若已补偿过则跳过

注意：这是对齐「新用户赠送30分钟」的存量补偿，与每月1号的「清空+赠送」不同
（后者是清零后设为30，本脚本是累加30）。
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.business import BusinessRecord, CHANGE_FREE_GIFT
from app.services import business_service


async def main() -> None:
    grant = settings.FREE_MONTHLY_MINUTES

    async with AsyncSessionLocal() as db:
        users = (await db.execute(select(User))).scalars().all()
        print(f"共 {len(users)} 个用户")

        granted = 0
        skipped = 0

        for user in users:
            # 幂等：检查是否已补偿过
            existing = await db.execute(
                select(BusinessRecord).where(
                    BusinessRecord.user_id == user.id,
                    BusinessRecord.change_type == CHANGE_FREE_GIFT,
                    BusinessRecord.source == "backfill_free_30min",
                )
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue

            user.monthly_card_minutes = (user.monthly_card_minutes or 0) + grant
            await business_service.record_free_gift(
                db, user.id, "monthly", grant, user.monthly_card_minutes,
                source="backfill_free_30min",
                description=f"存量补偿赠送 {grant} 分钟",
            )
            granted += 1

        await db.commit()

    print(f"完成：补偿 {granted} 个用户（每人 +{grant} 分钟），跳过 {skipped} 个已补偿")


if __name__ == "__main__":
    asyncio.run(main())
