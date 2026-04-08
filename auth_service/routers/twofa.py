"""2FA router composition module."""

from fastapi import APIRouter

from routers.twofa_routes_manage import twofa_manage_router
from routers.twofa_routes_status import twofa_status_router

twofa_router = APIRouter(prefix="/2fa", tags=["2FA"])
twofa_router.include_router(twofa_status_router)
twofa_router.include_router(twofa_manage_router)
