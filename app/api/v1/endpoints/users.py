from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.database import get_db
from app.core.security import get_password_hash
from app.models.user import User
from app.models.user_setting import UserSetting
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.schemas.user_setting import UserSettingResponse, UserSettingUpdate
from app.api.v1.endpoints.auth import get_current_user

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
