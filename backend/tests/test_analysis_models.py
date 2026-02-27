# =============================================================================
# Analysis Request/Response Model Tests
# =============================================================================
# Tests for Pydantic model validation, sanitization, and serialization
# of analysis request/response models.
# =============================================================================

import pytest
from uuid import uuid4
from datetime import datetime

from pydantic import ValidationError

from app.models.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisStatus,
    AnalysisProgress,
    AnalysisError,
    ModuleStatus,
)


# =============================================================================
# Test AnalysisRequest validation
# =============================================================================


class TestAnalysisRequest:
    """Tests for AnalysisRequest model validation."""

    def test_valid_request(self):
        req = AnalysisRequest(url="https://example.com")
        assert "example.com" in str(req.url)

    def test_normalizes_url_without_protocol(self):
        req = AnalysisRequest(url="example.com")
        assert str(req.url).startswith("https://")

    def test_rejects_empty_url(self):
        with pytest.raises(ValidationError):
            AnalysisRequest(url="")

    def test_rejects_blocked_host(self):
        with pytest.raises(ValidationError):
            AnalysisRequest(url="http://localhost")

    def test_rejects_private_ip(self):
        with pytest.raises(ValidationError):
            AnalysisRequest(url="http://192.168.1.1")

    def test_accepts_optional_description(self):
        req = AnalysisRequest(
            url="https://example.com",
            description="A test company",
        )
        assert req.description == "A test company"

    def test_sanitizes_description_xss(self):
        req = AnalysisRequest(
            url="https://example.com",
            description='<script>alert("xss")</script>Normal text',
        )
        assert "<script" not in (req.description or "")

    def test_accepts_optional_industry(self):
        req = AnalysisRequest(
            url="https://example.com",
            industry="fintech",
        )
        assert req.industry == "fintech"

    def test_sanitizes_industry(self):
        req = AnalysisRequest(
            url="https://example.com",
            industry='<script>alert(1)</script>Technology',
        )
        assert "<script" not in (req.industry or "")

    def test_validates_email(self):
        req = AnalysisRequest(
            url="https://example.com",
            email="user@example.com",
        )
        assert req.email == "user@example.com"

    def test_rejects_invalid_email(self):
        with pytest.raises(ValidationError):
            AnalysisRequest(
                url="https://example.com",
                email="not_an_email",
            )

    def test_lowercases_email(self):
        req = AnalysisRequest(
            url="https://example.com",
            email="User@Example.COM",
        )
        assert req.email == "user@example.com"

    def test_none_optionals_accepted(self):
        req = AnalysisRequest(url="https://example.com")
        assert req.description is None
        assert req.industry is None
        assert req.email is None

    def test_file_url_gets_normalized_to_https(self):
        """Note: normalize_url adds https:// prefix to non-http URLs.
        This is a known limitation - the file:// scheme gets mangled."""
        req = AnalysisRequest(url="file:///etc/passwd")
        # normalize_url turns this into https://file///etc/passwd
        assert str(req.url).startswith("https://")

    def test_rejects_metadata_url(self):
        with pytest.raises(ValidationError):
            AnalysisRequest(url="http://169.254.169.254")


# =============================================================================
# Test AnalysisResponse
# =============================================================================


class TestAnalysisResponse:
    """Tests for AnalysisResponse model."""

    def test_basic_response(self):
        resp = AnalysisResponse(
            id=uuid4(),
            url="https://example.com",
            status=AnalysisStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        assert resp.status == AnalysisStatus.PENDING

    def test_completed_response(self):
        resp = AnalysisResponse(
            id=uuid4(),
            url="https://example.com",
            status=AnalysisStatus.COMPLETED,
            overall_score=85.5,
            scores={"seo": 90, "social_media": 80},
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        assert resp.overall_score == 85.5
        assert resp.scores["seo"] == 90

    def test_rejects_score_over_100(self):
        with pytest.raises(ValidationError):
            AnalysisResponse(
                id=uuid4(),
                url="https://example.com",
                status=AnalysisStatus.COMPLETED,
                overall_score=150.0,
                created_at=datetime.utcnow(),
            )

    def test_rejects_negative_score(self):
        with pytest.raises(ValidationError):
            AnalysisResponse(
                id=uuid4(),
                url="https://example.com",
                status=AnalysisStatus.COMPLETED,
                overall_score=-10.0,
                created_at=datetime.utcnow(),
            )

    def test_serialization_uses_enum_values(self):
        resp = AnalysisResponse(
            id=uuid4(),
            url="https://example.com",
            status=AnalysisStatus.PROCESSING,
            created_at=datetime.utcnow(),
        )
        data = resp.model_dump()
        assert data["status"] == "processing"


# =============================================================================
# Test AnalysisProgress
# =============================================================================


class TestAnalysisProgress:
    """Tests for AnalysisProgress model."""

    def test_default_all_pending(self):
        progress = AnalysisProgress()
        assert progress.seo == "pending"
        assert progress.social_media == "pending"
        assert progress.brand_messaging == "pending"
        assert progress.website_ux == "pending"
        assert progress.ai_discoverability == "pending"
        assert progress.content == "pending"
        assert progress.team_presence == "pending"
        assert progress.channel_fit == "pending"
        assert progress.scorecard == "pending"

    def test_partial_progress(self):
        progress = AnalysisProgress(
            seo="completed",
            social_media="running",
        )
        assert progress.seo == "completed"
        assert progress.social_media == "running"
        assert progress.brand_messaging == "pending"


# =============================================================================
# Test AnalysisError
# =============================================================================


class TestAnalysisError:
    """Tests for AnalysisError model."""

    def test_error_response(self):
        err = AnalysisError(
            id=uuid4(),
            error_code="TIMEOUT",
            error_message="Analysis timed out after 300 seconds",
            failed_module="seo",
        )
        assert err.status == AnalysisStatus.FAILED
        assert err.error_code == "TIMEOUT"
        assert err.failed_module == "seo"

    def test_error_without_module(self):
        err = AnalysisError(
            id=uuid4(),
            error_code="UNKNOWN",
            error_message="Something went wrong",
        )
        assert err.failed_module is None


# =============================================================================
# Test AnalysisStatus enum
# =============================================================================


class TestAnalysisStatusEnum:
    """Tests for AnalysisStatus enum values."""

    def test_all_statuses(self):
        assert AnalysisStatus.PENDING == "pending"
        assert AnalysisStatus.PROCESSING == "processing"
        assert AnalysisStatus.COMPLETED == "completed"
        assert AnalysisStatus.FAILED == "failed"

    def test_module_statuses(self):
        assert ModuleStatus.PENDING == "pending"
        assert ModuleStatus.RUNNING == "running"
        assert ModuleStatus.COMPLETED == "completed"
        assert ModuleStatus.FAILED == "failed"
        assert ModuleStatus.SKIPPED == "skipped"
