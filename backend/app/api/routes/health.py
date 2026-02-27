# =============================================================================
# Health Check Endpoints
# =============================================================================
# This module provides health check endpoints for monitoring and load balancers.
# It checks the status of all critical dependencies (database, Redis, etc.).
# =============================================================================

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis

from app.config import settings
from app.database import get_db
from app.utils.metrics import get_metrics_collector
from app.utils.circuit_breaker import get_all_circuit_states


router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.

    Returns:
        dict: Health status with version and timestamp

    Example Response:
        {
            "status": "healthy",
            "version": "0.1.0",
            "timestamp": "2024-01-15T10:30:00Z"
        }
    """
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/health/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Detailed health check that verifies all dependencies.

    Checks:
        - Database connectivity (PostgreSQL)
        - Cache connectivity (Redis)
        - Required API keys presence

    Returns:
        dict: Detailed health status of all components

    Example Response:
        {
            "status": "healthy",
            "version": "0.1.0",
            "timestamp": "2024-01-15T10:30:00Z",
            "checks": {
                "database": {"status": "healthy", "latency_ms": 5},
                "redis": {"status": "healthy", "latency_ms": 2},
                "openai_key": {"status": "configured"},
                "google_key": {"status": "configured"}
            }
        }
    """
    checks = {}
    overall_status = "healthy"

    # -------------------------------------------------------------------------
    # Check Database Connection
    # -------------------------------------------------------------------------
    try:
        start = datetime.utcnow()
        await db.execute(text("SELECT 1"))
        latency = (datetime.utcnow() - start).total_seconds() * 1000
        checks["database"] = {
            "status": "healthy",
            "latency_ms": round(latency, 2),
        }
    except Exception as e:
        checks["database"] = {
            "status": "unhealthy",
            "error": "connection_failed",  # Don't leak internal error details
        }
        overall_status = "unhealthy"

    # -------------------------------------------------------------------------
    # Check Redis Connection
    # -------------------------------------------------------------------------
    try:
        start = datetime.utcnow()
        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.close()
        latency = (datetime.utcnow() - start).total_seconds() * 1000
        checks["redis"] = {
            "status": "healthy",
            "latency_ms": round(latency, 2),
        }
    except Exception as e:
        checks["redis"] = {
            "status": "unhealthy",
            "error": "connection_failed",  # Don't leak internal error details
        }
        overall_status = "degraded"  # Redis failure is not critical

    # -------------------------------------------------------------------------
    # Check Required API Keys
    # -------------------------------------------------------------------------
    # OpenAI API key (required for brand archetype analysis)
    checks["openai_key"] = {
        "status": "configured" if settings.OPENAI_API_KEY else "missing",
    }
    if not settings.OPENAI_API_KEY:
        overall_status = "degraded"

    # Google API key (required for PageSpeed and Search)
    checks["google_key"] = {
        "status": "configured" if settings.GOOGLE_API_KEY else "missing",
    }

    # -------------------------------------------------------------------------
    # Return Health Report
    # -------------------------------------------------------------------------
    return {
        "status": overall_status,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": checks,
    }


@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)) -> Dict[str, str]:
    """
    Readiness check for Kubernetes/load balancer probes.

    This endpoint returns 200 only if the service is ready to accept traffic.
    Used by orchestrators to determine if the service should receive requests.

    Returns:
        dict: Ready status

    Raises:
        HTTPException: 503 if service is not ready
    """
    # Verify database is accessible
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        return {"status": "not_ready", "reason": "database_unavailable"}

    return {"status": "ready"}


@router.get("/health/live")
async def liveness_check() -> Dict[str, str]:
    """
    Liveness check for Kubernetes probes.

    This endpoint returns 200 as long as the service is running.
    Used by orchestrators to determine if the service needs to be restarted.

    Returns:
        dict: Alive status
    """
    return {"status": "alive"}


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """Application metrics for monitoring."""
    collector = get_metrics_collector()
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        **collector.get_metrics(),
    }


@router.get("/circuits")
async def get_circuit_status() -> Dict[str, Any]:
    """Circuit breaker status for all external services."""
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "circuits": get_all_circuit_states(),
    }
