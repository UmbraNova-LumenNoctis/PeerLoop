"""
peerloop API Gateway
FastAPI application with health checks and Prometheus metrics
"""
import logging
import os
import time
from datetime import datetime

# ---------------------------------------------------------------------------
# Load secrets from Vault BEFORE importing routers (they call os.getenv at module level)
# ---------------------------------------------------------------------------
from shared_schemas.vault_client import PATHS_API_GATEWAY, load_vault_secrets

logging.basicConfig(level=logging.INFO)
load_vault_secrets(PATHS_API_GATEWAY)
# ---------------------------------------------------------------------------

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from routers import auth, chat, files, friendships, llm, notifications, posts, search, twofa, users

# Initialize FastAPI app
app = FastAPI(
    title="peerloop API Gateway",
    description="API Gateway for peerloop DevOps Infrastructure",
    version="1.0.0"
)

# CORS middleware
_default_cors_origins = [
    "http://localhost:3000",
    "https://localhost:3000",
    "http://127.0.0.1:3000",
    "https://127.0.0.1:3000",
    "http://localhost:5173",
    "https://localhost:5173",
    "http://127.0.0.1:5173",
    "https://127.0.0.1:5173",
    "http://localhost:8443",
    "https://localhost:8443",
    "http://127.0.0.1:8443",
    "https://127.0.0.1:8443",
    "http://localhost:8444",
    "https://localhost:8444",
    "http://127.0.0.1:8444",
    "https://127.0.0.1:8444",
]
_cors_origins_env = (os.getenv("CORS_ALLOW_ORIGINS") or "").strip()
if _cors_origins_env:
    cors_allowed_origins = [origin.strip() for origin in _cors_origins_env.split(",") if origin.strip()]
else:
    cors_allowed_origins = _default_cors_origins

if "*" in cors_allowed_origins:
    # Wildcard origins are incompatible with allow_credentials=True in browsers.
    cors_allowed_origins = [origin for origin in cors_allowed_origins if origin != "*"] or _default_cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Authorization"],
)

# Prometheus metrics
SERVICE_NAME = "api-gateway"

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests processed",
    ["service", "method", "path", "status"],
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["service", "method", "path"],
)

# Startup time
STARTUP_TIME = datetime.now()

# Middleware for metrics
def _public_base_url(request: Request) -> str:
    """Build the public base URL for responses and documentation links.
    
    Args:
        request (Request): Incoming FastAPI request context.
    
    Returns:
        str: Public base URL for responses and documentation links.
    """
    forwarded_proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "https").lower()
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    forwarded_port = request.headers.get("x-forwarded-port")
    if host and ":" not in host and forwarded_port and forwarded_port not in {"80", "443"}:
        host = f"{host}:{forwarded_port}"
    return f"{forwarded_proto}://{host}"


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Collect Prometheus request metrics for each HTTP call.
    
    Args:
        request (Request): Incoming FastAPI request context.
        call_next (Any): ASGI handler for the next middleware.
    
    Returns:
        Any: Result of the operation.
    """
    start_time = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        route = request.scope.get("route")
        route_path = getattr(route, "path", None)
        if not isinstance(route_path, str) or not route_path:
            route_path = request.url.path
        REQUEST_COUNT.labels(
            service=SERVICE_NAME,
            method=request.method,
            path=route_path,
            status=str(status_code),
        ).inc()
        REQUEST_DURATION.labels(
            service=SERVICE_NAME,
            method=request.method,
            path=route_path,
        ).observe(time.perf_counter() - start_time)

@app.get("/")
async def root(request: Request):
    """Root endpoint.
    
    Args:
        request (Request): Incoming FastAPI request context.
    
    Returns:
        Any: Result of the operation.
    """
    base_url = _public_base_url(request)
    return {
        "service": "peerloop API Gateway",
        "version": "1.0.0",
        "status": "running",
        "uptime": str(datetime.now() - STARTUP_TIME),
        "urls": {
            "api_gateway": base_url,
            "docs": f"{base_url}/docs",
            "openapi": f"{base_url}/openapi.json",
        },
    }

@app.get("/health")
async def health_check():
    """Health check endpoint.
    
    Returns:
        Any: Result of the operation.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": SERVICE_NAME,
        "environment": os.getenv("ENVIRONMENT") or os.getenv("ENV"),
        "vault_configured": bool(os.getenv("VAULT_ADDR"))
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint.
    
    Returns:
        Any: Result of the operation.
    """
    return PlainTextResponse(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

# -----------------------------
# Include Auth Routers
# -----------------------------

app.include_router(auth.auth_router)
app.include_router(auth.oauth_callback_router)
app.include_router(twofa.twofa_router)
app.include_router(users.user_router)
app.include_router(friendships.friendship_router)
app.include_router(posts.post_router)
app.include_router(notifications.notification_router)
app.include_router(chat.chat_router)
app.include_router(files.file_router)
app.include_router(llm.llm_router)
app.include_router(search.search_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
