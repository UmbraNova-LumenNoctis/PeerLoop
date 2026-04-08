"""Auth router composition module."""

from fastapi import APIRouter

from routers.auth_routes_credentials import auth_credentials_router
from routers.auth_routes_google import auth_google_router

auth_router = APIRouter(prefix="/auth", tags=["Auth"])
auth_router.include_router(auth_credentials_router)
auth_router.include_router(auth_google_router)
