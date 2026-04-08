import logging
import time

# ---------------------------------------------------------------------------
# Load secrets from Vault FIRST — routers read os.getenv() at import time
# ---------------------------------------------------------------------------
from shared_schemas.vault_client import PATHS_AUTH, load_vault_secrets

logging.basicConfig(level=logging.INFO)
load_vault_secrets(PATHS_AUTH)
# ---------------------------------------------------------------------------

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from routers import auth, twofa, user

SERVICE_NAME = "auth-service"

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
    title="Auth Service",
    description="Authentication microservice (Supabase-based) with full documentation",
    version="1.0.0",
)


def _resolve_route_path(request: Request) -> str:
    """Resolve the best-effort route path for metrics labeling.
    
    Args:
        request (Request): Incoming FastAPI request context.
    
    Returns:
        str: Best-effort route path for metrics labeling.
    """
    route = request.scope.get("route")
    route_path = getattr(route, "path", None)
    if isinstance(route_path, str) and route_path:
        return route_path
    return request.url.path


@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
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
        path = _resolve_route_path(request)
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
    """Return a basic health payload for the auth service.
    
    Returns:
        Any: Basic health payload for the auth service.
    """
    return {"status": "healthy", "service": SERVICE_NAME}


@app.get("/metrics", include_in_schema=False)
def metrics():
    """Expose Prometheus metrics in the standard plaintext format.
    
    Returns:
        Any: Result of the operation.
    """
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Include routers
app.include_router(auth.auth_router)
app.include_router(twofa.twofa_router)
app.include_router(user.user_router)
