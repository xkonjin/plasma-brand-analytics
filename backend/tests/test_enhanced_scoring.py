# =============================================================================
# Enhanced Scoring Models Test Suite
# =============================================================================
# Tests for NormalizedScore, ConfidenceLevel, DataSource, BenchmarkComparison,
# and EnhancedScoreCard models.
# =============================================================================

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models.enhanced_scoring import (
    ConfidenceLevel,
    NormalizationMethod,
    DataSource,
    ConfidenceFactors,
    BenchmarkComparison,
    NormalizedScore,
)


class TestConfidenceLevel:
    """Tests for ConfidenceLevel enum."""

    def test_all_levels(self):
        assert ConfidenceLevel.VERY_HIGH == "very_high"
        assert ConfidenceLevel.HIGH == "high"
        assert ConfidenceLevel.MEDIUM == "medium"
        assert ConfidenceLevel.LOW == "low"
        assert ConfidenceLevel.VERY_LOW == "very_low"


class TestNormalizationMethod:
    """Tests for NormalizationMethod enum."""

    def test_all_methods(self):
        assert NormalizationMethod.PERCENTILE_RANK == "percentile_rank"
        assert NormalizationMethod.Z_SCORE == "z_score"
        assert NormalizationMethod.BENCHMARK_COMPARISON == "benchmark_comparison"
        assert NormalizationMethod.WEIGHTED_FACTORS == "weighted_factors"
        assert NormalizationMethod.RAW_METRIC == "raw_metric"


class TestDataSource:
    """Tests for DataSource model."""

    def test_valid_data_source(self):
        ds = DataSource(name="Google PageSpeed", type="api")
        assert ds.name == "Google PageSpeed"
        assert ds.type == "api"
        assert ds.timestamp is not None

    def test_data_source_with_all_fields(self):
        ds = DataSource(
            name="Moz API",
            type="api",
            url="https://moz.com/api",
            version="v2",
            reliability_score=0.9,
        )
        assert ds.reliability_score == 0.9

    def test_reliability_score_bounds(self):
        with pytest.raises(ValidationError):
            DataSource(name="test", type="api", reliability_score=1.5)

        with pytest.raises(ValidationError):
            DataSource(name="test", type="api", reliability_score=-0.1)


class TestConfidenceFactors:
    """Tests for ConfidenceFactors model."""

    def test_valid_factors(self):
        cf = ConfidenceFactors(
            data_completeness=0.8,
            data_freshness=0.9,
            source_reliability=0.85,
            methodology_robustness=0.7,
        )
        assert cf.data_completeness == 0.8
        assert cf.sample_size is None

    def test_rejects_out_of_range(self):
        with pytest.raises(ValidationError):
            ConfidenceFactors(
                data_completeness=1.5,
                data_freshness=0.9,
                source_reliability=0.85,
                methodology_robustness=0.7,
            )

    def test_accepts_zero(self):
        cf = ConfidenceFactors(
            data_completeness=0.0,
            data_freshness=0.0,
            source_reliability=0.0,
            methodology_robustness=0.0,
        )
        assert cf.data_completeness == 0.0


class TestBenchmarkComparison:
    """Tests for BenchmarkComparison model."""

    def test_valid_comparison(self):
        bc = BenchmarkComparison(
            benchmark_value=70.0,
            benchmark_source="Industry Report 2024",
            percentile_rank=80.0,
            difference_from_benchmark=10.0,
            benchmark_category="B2B SaaS",
        )
        assert bc.percentile_rank == 80.0

    def test_percentile_rank_bounds(self):
        with pytest.raises(ValidationError):
            BenchmarkComparison(
                benchmark_value=70.0,
                benchmark_source="test",
                percentile_rank=110.0,
                difference_from_benchmark=10.0,
                benchmark_category="test",
            )

    def test_negative_difference_allowed(self):
        bc = BenchmarkComparison(
            benchmark_value=70.0,
            benchmark_source="test",
            percentile_rank=30.0,
            difference_from_benchmark=-20.0,
            benchmark_category="test",
        )
        assert bc.difference_from_benchmark == -20.0


class TestNormalizedScore:
    """Tests for NormalizedScore model."""

    def test_valid_score(self):
        ns = NormalizedScore(
            value=75.0,
            raw_score=75.0,
            confidence_level=ConfidenceLevel.HIGH,
        )
        assert ns.value == 75.0
        assert ns.raw_score == 75.0
        assert ns.confidence_level == ConfidenceLevel.HIGH

    def test_score_bounds(self):
        with pytest.raises(ValidationError):
            NormalizedScore(
                value=150.0,
                confidence_level=ConfidenceLevel.HIGH,
            )

    def test_negative_score_rejected(self):
        with pytest.raises(ValidationError):
            NormalizedScore(
                value=-10.0,
            )

    def test_serialization(self):
        ns = NormalizedScore(
            value=80.0,
            raw_score=80.0,
            confidence_level=ConfidenceLevel.MEDIUM,
        )
        data = ns.model_dump()
        assert data["value"] == 80.0
        assert data["raw_score"] == 80.0
        assert data["confidence_level"] == "medium"

    def test_optional_fields_default_none(self):
        ns = NormalizedScore(value=50.0)
        assert ns.confidence_level is None
        assert ns.raw_score is None
        assert ns.benchmark_comparison is None
