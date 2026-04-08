"""LLM service application entrypoint."""

import time

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from shared_schemas.vault_client import PATHS_LLM_SERVICE, load_vault_secrets

load_vault_secrets(PATHS_LLM_SERVICE)

from core.context import GEMINI_MODEL, SERVICE_NAME
from routers.routes_chat import llm_chat_router
from routers.routes_history import llm_history_router

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
    title="LLM Service",
    version="1.0.0",
    description="Gemini-powered LLM proxy service for peerloop.",
)

llm_router = APIRouter(prefix="/llm", tags=["LLM"])
llm_router.include_router(llm_chat_router)
llm_router.include_router(llm_history_router)


@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    """Collect request count and latency metrics.
    
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
    """Return service health and default model info.
    
    Returns:
        Any: Service health and default model info.
    """
    return {"status": "healthy", "service": SERVICE_NAME, "model_default": GEMINI_MODEL}


@app.get("/metrics", include_in_schema=False)
def metrics():
    """Expose Prometheus text metrics.
    
    Returns:
        Any: Result of the operation.
    """
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(llm_router)
