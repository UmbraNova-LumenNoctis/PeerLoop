"""Friendship router composition module."""

from fastapi import APIRouter

from routers.friendships_read import friendships_read_router
from routers.friendships_write import friendships_write_router

friendship_router = APIRouter(tags=["Friendships"])
friendship_router.include_router(friendships_read_router, prefix="/api/friendships")
friendship_router.include_router(friendships_write_router, prefix="/api/friendships")
