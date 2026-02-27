# =============================================================================
# Reports API Endpoints
# =============================================================================
# This module provides endpoints for retrieving analysis reports and PDFs.
# It handles report generation and delivery.
# =============================================================================

from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models.db_models import Analysis, AnalysisStatusEnum
from app.services.pdf_generator import generate_pdf_report


router = APIRouter()


@router.get(
    "/analysis/{analysis_id}/report",
    summary="Get full analysis report",
    description="""
    Retrieve the complete brand analysis report.
    
    The report includes detailed findings and recommendations for:
    - SEO Performance
    - Social Media Presence
    - Brand Messaging & Archetype
    - Website UX & Conversion
    - AI Discoverability
    - Content Analysis
    - Team Presence
    - Channel Fit
    - Overall Scorecard
    """,
)
async def get_report(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get the full analysis report.

    Args:
        analysis_id: UUID of the analysis
        db: Database session

    Returns:
        dict: Complete analysis report

    Raises:
        HTTPException: 404 if not found, 400 if not yet completed
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
    # Check Status
    # -------------------------------------------------------------------------
    if analysis.status == AnalysisStatusEnum.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Analysis has not started yet. Please wait.",
        )

    if analysis.status == AnalysisStatusEnum.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Analysis is still in progress. Please check back soon.",
        )

    if analysis.status == AnalysisStatusEnum.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Analysis failed: {analysis.error_message or 'Unknown error'}",
        )

    # -------------------------------------------------------------------------
    # Return Report
    # -------------------------------------------------------------------------
    if not analysis.report:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Report data is missing. Please contact support.",
        )

    return {
        "id": str(analysis.id),
        "url": analysis.url,
        "overall_score": analysis.overall_score,
        "scores": analysis.scores,
        "report": analysis.report,
        "created_at": analysis.created_at.isoformat() + "Z",
        "completed_at": analysis.completed_at.isoformat() + "Z"
        if analysis.completed_at
        else None,
        "processing_time_seconds": analysis.processing_time_seconds,
    }


@router.get(
    "/analysis/{analysis_id}/pdf",
    summary="Download PDF report",
    description="Download the brand analysis report as a PDF file.",
)
async def download_pdf(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Download the analysis report as a PDF.

    If the PDF has already been generated, redirects to the stored file.
    Otherwise, generates the PDF on-demand.

    Args:
        analysis_id: UUID of the analysis
        db: Database session

    Returns:
        StreamingResponse or RedirectResponse: PDF file

    Raises:
        HTTPException: 404 if not found, 400 if not completed
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
    # Check Status
    # -------------------------------------------------------------------------
    if analysis.status != AnalysisStatusEnum.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Report is not yet available. Analysis must be completed first.",
        )

    # -------------------------------------------------------------------------
    # Return Existing PDF or Generate New One
    # -------------------------------------------------------------------------
    if analysis.pdf_url:
        # Redirect to stored PDF
        return RedirectResponse(url=analysis.pdf_url)

    # Generate PDF on-demand
    if not analysis.report:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Report data is missing. Cannot generate PDF.",
        )

    try:
        # Generate PDF from report data
        pdf_bytes = await generate_pdf_report(
            analysis_id=str(analysis.id),
            url=analysis.url,
            report=analysis.report,
            scores=analysis.scores,
            overall_score=analysis.overall_score,
        )

        # Return as streaming response
        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="brand-report-{analysis_id}.pdf"',
                "Content-Length": str(len(pdf_bytes)),
            },
        )
    except Exception as e:
        # Log the actual error server-side but don't expose to client
        import logging
        logging.getLogger(__name__).exception("PDF generation failed for analysis %s", analysis_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate PDF report. Please try again or contact support.",
        )


@router.get(
    "/analysis/{analysis_id}/summary",
    summary="Get report summary",
    description="Get a condensed summary of the analysis suitable for sharing.",
)
async def get_report_summary(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get a condensed summary of the analysis.

    Returns only the key scores, strengths, weaknesses, and top recommendations.
    Suitable for sharing or preview purposes.

    Args:
        analysis_id: UUID of the analysis
        db: Database session

    Returns:
        dict: Condensed report summary
    """
    result = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID {analysis_id} not found",
        )

    if analysis.status != AnalysisStatusEnum.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Summary not available until analysis is complete.",
        )

    report = analysis.report or {}
    scorecard = report.get("scorecard", {})

    return {
        "id": str(analysis.id),
        "url": analysis.url,
        "overall_score": analysis.overall_score,
        "scores": analysis.scores,
        "strengths": scorecard.get("strengths", [])[:3],
        "weaknesses": scorecard.get("weaknesses", [])[:3],
        "top_recommendations": scorecard.get("top_recommendations", [])[:5],
        "brand_archetype": report.get("brand_messaging", {}).get("archetype"),
        "completed_at": analysis.completed_at.isoformat() + "Z"
        if analysis.completed_at
        else None,
    }


@router.get(
    "/analysis/{analysis_id}/share",
    summary="Get shareable report link",
    description="Get a public shareable link for the report.",
)
async def get_shareable_link(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """
    Get a shareable link for the report.

    Returns a public URL that can be shared to view the report.

    Args:
        analysis_id: UUID of the analysis
        db: Database session

    Returns:
        dict: Shareable URL
    """
    result = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis with ID {analysis_id} not found",
        )

    if analysis.status != AnalysisStatusEnum.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot share an incomplete analysis.",
        )

    # Generate shareable URL (frontend will handle rendering)
    # In production, this would use the actual frontend domain
    frontend_url = (
        settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "http://localhost:3000"
    )
    share_url = f"{frontend_url}/report/{analysis_id}"

    return {
        "share_url": share_url,
        "analysis_id": str(analysis_id),
    }
