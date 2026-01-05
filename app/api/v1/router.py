from fastapi import APIRouter
from app.api.v1.endpoints import users, auth, common

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(common.router, prefix="/common", tags=["Common"])
