from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List
from app.core.database import get_db
from app.core.security import get_password_hash
from app.models.user import User
from app.models.user_setting import UserSetting
from app.models.iap import UserEntitlement, TransactionRecord
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.schemas.user_setting import UserSettingResponse, UserSettingUpdate
from app.api.v1.endpoints.auth import get_current_user
from app.core.dependencies import get_language
from app.core.i18n import get_translation
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# @router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
# async def create_user(
#     user_in: UserCreate,
#     db: AsyncSession = Depends(get_db)
# ):
#     """Create a new user."""
#     # Check if user already exists
#     result = await db.execute(
#         select(User).where(
#             (User.email == user_in.email) | (User.username == user_in.username)
#         )
#     )
#     existing_user = result.scalar_one_or_none()
    
#     if existing_user:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="User with this email or username already exists"
#         )
    
#     # Create new user
#     hashed_password = get_password_hash(user_in.password)
#     db_user = User(
#         email=user_in.email,
#         username=user_in.username,
#         hashed_password=hashed_password
#     )
    
#     db.add(db_user)
#     await db.commit()
#     await db.refresh(db_user)
    
#     return db_user


@router.get("/me", response_model=UserResponse)
async def read_current_user(
    current_user: User = Depends(get_current_user)
):
    """Get current user information."""
    return current_user


@router.get("/users_setting", response_model=UserSettingResponse)
async def get_user_setting(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's settings."""
    result = await db.execute(
        select(UserSetting).where(UserSetting.user_uuid == current_user.uuid)
    )
    user_setting = result.scalar_one_or_none()
    
    if not user_setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User settings not found"
        )
    
    return user_setting


@router.put("/users_setting", response_model=UserSettingResponse)
async def update_user_setting(
    setting_in: UserSettingUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user's settings."""
    result = await db.execute(
        select(UserSetting).where(UserSetting.user_uuid == current_user.uuid)
    )
    user_setting = result.scalar_one_or_none()
    
    if not user_setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User settings not found"
        )
    
    # Update settings fields
    update_data = setting_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user_setting, field, value)

    await db.commit()
    await db.refresh(user_setting)

    return user_setting


@router.delete(
    "/delete_account",
    status_code=status.HTTP_200_OK,
    summary="注销当前账号（硬删除）",
    description="""
永久删除当前登录用户的账号及其所有关联数据，**操作不可逆**。

## 删除范围
按依赖顺序在一个 DB 事务中依次执行：

| # | 表 | 操作 | 说明 |
|---|---|---|---|
| 1 | `users_setting` | `DELETE` | 用户偏好设置（按 `user_uuid` 匹配） |
| 2 | `user_entitlements` | `DELETE` | 用户当前 IAP 权益（按 `user_id` 匹配） |
| 3 | `iap_transactions` | `UPDATE user_id=NULL` | IAP 不可变审计日志，**保留数据但匿名化** |
| 4 | `users` | `DELETE` | 用户主表本身 |

任一步失败会 `ROLLBACK`，数据库回滚到操作前状态。

## 安全建议（客户端）
1. 调用前应**弹窗二次确认**，明确告知用户"账号将永久删除，无法恢复"
2. 强烈建议先要求用户**输入验证码**或密码，再调用本接口
3. 收到 200 后应**立即清除本地存储的 token**，并跳转回登录页
4. 同一 token 在请求完成后立即失效（DB 中已无对应 user）

## 注意事项
- 邮箱释放后，该邮箱可重新用于"验证码登录"自动建号
- `iap_transactions` 不会真正删除，仅去掉 user 关联，便于财务/审计追溯
""",
    responses={
        200: {
            "description": "账号删除成功",
            "content": {
                "application/json": {
                    "example": {
                        "message": "账号已成功注销",
                        "deleted_user_id": 123,
                    }
                }
            },
        },
        401: {
            "description": "未提供有效 token 或 token 已过期",
            "content": {
                "application/json": {
                    "example": {"detail": "Could not validate credentials"}
                }
            },
        },
        500: {
            "description": "服务器内部错误（如 DB 事务失败、连接断开等）",
            "content": {
                "application/json": {
                    "example": {"detail": "账号注销失败，请稍后重试"}
                }
            },
        },
    },
)
async def delete_current_user(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    lang: str = Depends(get_language),
):
    """注销当前登录用户的账号（接口实现）。"""
    user_id = current_user.id
    user_uuid = current_user.uuid
    logger.info(f"注销账号请求: id={user_id}, uuid={user_uuid}, email={current_user.email}")

    try:
        # 1. 删除用户设置
        await db.execute(
            UserSetting.__table__.delete().where(UserSetting.user_uuid == user_uuid)
        )

        # 2. 删除用户当前权益
        await db.execute(
            UserEntitlement.__table__.delete().where(UserEntitlement.user_id == user_id)
        )

        # 3. 匿名化 IAP 交易历史（不可变审计日志，仅去掉 user 关联）
        await db.execute(
            update(TransactionRecord)
            .where(TransactionRecord.user_id == user_id)
            .values(user_id=None)
        )

        # 4. 删除用户本身
        await db.execute(User.__table__.delete().where(User.id == user_id))

        await db.commit()
        logger.info(f"账号已注销: id={user_id}, uuid={user_uuid}")

        return {
            "message": get_translation("account_deleted", lang),
            "deleted_user_id": user_id,
        }
    except Exception as e:
        await db.rollback()
        logger.exception(f"注销账号失败: id={user_id}, error={e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_translation("account_delete_failed", lang),
        )


# @router.get("/{user_id}", response_model=UserResponse)
# async def read_user(
#     user_id: int,
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     """Get user by ID."""
#     result = await db.execute(select(User).where(User.id == user_id))
#     user = result.scalar_one_or_none()
    
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="User not found"
#         )
    
#     return user


# @router.get("/", response_model=List[UserResponse])
# async def read_users(
#     skip: int = 0,
#     limit: int = 100,
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     """Get list of users."""
#     result = await db.execute(select(User).offset(skip).limit(limit))
#     users = result.scalars().all()
#     return users


# @router.put("/{user_id}", response_model=UserResponse)
# async def update_user(
#     user_id: int,
#     user_in: UserUpdate,
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     """Update user information."""
#     # Check if user is updating their own profile or is superuser
#     if current_user.id != user_id and not current_user.is_superuser:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Not enough permissions"
#         )
    
#     result = await db.execute(select(User).where(User.id == user_id))
#     user = result.scalar_one_or_none()
    
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="User not found"
#         )
    
#     # Update user fields
#     update_data = user_in.model_dump(exclude_unset=True)
    
#     if "password" in update_data:
#         update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
#     for field, value in update_data.items():
#         setattr(user, field, value)
    
#     await db.commit()
#     await db.refresh(user)
    
#     return user


# @router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
# async def delete_user(
#     user_id: int,
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     """Delete a user."""
#     # Only superusers can delete users
#     if not current_user.is_superuser:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Not enough permissions"
#         )
    
#     result = await db.execute(select(User).where(User.id == user_id))
#     user = result.scalar_one_or_none()
    
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="User not found"
#         )
    
#     await db.delete(user)
#     await db.commit()
    
#     return None
