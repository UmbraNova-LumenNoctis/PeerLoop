"""Chat service application entrypoint."""

import time

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from core.context import SERVICE_NAME
from routers.routes_conversations import chat_conversations_router
from routers.routes_messages import chat_messages_router
from routers.routes_presence import chat_presence_router, presence_internal_router
from routers.ws_routes import ws_router

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
    title="Chat Service",
    version="1.0.0",
    description="Conversation and real-time messaging service for peerloop.",
)

chat_router = APIRouter(prefix="/chat", tags=["Chat"])
chat_router.include_router(chat_conversations_router)
chat_router.include_router(chat_messages_router)
chat_router.include_router(chat_presence_router)


@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    """Collect Prometheus counters and latency histogram.
    
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
    """Expose Prometheus metrics.
    
    Returns:
        Any: Result of the operation.
    """
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(chat_router)
app.include_router(presence_internal_router)
app.include_router(ws_router)
