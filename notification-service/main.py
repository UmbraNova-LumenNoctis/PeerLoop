"""Notification service application entrypoint."""

import time

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

# ---------------------------------------------------------------------------
# Load secrets from Vault BEFORE module-level os.getenv() calls in context.py
# ---------------------------------------------------------------------------
from shared_schemas.vault_client import PATHS_NOTIFICATION_SERVICE, load_vault_secrets

load_vault_secrets(PATHS_NOTIFICATION_SERVICE)
# ---------------------------------------------------------------------------

from core.context import SERVICE_NAME
from routers.routes_read import notification_read_router
from routers.routes_write import notification_write_router

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests processed",
    ["service", "method", "path", "status"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["service", "method", "path"],
)

app = FastAPI(
    title="Notification Service",
    version="1.0.0",
    description="Notification management service for peerloop.",
)

notification_router = APIRouter(tags=["Notifications"])
notification_router.include_router(notification_read_router, prefix="/notifications")
notification_router.include_router(notification_write_router, prefix="/notifications")


@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    """Collect Prometheus metrics for every HTTP request.
    
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
        path = getattr(route, "path", None)
        if not isinstance(path, str) or not path:
            path = request.url.path

        HTTP_REQUESTS_TOTAL.labels(
            service=SERVICE_NAME,
            method=request.method,
            path=path,
            status=str(status_code),
        ).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(
            service=SERVICE_NAME,
            method=request.method,
            path=path,
        ).observe(time.perf_counter() - start_time)


@app.get("/health", tags=["Health"])
def health():
    """Return service health status.
    
    Returns:
        Any: Service health status.
    """
    return {"status": "healthy", "service": SERVICE_NAME}


@app.get("/metrics", include_in_schema=False)
def metrics():
    """Expose Prometheus text metrics.
    
    Returns:
        Any: Result of the operation.
    """
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(notification_router)
