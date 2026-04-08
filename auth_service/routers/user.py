"""User router composition module."""

from fastapi import APIRouter

from routers.user_routes import user_routes_router

user_router = APIRouter(prefix="/user", tags=["User"])
user_router.include_router(user_routes_router)
