# =============================================================================
# Reports API Test Suite
# =============================================================================
# Tests for report retrieval, PDF download, summary, and shareable link endpoints.
# =============================================================================

import pytest
import uuid
from datetime import datetime

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, AsyncMock

from app.models.db_models import Analysis, AnalysisStatusEnum


async def _create_analysis(
    session: AsyncSession,
    status: AnalysisStatusEnum = AnalysisStatusEnum.COMPLETED,
    report: dict = None,
    scores: dict = None,
    overall_score: float = 75.0,
    url: str = "https://example.com",
) -> Analysis:
    """Helper to create an analysis record for testing."""
    analysis = Analysis(
        id=uuid.uuid4(),
        url=url,
        status=status,
        progress={},
        report=report or {"scorecard": {"strengths": ["a"], "weaknesses": ["b"], "top_recommendations": ["c"]}},
        scores=scores or {"seo": 80, "social_media": 70},
        overall_score=overall_score,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        completed_at=datetime.utcnow() if status == AnalysisStatusEnum.COMPLETED else None,
    )
    session.add(analysis)
    await session.commit()
    await session.refresh(analysis)
    return analysis


class TestGetReport:
    """Tests for GET /api/v1/analysis/{id}/report endpoint."""

    async def test_returns_completed_report(self, client: AsyncClient, test_session: AsyncSession):
        analysis = await _create_analysis(test_session)
        response = await client.get(f"/api/v1/analysis/{analysis.id}/report")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(analysis.id)
        assert data["url"] == "https://example.com"
        assert data["overall_score"] == 75.0
        assert "report" in data
        assert "scores" in data

    async def test_404_for_nonexistent(self, client: AsyncClient):
        fake_id = uuid.uuid4()
        response = await client.get(f"/api/v1/analysis/{fake_id}/report")
        assert response.status_code == 404

    async def test_400_for_pending_analysis(self, client: AsyncClient, test_session: AsyncSession):
        analysis = await _create_analysis(test_session, status=AnalysisStatusEnum.PENDING)
        response = await client.get(f"/api/v1/analysis/{analysis.id}/report")
        assert response.status_code == 400
        assert "not started" in response.json()["detail"].lower()

    async def test_400_for_processing_analysis(self, client: AsyncClient, test_session: AsyncSession):
        analysis = await _create_analysis(test_session, status=AnalysisStatusEnum.PROCESSING)
        response = await client.get(f"/api/v1/analysis/{analysis.id}/report")
        assert response.status_code == 400
        assert "in progress" in response.json()["detail"].lower()

    async def test_400_for_failed_analysis(self, client: AsyncClient, test_session: AsyncSession):
        analysis = await _create_analysis(test_session, status=AnalysisStatusEnum.FAILED)
        response = await client.get(f"/api/v1/analysis/{analysis.id}/report")
        assert response.status_code == 400

    async def test_500_for_missing_report_data(self, client: AsyncClient, test_session: AsyncSession):
        analysis = await _create_analysis(test_session, report=None)
        # Manually null out the report
        analysis.report = None
        await test_session.commit()
        response = await client.get(f"/api/v1/analysis/{analysis.id}/report")
        assert response.status_code == 500

    async def test_report_has_timestamps(self, client: AsyncClient, test_session: AsyncSession):
        analysis = await _create_analysis(test_session)
        response = await client.get(f"/api/v1/analysis/{analysis.id}/report")
        data = response.json()
        assert "created_at" in data
        assert data["created_at"].endswith("Z")


class TestGetReportSummary:
    """Tests for GET /api/v1/analysis/{id}/summary endpoint."""

    async def test_returns_summary(self, client: AsyncClient, test_session: AsyncSession):
        report = {
            "scorecard": {
                "strengths": ["Strong SEO", "Good brand"],
                "weaknesses": ["Low social"],
                "top_recommendations": ["Improve social"],
            },
            "brand_messaging": {"archetype": {"primary": "Innovator"}},
        }
        analysis = await _create_analysis(test_session, report=report)
        response = await client.get(f"/api/v1/analysis/{analysis.id}/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["overall_score"] == 75.0
        assert len(data["strengths"]) <= 3
        assert len(data["top_recommendations"]) <= 5

    async def test_404_for_nonexistent(self, client: AsyncClient):
        response = await client.get(f"/api/v1/analysis/{uuid.uuid4()}/summary")
        assert response.status_code == 404

    async def test_400_for_incomplete(self, client: AsyncClient, test_session: AsyncSession):
        analysis = await _create_analysis(test_session, status=AnalysisStatusEnum.PROCESSING)
        response = await client.get(f"/api/v1/analysis/{analysis.id}/summary")
        assert response.status_code == 400


class TestGetShareableLink:
    """Tests for GET /api/v1/analysis/{id}/share endpoint."""

    async def test_returns_shareable_url(self, client: AsyncClient, test_session: AsyncSession):
        analysis = await _create_analysis(test_session)
        response = await client.get(f"/api/v1/analysis/{analysis.id}/share")
        assert response.status_code == 200
        data = response.json()
        assert "share_url" in data
        assert str(analysis.id) in data["share_url"]
        assert data["analysis_id"] == str(analysis.id)

    async def test_404_for_nonexistent(self, client: AsyncClient):
        response = await client.get(f"/api/v1/analysis/{uuid.uuid4()}/share")
        assert response.status_code == 404

    async def test_400_for_incomplete(self, client: AsyncClient, test_session: AsyncSession):
        analysis = await _create_analysis(test_session, status=AnalysisStatusEnum.PENDING)
        response = await client.get(f"/api/v1/analysis/{analysis.id}/share")
        assert response.status_code == 400


class TestDownloadPDF:
    """Tests for GET /api/v1/analysis/{id}/pdf endpoint."""

    async def test_404_for_nonexistent(self, client: AsyncClient):
        response = await client.get(f"/api/v1/analysis/{uuid.uuid4()}/pdf")
        assert response.status_code == 404

    async def test_400_for_incomplete(self, client: AsyncClient, test_session: AsyncSession):
        analysis = await _create_analysis(test_session, status=AnalysisStatusEnum.PENDING)
        response = await client.get(f"/api/v1/analysis/{analysis.id}/pdf")
        assert response.status_code == 400

    async def test_redirects_when_pdf_url_exists(self, client: AsyncClient, test_session: AsyncSession):
        analysis = await _create_analysis(test_session)
        analysis.pdf_url = "https://storage.example.com/report.pdf"
        await test_session.commit()
        response = await client.get(
            f"/api/v1/analysis/{analysis.id}/pdf", follow_redirects=False
        )
        assert response.status_code in (301, 302, 303, 307)
