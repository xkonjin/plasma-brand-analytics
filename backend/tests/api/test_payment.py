# =============================================================================
# Payment API Test Suite
# =============================================================================
# Tests for payment invoice creation, submission, and status endpoints.
# =============================================================================

import pytest
import uuid
from datetime import datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, AsyncMock

from app.models.db_models import PaymentInvoice, PaymentStatusEnum


async def _create_invoice(
    session: AsyncSession,
    status: PaymentStatusEnum = PaymentStatusEnum.PENDING,
) -> PaymentInvoice:
    """Helper to create a payment invoice for testing."""
    invoice = PaymentInvoice(
        id=uuid.uuid4(),
        payer_address="0x" + "a" * 40,
        amount_atomic=100000,
        nonce="0x" + uuid.uuid4().hex,
        deadline=datetime.utcnow() + timedelta(hours=1),
        status=status,
        created_at=datetime.utcnow(),
    )
    session.add(invoice)
    await session.commit()
    await session.refresh(invoice)
    return invoice


class TestCreateInvoice:
    """Tests for POST /api/v1/payment/invoice endpoint."""

    async def test_rejects_invalid_address_format(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/payment/invoice",
            json={"payer_address": "not_an_address"},
        )
        # Pydantic field_validator returns 422 Unprocessable Entity
        assert response.status_code == 422

    async def test_rejects_short_address(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/payment/invoice",
            json={"payer_address": "0x1234"},
        )
        assert response.status_code == 422

    async def test_rejects_missing_0x_prefix(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/payment/invoice",
            json={"payer_address": "a" * 42},
        )
        assert response.status_code == 422


class TestGetInvoiceStatus:
    """Tests for GET /api/v1/payment/invoice/{id} endpoint."""

    async def test_returns_pending_invoice(self, client: AsyncClient, test_session: AsyncSession):
        invoice = await _create_invoice(test_session, PaymentStatusEnum.PENDING)
        response = await client.get(f"/api/v1/payment/invoice/{invoice.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(invoice.id)
        assert data["status"] == "pending"

    async def test_returns_completed_invoice(self, client: AsyncClient, test_session: AsyncSession):
        invoice = await _create_invoice(test_session, PaymentStatusEnum.COMPLETED)
        invoice.tx_hash = "0x" + "b" * 64
        await test_session.commit()
        response = await client.get(f"/api/v1/payment/invoice/{invoice.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["txHash"] is not None

    async def test_404_for_nonexistent(self, client: AsyncClient):
        response = await client.get(f"/api/v1/payment/invoice/{uuid.uuid4()}")
        assert response.status_code == 404

    async def test_response_has_timestamps(self, client: AsyncClient, test_session: AsyncSession):
        invoice = await _create_invoice(test_session)
        response = await client.get(f"/api/v1/payment/invoice/{invoice.id}")
        data = response.json()
        assert "created_at" in data
        assert "deadline" in data


class TestSubmitPayment:
    """Tests for POST /api/v1/payment/pay endpoint."""

    async def test_rejects_invalid_invoice_id(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/payment/pay",
            json={
                "invoiceId": str(uuid.uuid4()),
                "signature": {"v": 27, "r": "0x" + "a" * 64, "s": "0x" + "b" * 64},
                "scheme": "eip3009-transfer-with-auth",
            },
        )
        # Should fail during processing - either 400 or 500
        assert response.status_code in (400, 404, 500)
