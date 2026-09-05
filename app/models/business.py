"""
Business model — 用户时长（月卡/点卡）变动流水。

记录用户字幕识别时长（月卡时长 / 点数时长）每一次增减的历史，
用于对账、审计与用户可见的「消费记录」。

时长单位统一为「分钟」。

类型（change_type）：
- recharge_points   充值点数（购买点卡，point 时长增加）
- recharge_member   充值会员（购买月卡/年卡，monthly 时长增加）
- free_gift         免费赠送（运营赠送 / 年卡补充月卡等）
- video_consumption 视频消费（下载字幕识别，时长扣减）
- system_deduction  系统扣除（人工/运营扣减、异常回滚等）

时长类型（duration_type）：
- monthly 月卡时长
- point   点数时长
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.sql import func

from app.core.database import Base


# 变动类型常量
CHANGE_RECHARGE_POINTS = "recharge_points"
CHANGE_RECHARGE_MEMBER = "recharge_member"
CHANGE_FREE_GIFT = "free_gift"
CHANGE_VIDEO_CONSUMPTION = "video_consumption"
CHANGE_SYSTEM_DEDUCTION = "system_deduction"

# 时长类型常量
DURATION_MONTHLY = "monthly"
DURATION_POINT = "point"


class BusinessRecord(Base):
    """用户时长变动流水（仅追加，不修改）。"""

    __tablename__ = "business_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )

    # 变动类型：recharge_points / recharge_member / free_gift / video_consumption / system_deduction
    change_type = Column(String, nullable=False, index=True)

    # 时长类型：monthly（月卡时长）/ point（点数时长）
    duration_type = Column(String, nullable=False)

    # 本次变动分钟数：正数 = 增加，负数 = 扣减
    amount = Column(Integer, nullable=False)

    # 变动后该类型时长余额（分钟），便于对账
    balance_after = Column(Integer, nullable=False)

    # 关联信息：商品 product_id、视频 URL、操作说明等
    source = Column(String, nullable=True)
    description = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_business_records_user_created", "user_id", "created_at"),
    )

    def __repr__(self):
        return (
            f"<BusinessRecord(id={self.id}, user_id={self.user_id}, "
            f"change_type='{self.change_type}', duration_type='{self.duration_type}', "
            f"amount={self.amount})>"
        )
