# =============================================================================
# Database Models Test Suite
# =============================================================================
# Tests for SQLAlchemy ORM models - Analysis, PaymentInvoice, UserRecord,
# APIKeyRecord, AnalysisCache.
# =============================================================================

import pytest
import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.db_models import (
    Analysis,
    AnalysisStatusEnum,
    AnalysisCache,
    PaymentInvoice,
    PaymentStatusEnum,
    UserRecord,
    UserRoleEnum,
    APIKeyRecord,
    GUID,
)


class TestAnalysisModel:
    """Tests for Analysis ORM model."""

    async def test_create_analysis(self, test_session: AsyncSession):
        analysis = Analysis(
            url="https://example.com",
            status=AnalysisStatusEnum.PENDING,
            progress={"seo": "pending"},
        )
        test_session.add(analysis)
        await test_session.commit()
        await test_session.refresh(analysis)

        assert analysis.id is not None
        assert analysis.url == "https://example.com"
        assert analysis.status == AnalysisStatusEnum.PENDING
        assert analysis.created_at is not None

    async def test_analysis_default_status_is_pending(self, test_session: AsyncSession):
        analysis = Analysis(url="https://test.com", progress={})
        test_session.add(analysis)
        await test_session.commit()
        await test_session.refresh(analysis)
        assert analysis.status == AnalysisStatusEnum.PENDING

    async def test_analysis_stores_scores_json(self, test_session: AsyncSession):
        scores = {"seo": 80, "social": 65}
        analysis = Analysis(
            url="https://test.com",
            progress={},
            scores=scores,
            overall_score=72.5,
        )
        test_session.add(analysis)
        await test_session.commit()
        await test_session.refresh(analysis)
        assert analysis.scores["seo"] == 80
        assert analysis.overall_score == 72.5

    async def test_analysis_stores_report_json(self, test_session: AsyncSession):
        report = {"scorecard": {"overall_score": 75}}
        analysis = Analysis(
            url="https://test.com", progress={}, report=report
        )
        test_session.add(analysis)
        await test_session.commit()
        await test_session.refresh(analysis)
        assert analysis.report["scorecard"]["overall_score"] == 75

    async def test_analysis_nullable_fields(self, test_session: AsyncSession):
        analysis = Analysis(url="https://test.com", progress={})
        test_session.add(analysis)
        await test_session.commit()
        await test_session.refresh(analysis)
        assert analysis.description is None
        assert analysis.industry is None
        assert analysis.email is None
        assert analysis.completed_at is None
        assert analysis.pdf_url is None

    async def test_query_by_status(self, test_session: AsyncSession):
        a1 = Analysis(url="https://a.com", status=AnalysisStatusEnum.COMPLETED, progress={})
        a2 = Analysis(url="https://b.com", status=AnalysisStatusEnum.PENDING, progress={})
        test_session.add_all([a1, a2])
        await test_session.commit()

        result = await test_session.execute(
            select(Analysis).where(Analysis.status == AnalysisStatusEnum.COMPLETED)
        )
        completed = result.scalars().all()
        assert any(a.url == "https://a.com" for a in completed)

    async def test_analysis_repr(self, test_session: AsyncSession):
        analysis = Analysis(url="https://test.com", progress={})
        test_session.add(analysis)
        await test_session.commit()
        await test_session.refresh(analysis)
        repr_str = repr(analysis)
        assert "Analysis" in repr_str
        assert "https://test.com" in repr_str


class TestPaymentInvoiceModel:
    """Tests for PaymentInvoice ORM model."""

    async def test_create_invoice(self, test_session: AsyncSession):
        invoice = PaymentInvoice(
            payer_address="0x" + "a" * 40,
            amount_atomic=100000,
            nonce="0x" + uuid.uuid4().hex,
            deadline=datetime.utcnow() + timedelta(hours=1),
        )
        test_session.add(invoice)
        await test_session.commit()
        await test_session.refresh(invoice)
        assert invoice.id is not None
        assert invoice.status == PaymentStatusEnum.PENDING

    async def test_invoice_status_update(self, test_session: AsyncSession):
        invoice = PaymentInvoice(
            payer_address="0x" + "b" * 40,
            amount_atomic=200000,
            nonce="0x" + uuid.uuid4().hex,
            deadline=datetime.utcnow() + timedelta(hours=1),
        )
        test_session.add(invoice)
        await test_session.commit()

        invoice.status = PaymentStatusEnum.COMPLETED
        invoice.tx_hash = "0x" + "c" * 64
        await test_session.commit()
        await test_session.refresh(invoice)
        assert invoice.status == PaymentStatusEnum.COMPLETED
        assert invoice.tx_hash is not None


class TestUserRecordModel:
    """Tests for UserRecord ORM model."""

    async def test_create_user(self, test_session: AsyncSession):
        user = UserRecord(
            email="test@example.com",
            hashed_password="hashed_value",
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.role == UserRoleEnum.USER
        assert user.is_active is True

    async def test_admin_user(self, test_session: AsyncSession):
        user = UserRecord(
            email="admin@example.com",
            hashed_password="hashed_value",
            role=UserRoleEnum.ADMIN,
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)
        assert user.role == UserRoleEnum.ADMIN

    async def test_unique_email_constraint(self, test_session: AsyncSession):
        from sqlalchemy.exc import IntegrityError

        u1 = UserRecord(email="dup@example.com", hashed_password="hash1")
        test_session.add(u1)
        await test_session.commit()

        u2 = UserRecord(email="dup@example.com", hashed_password="hash2")
        test_session.add(u2)
        with pytest.raises(IntegrityError):
            await test_session.commit()
        await test_session.rollback()


class TestAPIKeyRecordModel:
    """Tests for APIKeyRecord ORM model."""

    async def test_create_api_key(self, test_session: AsyncSession):
        user = UserRecord(email="keyuser@example.com", hashed_password="hash")
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        api_key = APIKeyRecord(
            user_id=user.id,
            name="Test Key",
            key_prefix="ba_abcdefgh",
            hashed_key="hashed_full_key",
        )
        test_session.add(api_key)
        await test_session.commit()
        await test_session.refresh(api_key)

        assert api_key.id is not None
        assert api_key.user_id == user.id
        assert api_key.is_active is True
        assert api_key.last_used_at is None

    async def test_api_key_cascade_delete(self, test_session: AsyncSession):
        user = UserRecord(email="cascade@example.com", hashed_password="hash")
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        api_key = APIKeyRecord(
            user_id=user.id,
            name="Cascade Key",
            key_prefix="ba_12345678",
            hashed_key="hashed_key",
        )
        test_session.add(api_key)
        await test_session.commit()
        key_id = api_key.id

        await test_session.delete(user)
        await test_session.commit()

        result = await test_session.execute(
            select(APIKeyRecord).where(APIKeyRecord.id == key_id)
        )
        assert result.scalar_one_or_none() is None


class TestAnalysisCacheModel:
    """Tests for AnalysisCache ORM model."""

    async def test_create_cache_entry(self, test_session: AsyncSession):
        cache = AnalysisCache(
            cache_key="pagespeed:example.com",
            url="https://example.com",
            data_type="pagespeed",
            data={"performance": 85},
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
        test_session.add(cache)
        await test_session.commit()
        await test_session.refresh(cache)
        assert cache.id is not None
        assert cache.data["performance"] == 85

    async def test_cache_unique_key(self, test_session: AsyncSession):
        from sqlalchemy.exc import IntegrityError

        c1 = AnalysisCache(
            cache_key="dup_key",
            url="https://a.com",
            data_type="test",
            data={},
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        test_session.add(c1)
        await test_session.commit()

        c2 = AnalysisCache(
            cache_key="dup_key",
            url="https://b.com",
            data_type="test",
            data={},
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        test_session.add(c2)
        with pytest.raises(IntegrityError):
            await test_session.commit()
        await test_session.rollback()


class TestGUIDType:
    """Tests for custom GUID type decorator."""

    def test_process_bind_param_uuid(self):
        guid = GUID()
        test_uuid = uuid.uuid4()
        result = guid.process_bind_param(test_uuid, None)
        assert result == str(test_uuid)

    def test_process_bind_param_none(self):
        guid = GUID()
        result = guid.process_bind_param(None, None)
        assert result is None

    def test_process_result_value_string(self):
        guid = GUID()
        test_uuid = uuid.uuid4()
        result = guid.process_result_value(str(test_uuid), None)
        assert result == test_uuid

    def test_process_result_value_none(self):
        guid = GUID()
        result = guid.process_result_value(None, None)
        assert result is None
