# =============================================================================
# Analysis Tasks
# =============================================================================
# This module contains Celery tasks for running brand analyses.
# Each task handles a specific part of the analysis pipeline.
# =============================================================================

import asyncio
from datetime import datetime
from typing import Dict, Any
import traceback

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.config import settings
from app.models.db_models import Analysis, AnalysisStatusEnum
from app.tasks.celery_app import celery_app


# =============================================================================
# Database Session for Tasks
# =============================================================================
# Tasks run in separate processes, so we need to create a new engine
def get_task_db_session():
    """
    Create a database session for use in background tasks.
    """
    db_url = settings.get_async_database_url()
    is_sqlite = "sqlite" in db_url

    if is_sqlite:
        engine = create_async_engine(
            db_url,
            echo=settings.DEBUG,
            connect_args={"check_same_thread": False},
        )
    else:
        engine = create_async_engine(
            db_url,
            echo=settings.DEBUG,
            pool_size=5,
            max_overflow=10,
        )

    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


# =============================================================================
# Progress Update Helper
# =============================================================================
async def update_progress(
    session_factory, analysis_id: str, module: str, status: str
) -> None:
    """
    Update the progress of a specific analysis module using its own session.

    Uses a separate session to avoid conflicts with the main analysis session
    when committing progress updates mid-operation.

    Args:
        session_factory: Factory to create new database sessions
        analysis_id: UUID of the analysis
        module: Name of the module (e.g., 'seo', 'social_media')
        status: New status ('pending', 'running', 'completed', 'failed')
    """
    from uuid import UUID

    async with session_factory() as progress_session:
        result = await progress_session.execute(
            select(Analysis).where(Analysis.id == UUID(analysis_id))
        )
        analysis = result.scalar_one_or_none()

        if analysis:
            progress = analysis.progress or {}
            progress[module] = status
            analysis.progress = progress
            analysis.updated_at = datetime.utcnow()
            await progress_session.commit()


# =============================================================================
# Main Analysis Task
# =============================================================================
def run_full_analysis(analysis_id: str) -> Dict[str, Any]:
    """
    Run the complete brand analysis.

    This is the main entry point for the analysis pipeline. It orchestrates
    all analysis modules and aggregates results into the final report.

    Args:
        analysis_id: UUID of the analysis to run

    Returns:
        dict: Analysis results summary

    Note:
        This function handles both sync (Celery) and async (FastAPI) contexts.
    """
    # Try to get existing event loop (when called from async context like FastAPI)
    try:
        asyncio.get_running_loop()
        # We're in an async context - create a task and run it
        # This happens when called from FastAPI background tasks
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, _run_analysis_async(analysis_id))
            return future.result()
    except RuntimeError:
        # No running loop - we're in a sync context (Celery)
        return asyncio.run(_run_analysis_async(analysis_id))


async def _run_analysis_async(analysis_id: str) -> Dict[str, Any]:
    """
    Async implementation of the full analysis pipeline.

    This function:
    1. Fetches the analysis record
    2. Scrapes the website
    3. Runs all analysis modules (some in parallel)
    4. Aggregates scores and generates recommendations
    5. Saves the complete report

    Args:
        analysis_id: UUID of the analysis

    Returns:
        dict: Analysis results summary
    """
    from uuid import UUID
    from app.analyzers.orchestrator import AnalysisOrchestrator

    # Get database session
    session_factory = get_task_db_session()

    async with session_factory() as session:
        start_time = datetime.utcnow()

        try:
            # -----------------------------------------------------------------
            # Fetch Analysis Record
            # -----------------------------------------------------------------
            result = await session.execute(
                select(Analysis).where(Analysis.id == UUID(analysis_id))
            )
            analysis = result.scalar_one_or_none()

            if not analysis:
                return {"error": f"Analysis {analysis_id} not found"}

            # Check if already completed or cancelled
            if analysis.status in (
                AnalysisStatusEnum.COMPLETED,
                AnalysisStatusEnum.FAILED,
            ):
                return {"status": "already_finished", "id": analysis_id}

            # -----------------------------------------------------------------
            # Update Status to Processing
            # -----------------------------------------------------------------
            analysis.status = AnalysisStatusEnum.PROCESSING
            analysis.updated_at = datetime.utcnow()
            await session.commit()

            # -----------------------------------------------------------------
            # Run Analysis Orchestrator
            # -----------------------------------------------------------------
            orchestrator = AnalysisOrchestrator(
                url=analysis.url,
                description=analysis.description,
                industry=analysis.industry,
            )

            async def progress_callback(module: str, module_status: str):
                await update_progress(
                    session_factory, analysis_id, module, module_status
                )

            # Run the analysis
            report = await orchestrator.run(progress_callback=progress_callback)

            # -----------------------------------------------------------------
            # Calculate Processing Time
            # -----------------------------------------------------------------
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()

            # -----------------------------------------------------------------
            # Save Results
            # -----------------------------------------------------------------
            analysis.status = AnalysisStatusEnum.COMPLETED
            analysis.report = report.model_dump(mode="json")
            analysis.scores = {
                "seo": report.seo.score,
                "social_media": report.social_media.score,
                "brand_messaging": report.brand_messaging.score,
                "website_ux": report.website_ux.score,
                "ai_discoverability": report.ai_discoverability.score,
                "content": report.content.score,
                "team_presence": report.team_presence.score,
                "channel_fit": report.channel_fit.score,
            }
            analysis.overall_score = report.scorecard.overall_score
            analysis.completed_at = end_time
            analysis.processing_time_seconds = processing_time

            # Update all module progress to completed
            analysis.progress = {
                module: "completed" for module in analysis.progress.keys()
            }

            await session.commit()

            return {
                "status": "completed",
                "id": analysis_id,
                "overall_score": report.scorecard.overall_score,
                "processing_time_seconds": processing_time,
            }

        except Exception as e:
            # -----------------------------------------------------------------
            # Handle Failure
            # -----------------------------------------------------------------
            # Store sanitized error for DB (no stack trace, no internal details)
            error_message = f"Analysis failed: {type(e).__name__}"
            error_traceback = traceback.format_exc()  # For server-side logging only

            # Update analysis record
            result = await session.execute(
                select(Analysis).where(Analysis.id == UUID(analysis_id))
            )
            analysis = result.scalar_one_or_none()

            if analysis:
                analysis.status = AnalysisStatusEnum.FAILED
                analysis.error_message = error_message
                analysis.updated_at = datetime.utcnow()

                # Mark current running module as failed
                progress = analysis.progress or {}
                for module, status in progress.items():
                    if status == "running":
                        progress[module] = "failed"
                analysis.progress = progress

                await session.commit()

            # Log the full traceback server-side only (never send to client)
            import logging
            logger = logging.getLogger(__name__)
            logger.error("Analysis %s failed: %s", analysis_id, error_message)
            logger.debug("Traceback: %s", error_traceback)

            return {
                "status": "failed",
                "id": analysis_id,
                "error": error_message,
            }


# =============================================================================
# Register as Celery Task
# =============================================================================
# Register the task with Celery for production use
@celery_app.task(
    name="run_full_analysis",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def celery_run_full_analysis(self, analysis_id: str) -> Dict[str, Any]:
    """
    Celery task wrapper for run_full_analysis.

    This wrapper adds:
    - Automatic retries on failure
    - Task state tracking
    - Progress updates

    Args:
        analysis_id: UUID of the analysis

    Returns:
        dict: Analysis results
    """
    try:
        return run_full_analysis(analysis_id)
    except Exception as e:
        # Retry on failure (up to max_retries)
        raise self.retry(exc=e)


# =============================================================================
# Cleanup Task (Optional - for maintenance)
# =============================================================================
@celery_app.task(name="cleanup_old_analyses")
def cleanup_old_analyses(days: int = 30) -> Dict[str, int]:
    """
    Clean up old analysis records and cached data.

    This task removes analyses older than the specified number of days
    to prevent database bloat.

    Args:
        days: Number of days to keep analyses (default 30)

    Returns:
        dict: Number of records cleaned up
    """
    # Implementation would go here
    # For now, just return a placeholder
    return {"deleted_analyses": 0, "deleted_cache_entries": 0}
