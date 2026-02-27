# =============================================================================
# Analysis API Endpoints
# =============================================================================
# This module provides endpoints for starting and monitoring brand analyses.
# It handles analysis requests, queues tasks, and tracks progress.
# =============================================================================

from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID

import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db, get_session_factory
from app.models.db_models import Analysis, AnalysisStatusEnum
from app.models.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisStatus,
    AnalysisProgress,
)
from app.tasks.analysis_tasks import run_full_analysis
from app.auth.dependencies import get_optional_auth, check_rate_limit
from app.auth.payment import require_payment


router = APIRouter()


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start a new brand analysis",
    description="""
    Start a comprehensive brand analysis for the given website URL.
    
    The analysis runs asynchronously and includes:
    - SEO Performance Analysis
    - Social Media Presence
    - Brand Messaging & Archetype
    - Website UX & Conversion
    - AI Discoverability
    - Content Analysis
    - Team Presence
    - Channel Fit Scoring
    
    Returns an analysis ID that can be used to track progress and retrieve results.
    """,
)
async def start_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _payment=Depends(require_payment),
    _auth=Depends(get_optional_auth),
    _rate_limit=Depends(check_rate_limit),
) -> AnalysisResponse:
    """
    Start a new brand analysis for the provided URL.

    Args:
        request: Analysis request containing URL and optional metadata
        background_tasks: FastAPI background tasks for async processing
        db: Database session
        _payment: Payment authorization (required)

    Returns:
        AnalysisResponse: Analysis ID and initial status

    Raises:
        HTTPException: 400 if URL is invalid
        HTTPException: 402 if payment is missing/invalid
    """
    # -------------------------------------------------------------------------
    # Validate URL
    # -------------------------------------------------------------------------
    url = str(request.url).strip().rstrip("/")

    # Basic URL validation (more thorough validation in the task)
    if not url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL must start with http:// or https://",
        )

    # -------------------------------------------------------------------------
    # Create Analysis Record
    # -------------------------------------------------------------------------
    # Initialize progress tracking for all modules
    initial_progress = {
        "seo": "pending",
        "social_media": "pending",
        "brand_messaging": "pending",
        "website_ux": "pending",
        "ai_discoverability": "pending",
        "content": "pending",
        "team_presence": "pending",
        "channel_fit": "pending",
        "scorecard": "pending",
    }

    analysis = Analysis(
        url=url,
        description=request.description,
        industry=request.industry,
        email=request.email,
        status=AnalysisStatusEnum.PENDING,
        progress=initial_progress,
    )

    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    # -------------------------------------------------------------------------
    # Queue Analysis Task
    # -------------------------------------------------------------------------
    if settings.ENVIRONMENT == "development" or settings.WEB_ONLY:
        background_tasks.add_task(run_full_analysis, str(analysis.id))
    else:
        from app.tasks.celery_app import celery_app

        celery_app.send_task("run_full_analysis", args=[str(analysis.id)])

    # -------------------------------------------------------------------------
    # Return Response
    # -------------------------------------------------------------------------
    return AnalysisResponse(
        id=analysis.id,
        url=url,
        status=AnalysisStatus.PENDING,
        progress=AnalysisProgress(**initial_progress),
        created_at=analysis.created_at,
        message="Analysis started. Use the ID to track progress.",
    )


@router.get(
    "/analysis/{analysis_id}",
    response_model=AnalysisResponse,
    summary="Get analysis status and progress",
    description="Retrieve the current status and progress of an analysis job.",
)
async def get_analysis_status(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AnalysisResponse:
    """
    Get the current status and progress of an analysis.

    Args:
        analysis_id: UUID of the analysis
        db: Database session

    Returns:
        AnalysisResponse: Current status, progress, and scores if available

    Raises:
        HTTPException: 404 if analysis not found
    """
    # -------------------------------------------------------------------------
    # Fetch Analysis
    # -------------------------------------------------------------------------
    result = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID {analysis_id} not found",
        )

    # -------------------------------------------------------------------------
    # Build Response
    # -------------------------------------------------------------------------
    response = AnalysisResponse(
        id=analysis.id,
        url=analysis.url,
        status=AnalysisStatus(analysis.status.value),
        progress=AnalysisProgress(**analysis.progress) if analysis.progress else None,
        scores=analysis.scores,
        overall_score=analysis.overall_score,
        created_at=analysis.created_at,
        completed_at=analysis.completed_at,
        processing_time_seconds=analysis.processing_time_seconds,
    )

    # Add error message if failed (sanitize to prevent leaking internal details)
    if analysis.status == AnalysisStatusEnum.FAILED:
        error_msg = analysis.error_message or "Analysis failed"
        # Strip any stack trace or file path details that may have been stored
        if "\n" in error_msg or "Traceback" in error_msg or "/" in error_msg:
            error_msg = "Analysis failed due to an internal error"
        response.message = error_msg

    # Add success message if completed
    if analysis.status == AnalysisStatusEnum.COMPLETED:
        response.message = "Analysis completed successfully"
        response.pdf_url = analysis.pdf_url

    return response


@router.get(
    "/analysis/{analysis_id}/progress",
    summary="Get real-time analysis progress",
    description="Get detailed progress for each analysis module.",
)
async def get_analysis_progress(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get detailed progress for each analysis module.

    This endpoint is optimized for polling to show real-time progress.

    Args:
        analysis_id: UUID of the analysis
        db: Database session

    Returns:
        dict: Detailed progress information
    """
    result = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID {analysis_id} not found",
        )

    # Calculate completion percentage
    progress = analysis.progress or {}
    total_modules = len(progress)
    completed_modules = sum(
        1 for status in progress.values() if status in ("completed", "failed")
    )
    completion_percentage = (
        (completed_modules / total_modules * 100) if total_modules > 0 else 0
    )

    return {
        "id": str(analysis.id),
        "status": analysis.status.value,
        "modules": progress,
        "completion_percentage": round(completion_percentage, 1),
        "updated_at": analysis.updated_at.isoformat() + "Z",
    }


@router.get(
    "/analysis/{analysis_id}/stream",
    summary="Stream analysis progress via SSE",
    description="Server-Sent Events stream for real-time progress updates.",
)
async def stream_analysis_progress(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Stream real-time progress updates via Server-Sent Events.

    The stream sends JSON-formatted events with progress updates until
    the analysis completes or fails.
    """
    result = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID {analysis_id} not found",
        )

    async def event_generator():
        last_progress = None
        poll_interval = 1.0
        max_iterations = 600
        iteration = 0
        session_factory = get_session_factory()

        while iteration < max_iterations:
            async with session_factory() as session:
                result = await session.execute(
                    select(Analysis).where(Analysis.id == analysis_id)
                )
                current = result.scalar_one_or_none()

                if not current:
                    yield f"data: {json.dumps({'error': 'Analysis not found'})}\n\n"
                    break

                current_progress = current.progress or {}
                progress_data = {
                    "status": current.status.value,
                    "modules": current_progress,
                    "overall_score": current.overall_score,
                    "completion_percentage": _calculate_completion(current_progress),
                }

                if progress_data != last_progress:
                    yield f"data: {json.dumps(progress_data)}\n\n"
                    last_progress = progress_data.copy()

                if current.status in (
                    AnalysisStatusEnum.COMPLETED,
                    AnalysisStatusEnum.FAILED,
                ):
                    final_data = {
                        "status": current.status.value,
                        "overall_score": current.overall_score,
                        "completed": True,
                    }
                    yield f"data: {json.dumps(final_data)}\n\n"
                    break

            await asyncio.sleep(poll_interval)
            iteration += 1

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _calculate_completion(progress: dict) -> float:
    if not progress:
        return 0.0
    total = len(progress)
    completed = sum(1 for s in progress.values() if s in ("completed", "failed"))
    return round((completed / total) * 100, 1) if total > 0 else 0.0


@router.delete(
    "/analysis/{analysis_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel an analysis",
    description="Cancel a pending or in-progress analysis.",
)
async def cancel_analysis(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Cancel an ongoing analysis.

    Args:
        analysis_id: UUID of the analysis to cancel
        db: Database session

    Raises:
        HTTPException: 404 if not found, 409 if already completed
    """
    result = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID {analysis_id} not found",
        )

    if analysis.status in (AnalysisStatusEnum.COMPLETED, AnalysisStatusEnum.FAILED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot cancel a completed or failed analysis",
        )

    # Mark as failed with cancellation message
    analysis.status = AnalysisStatusEnum.FAILED
    analysis.error_message = "Analysis cancelled by user"
    analysis.updated_at = datetime.utcnow()

    await db.commit()


@router.get(
    "/analyses",
    summary="List recent analyses",
    description="Get a list of recent analyses, optionally filtered by status.",
)
async def list_analyses(
    status_filter: Optional[AnalysisStatus] = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    List recent analyses with optional filtering.

    Args:
        status_filter: Optional status to filter by
        limit: Maximum number of results (default 20, max 100)
        offset: Offset for pagination
        db: Database session

    Returns:
        dict: List of analyses with pagination info
    """
    # Validate and cap limit
    limit = min(limit, 100)

    # Build query
    query = select(Analysis).order_by(Analysis.created_at.desc())

    if status_filter:
        query = query.where(Analysis.status == AnalysisStatusEnum(status_filter.value))

    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    analyses = result.scalars().all()

    return {
        "items": [
            {
                "id": str(a.id),
                "url": a.url,
                "status": a.status.value,
                "overall_score": a.overall_score,
                "created_at": a.created_at.isoformat() + "Z",
                "completed_at": a.completed_at.isoformat() + "Z"
                if a.completed_at
                else None,
            }
            for a in analyses
        ],
        "limit": limit,
        "offset": offset,
    }
