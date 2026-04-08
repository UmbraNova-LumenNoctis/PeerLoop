"""Search service application entrypoint."""

import time

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from .core.context import SERVICE_NAME
from .routers.routes_search import search_router

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
    title="Search Service",
    version="2.0.0",
    description="Search users and posts for peerloop.",
)


@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    """Collect Prometheus counters and latency metrics.
    
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


@app.get("/", tags=["Root"])
def root():
    """Return service metadata and exposed endpoint paths.
    
    Returns:
        Any: Service metadata and exposed endpoint paths.
    """
    return {
        "service": "Search Service",
        "status": "running",
        "version": "2.0.0",
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "search_users": "/search/users",
            "search_posts": "/search/posts",
        },
    }


@app.get("/health", tags=["Health"])
def health():
    """Return search service health status.
    
    Returns:
        Any: Search service health status.
    """
    return {"status": "healthy", "service": SERVICE_NAME}


@app.get("/metrics", include_in_schema=False)
def metrics():
    """Expose Prometheus metrics endpoint.
    
    Returns:
        Any: Result of the operation.
    """
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(search_router)
