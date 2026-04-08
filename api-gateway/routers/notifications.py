"""Notification router composition module."""

from fastapi import APIRouter

from routers.notifications_read import notifications_read_router
from routers.notifications_state import notifications_state_router

notification_router = APIRouter(tags=["Notifications"])
notification_router.include_router(notifications_read_router, prefix="/api/notifications")
notification_router.include_router(notifications_state_router, prefix="/api/notifications")
