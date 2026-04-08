"""Friendship service application entrypoint."""

import time

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from core.context import SERVICE_NAME
from routers.routes_friendships_list import friendship_list_router
from routers.routes_friendships_write import friendship_write_router

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
    title="Friendship Service",
    version="1.0.0",
    description="Friendship management service for peerloop.",
)

friendship_router = APIRouter(tags=["Friendships"])
friendship_router.include_router(friendship_list_router, prefix="/friendships")
friendship_router.include_router(friendship_write_router, prefix="/friendships")


@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    """Collect Prometheus counters and request duration metrics.
    
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
    """Return friendship service health status.
    
    Returns:
        Any: Friendship service health status.
    """
    return {"status": "healthy", "service": SERVICE_NAME}


@app.get("/metrics", include_in_schema=False)
def metrics():
    """Expose Prometheus metrics endpoint.
    
    Returns:
        Any: Result of the operation.
    """
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(friendship_router)
