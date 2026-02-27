# =============================================================================
# Auth Models Test Suite
# =============================================================================
# Tests for authentication Pydantic models - user creation, API keys, tokens.
# =============================================================================

import pytest
from uuid import uuid4
from datetime import datetime

from pydantic import ValidationError

from app.auth.models import (
    UserBase,
    UserCreate,
    User,
    UserRole,
    APIKeyBase,
    APIKeyCreate,
    APIKey,
    APIKeyWithSecret,
    TokenData,
    AuthResponse,
    RateLimitInfo,
)


class TestUserBase:
    """Tests for UserBase model validation."""

    def test_valid_email(self):
        user = UserBase(email="test@example.com")
        assert user.email == "test@example.com"

    def test_email_lowercased(self):
        user = UserBase(email="Test@EXAMPLE.COM")
        assert user.email == "test@example.com"

    def test_email_stripped_after_validation(self):
        """Email validator strips after matching, so space breaks regex."""
        with pytest.raises(ValidationError):
            UserBase(email="  test@example.com  ")

    def test_rejects_invalid_email(self):
        with pytest.raises(ValidationError):
            UserBase(email="not_an_email")

    def test_rejects_missing_at(self):
        with pytest.raises(ValidationError):
            UserBase(email="testexample.com")

    def test_rejects_too_short(self):
        with pytest.raises(ValidationError):
            UserBase(email="a@b")

    def test_rejects_empty(self):
        with pytest.raises(ValidationError):
            UserBase(email="")


class TestUserCreate:
    """Tests for UserCreate model validation."""

    def test_valid_user_create(self):
        user = UserCreate(email="test@example.com", password="securePass1!")
        assert user.email == "test@example.com"
        assert user.password == "securePass1!"

    def test_rejects_short_password(self):
        with pytest.raises(ValidationError):
            UserCreate(email="test@example.com", password="short")

    def test_rejects_too_long_password(self):
        with pytest.raises(ValidationError):
            UserCreate(email="test@example.com", password="a" * 101)

    def test_accepts_8_char_password(self):
        user = UserCreate(email="test@example.com", password="12345678")
        assert len(user.password) == 8


class TestUser:
    """Tests for User response model."""

    def test_user_defaults(self):
        user = User(
            id=uuid4(),
            email="test@example.com",
            created_at=datetime.utcnow(),
        )
        assert user.role == UserRole.USER
        assert user.is_active is True
        assert user.api_keys == []

    def test_admin_role(self):
        user = User(
            id=uuid4(),
            email="admin@example.com",
            role=UserRole.ADMIN,
            created_at=datetime.utcnow(),
        )
        assert user.role == UserRole.ADMIN


class TestAPIKeyModels:
    """Tests for API key models."""

    def test_api_key_base_requires_name(self):
        with pytest.raises(ValidationError):
            APIKeyBase(name="")

    def test_api_key_create_with_expiry(self):
        key = APIKeyCreate(name="My Key", expires_days=30)
        assert key.expires_days == 30

    def test_api_key_create_no_expiry(self):
        key = APIKeyCreate(name="My Key")
        assert key.expires_days is None

    def test_api_key_create_rejects_negative_days(self):
        with pytest.raises(ValidationError):
            APIKeyCreate(name="My Key", expires_days=-1)

    def test_api_key_create_rejects_over_365_days(self):
        with pytest.raises(ValidationError):
            APIKeyCreate(name="My Key", expires_days=366)

    def test_api_key_response(self):
        key = APIKey(
            id=uuid4(),
            name="Test Key",
            key_prefix="ba_abcdefgh",
            created_at=datetime.utcnow(),
        )
        assert key.is_active is True
        assert key.last_used_at is None

    def test_api_key_with_secret(self):
        key = APIKeyWithSecret(
            id=uuid4(),
            name="Test Key",
            key_prefix="ba_abcdefgh",
            key="ba_abcdefghijklmnop",
            created_at=datetime.utcnow(),
        )
        assert key.key.startswith("ba_")


class TestTokenData:
    """Tests for TokenData model."""

    def test_empty_token_data(self):
        td = TokenData()
        assert td.user_id is None
        assert td.api_key_id is None
        assert td.scopes == []

    def test_token_with_user_id(self):
        uid = uuid4()
        td = TokenData(user_id=uid)
        assert td.user_id == uid


class TestAuthResponse:
    """Tests for AuthResponse model."""

    def test_auth_response(self):
        resp = AuthResponse(
            access_token="eyJ...",
            expires_in=3600,
        )
        assert resp.token_type == "bearer"
        assert resp.expires_in == 3600


class TestRateLimitInfo:
    """Tests for RateLimitInfo model."""

    def test_rate_limit_info(self):
        info = RateLimitInfo(
            limit=100,
            remaining=95,
            reset_at=datetime.utcnow(),
        )
        assert info.limit == 100
        assert info.remaining == 95
