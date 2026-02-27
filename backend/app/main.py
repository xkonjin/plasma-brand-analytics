# =============================================================================
# EXPLAINER: FastAPI Application Entry Point
# =============================================================================
#
# WHAT IS THIS?
# This file is the "main" entry point for the backend. It bootstraps the FastAPI application.
#
# KEY RESPONSIBILITIES:
# 1. **Lifespan Management**: Handles startup (DB connection) and shutdown (cleanup) logic.
# 2. **Middleware**: Configures CORS (Cross-Origin Resource Sharing) so our frontend can talk to us.
# 3. **Routing**: Mounts the API routes (e.g., /api/v1/analysis) from other modules.
# 4. **Exception Handling**: Ensures we return clean JSON errors, not raw stack traces (in prod).
#
# ARCHITECTURAL NOTE:
# We use an `asynccontextmanager` for the lifespan. This is the modern FastAPI way to handle
# startup/shutdown events, replacing the old `on_event("startup")` hooks.
# =============================================================================

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import settings
from app.api.routes import analysis, reports, health, payment
from app.auth.routes import router as auth_router
from app.database import init_db, close_db
from app.middleware.security import SecurityHeadersMiddleware
from app.utils.logging import configure_logging, get_logger
from app.utils.sentry import init_sentry, capture_exception
from app.middleware.logging import RequestLoggingMiddleware

configure_logging(
    log_level=settings.LOG_LEVEL,
    json_logs=settings.LOG_JSON,
)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler for startup and shutdown events.

    This context manager handles:
    - Database connection pool initialization on startup
    - Playwright browser initialization (if needed)
    - Graceful shutdown of connections
    """
    logger.info(
        "Application starting",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )

    init_sentry(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        release=settings.APP_VERSION,
    )

    await init_db()
    logger.info("Database connection pool initialized")

    # Yield control to the application
    # This is where the application actually runs and accepts requests
    yield

    logger.info("Application shutting down")
    await close_db()
    logger.info("Database connections closed")


# =============================================================================
# Create FastAPI Application
# =============================================================================
app = FastAPI(
    title=settings.APP_NAME,
    description="""
    ## Brand Analytics API
    
    A comprehensive brand analysis tool that provides professional marketing audits
    across multiple dimensions:
    
    - **SEO Performance**: PageSpeed, meta tags, indexing
    - **Social Media**: Follower counts, engagement rates, platform presence
    - **Brand Messaging**: Archetype identification, tone analysis, readability
    - **Website UX**: CTAs, navigation, trust signals
    - **AI Discoverability**: Wikipedia, Knowledge Graph, structured data
    - **Content Analysis**: Recent posts, sentiment, content mix
    - **Team Presence**: LinkedIn, founder visibility
    - **Channel Fit**: Platform suitability scoring
    
    ### Getting Started
    
    1. POST `/api/v1/analyze` with a website URL to start analysis
    2. Poll `/api/v1/analysis/{id}` for progress updates
    3. GET `/api/v1/analysis/{id}/report` for the full report
    4. GET `/api/v1/analysis/{id}/pdf` to download PDF
    """,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.ENABLE_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_DOCS else None,
    openapi_url="/openapi.json" if settings.ENABLE_DOCS else None,
)


# =============================================================================
# Configure Middleware Stack (order matters - first added = outermost)
# =============================================================================

# Security Headers - adds XSS protection, clickjacking prevention, etc.
app.add_middleware(SecurityHeadersMiddleware)

# Trusted Host - validates Host header to prevent host header attacks
# In production, restrict to actual domains. Use ["*"] only for development.
if settings.ENVIRONMENT != "development":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )

# CORS - allows frontend applications to make requests to this API
# Methods are restricted to what the API actually uses
# Supports both explicit origins and regex for Vercel preview deployments
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Correlation-ID", "X-API-Key", "X-Invoice-ID"],
    expose_headers=["X-Request-ID", "X-Correlation-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset", "Retry-After"],
    max_age=86400,  # Cache preflight requests for 24 hours
)

app.add_middleware(RequestLoggingMiddleware)

# =============================================================================
# Register API Routes
# =============================================================================
# All routes are prefixed with /api/v1 for versioning
app.include_router(health.router, prefix=settings.API_V1_PREFIX, tags=["Health"])

app.include_router(analysis.router, prefix=settings.API_V1_PREFIX, tags=["Analysis"])

app.include_router(reports.router, prefix=settings.API_V1_PREFIX, tags=["Reports"])

app.include_router(payment.router, prefix=settings.API_V1_PREFIX, tags=["Payments"])

app.include_router(auth_router, prefix=settings.API_V1_PREFIX, tags=["Authentication"])


# =============================================================================
# Root Endpoints (outside API versioning for health checks)
# =============================================================================
@app.get("/", include_in_schema=False)
async def root():
    """
    Root endpoint that provides basic API information.
    Redirects users to the API documentation.
    """
    return JSONResponse(
        content={
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "health": f"{settings.API_V1_PREFIX}/health",
        }
    )


@app.get("/health", include_in_schema=False)
async def root_health():
    """
    Root-level health check endpoint for Railway/Kubernetes probes.
    Returns 200 OK if the application is running.
    """
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "brand-analytics-api",
            "version": settings.APP_VERSION,
        },
        status_code=200,
    )


# =============================================================================
# Exception Handlers
# =============================================================================
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler - logs errors and sends to Sentry."""
    logger.exception(
        "Unhandled exception",
        path=str(request.url.path),
        method=request.method,
        error=str(exc),
    )
    capture_exception(exc, path=str(request.url.path), method=request.method)

    if settings.ENABLE_DEBUG_ERRORS:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": str(exc),
                "type": type(exc).__name__,
            },
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": "An unexpected error occurred. Please try again later.",
            },
        )


# =============================================================================
# Development Server Entry Point
# =============================================================================
if __name__ == "__main__":
    import uvicorn

    # Run the development server
    # For production, use: uvicorn app.main:app --host 0.0.0.0 --port 8000
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",  # nosec B104 - Binding to all interfaces is intentional for containerized deployment
        port=8000,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning",
    )
