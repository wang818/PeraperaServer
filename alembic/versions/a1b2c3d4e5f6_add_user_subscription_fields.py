"""add_user_subscription_fields

为 users 表新增订阅 / 字幕识别时长配额字段：
- annual_expire_at  年卡过期时间
- monthly_expire_at 月卡过期时间
- point_card_minutes 点卡时长（分钟，int）
- monthly_card_minutes 月卡时长（分钟，int）

Revision ID: a1b2c3d4e5f6
Revises: 36fc156e92d7
Create Date: 2026-07-29 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '36fc156e92d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('annual_expire_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'users',
        sa.Column('monthly_expire_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'users',
        sa.Column('point_card_minutes', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'users',
        sa.Column('monthly_card_minutes', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    op.drop_column('users', 'monthly_card_minutes')
    op.drop_column('users', 'point_card_minutes')
    op.drop_column('users', 'monthly_expire_at')
    op.drop_column('users', 'annual_expire_at')
