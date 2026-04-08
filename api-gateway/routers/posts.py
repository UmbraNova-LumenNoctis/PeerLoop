"""Posts router composition module."""

from fastapi import APIRouter

from routers.posts_actions import post_actions_router
from routers.posts_read import post_read_router
from routers.posts_write import post_write_router

post_router = APIRouter(tags=["Posts"])
post_router.include_router(post_read_router, prefix="/api/posts")
post_router.include_router(post_write_router, prefix="/api/posts")
post_router.include_router(post_actions_router, prefix="/api/posts")
