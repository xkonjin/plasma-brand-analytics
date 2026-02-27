# =============================================================================
# Payment API Routes
# =============================================================================
# Endpoints for handling x402 payments via Plasma network.
# =============================================================================

from uuid import UUID
from typing import Dict, Any, Optional
from pydantic import BaseModel, field_validator

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.services.x402_service import X402Service
from app.models.db_models import PaymentInvoice
from app.auth.dependencies import check_rate_limit

router = APIRouter()
x402_service = X402Service()


# -----------------------------------------------------------------------------
# Request/Response Models
# -----------------------------------------------------------------------------


class InvoiceRequest(BaseModel):
    payer_address: str

    @field_validator("payer_address")
    @classmethod
    def validate_payer_address(cls, v: str) -> str:
        import re
        if not re.match(r"^0x[0-9a-fA-F]{40}$", v):
            raise ValueError("Invalid Ethereum address format. Expected 0x followed by 40 hex characters.")
        return v


class PaymentSubmission(BaseModel):
    invoiceId: UUID
    signature: Dict[str, Any]
    scheme: str = "eip3009-transfer-with-auth"
    chosenOption: Optional[Dict[str, Any]] = None


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------


@router.post(
    "/payment/invoice",
    status_code=status.HTTP_201_CREATED,
    summary="Create a payment invoice",
    description="Generate a new x402 payment invoice for $0.10 USD₮0",
)
async def create_invoice(
    request: InvoiceRequest,
    db: AsyncSession = Depends(get_db),
    _rate_limit=Depends(check_rate_limit),
) -> Dict[str, Any]:
    """Generate a new payment invoice."""
    # Basic validation of address
    if not request.payer_address.startswith("0x") or len(request.payer_address) != 42:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid wallet address"
        )

    return await x402_service.create_invoice(request.payer_address, db)


@router.post(
    "/payment/pay",
    status_code=status.HTTP_200_OK,
    summary="Submit signed payment",
    description="Submit an EIP-3009 signature to execute payment",
)
async def submit_payment(
    submission: PaymentSubmission,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _rate_limit=Depends(check_rate_limit),
) -> Dict[str, Any]:
    """Process a signed payment."""
    # Get client IP for rate limiting on Relayer API
    client_ip = request.headers.get("x-forwarded-for") or request.client.host
    if client_ip and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()

    try:
        return await x402_service.process_payment(
            submission.invoiceId, submission.signature, str(client_ip), db
        )
    except ValueError as e:
        # Only expose safe, expected validation errors
        safe_messages = [
            "Invoice not found",
            "Invoice already completed",
            "Invoice expired",
            "Invalid signature",
        ]
        detail = str(e) if str(e) in safe_messages else "Invalid payment submission"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Payment processing failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment processing failed. Please try again.",
        )


@router.get(
    "/payment/invoice/{invoice_id}",
    summary="Get invoice status",
)
async def get_invoice_status(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Check status of an invoice."""
    result = await db.execute(
        select(PaymentInvoice).where(PaymentInvoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found"
        )

    return {
        "id": str(invoice.id),
        "status": invoice.status.value,
        "txHash": invoice.tx_hash,
        "created_at": invoice.created_at.isoformat() + "Z",
        "deadline": invoice.deadline.isoformat() + "Z",
    }
