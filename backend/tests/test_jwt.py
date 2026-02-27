# =============================================================================
# JWT Utilities Test Suite
# =============================================================================
# Tests for token creation, decoding, password hashing, and API key generation.
# =============================================================================

import pytest
from datetime import timedelta
from unittest.mock import patch

from app.auth.jwt import (
    verify_password,
    hash_password,
    generate_api_key,
    verify_api_key,
    create_access_token,
    decode_access_token,
    create_api_key_token,
)


# =============================================================================
# Test password hashing
# =============================================================================


class TestPasswordHashing:
    """Tests for password hash/verify functions."""

    def test_hash_and_verify_password(self):
        password = "securePassword123!"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_hash_is_not_plaintext(self):
        password = "mypassword"
        hashed = hash_password(password)
        assert hashed != password

    def test_different_hashes_for_same_password(self):
        """bcrypt uses a random salt, so hashes should differ."""
        password = "same_password"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2
        # But both should verify
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

    def test_empty_password_hashes(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True
        assert verify_password("not_empty", hashed) is False


# =============================================================================
# Test API key generation
# =============================================================================


class TestAPIKeyGeneration:
    """Tests for API key generation and verification."""

    def test_generate_api_key_returns_tuple(self):
        full_key, prefix, hashed = generate_api_key()
        assert isinstance(full_key, str)
        assert isinstance(prefix, str)
        assert isinstance(hashed, str)

    def test_api_key_starts_with_prefix(self):
        full_key, prefix, _ = generate_api_key()
        assert full_key.startswith("ba_")

    def test_prefix_is_start_of_key(self):
        full_key, prefix, _ = generate_api_key()
        assert full_key.startswith(prefix)

    def test_prefix_length(self):
        _, prefix, _ = generate_api_key()
        assert len(prefix) == 11  # "ba_" + 8 chars

    def test_verify_generated_key(self):
        full_key, _, hashed = generate_api_key()
        assert verify_api_key(full_key, hashed) is True

    def test_wrong_key_fails_verification(self):
        _, _, hashed = generate_api_key()
        assert verify_api_key("ba_wrong_key_here", hashed) is False

    def test_keys_are_unique(self):
        key1, _, _ = generate_api_key()
        key2, _, _ = generate_api_key()
        assert key1 != key2


# =============================================================================
# Test JWT token creation/decoding
# =============================================================================


class TestJWTTokens:
    """Tests for JWT access token creation and decoding."""

    def test_create_and_decode_token(self):
        data = {"sub": "user123", "role": "admin"}
        token = create_access_token(data)
        decoded = decode_access_token(token)
        assert decoded is not None
        assert decoded["sub"] == "user123"
        assert decoded["role"] == "admin"

    def test_token_contains_expiration(self):
        token = create_access_token({"sub": "user1"})
        decoded = decode_access_token(token)
        assert "exp" in decoded
        assert "iat" in decoded

    def test_custom_expiration(self):
        token = create_access_token(
            {"sub": "user1"}, expires_delta=timedelta(hours=2)
        )
        decoded = decode_access_token(token)
        assert decoded is not None
        assert decoded["sub"] == "user1"

    def test_expired_token_returns_none(self):
        token = create_access_token(
            {"sub": "user1"}, expires_delta=timedelta(seconds=-1)
        )
        decoded = decode_access_token(token)
        assert decoded is None

    def test_invalid_token_returns_none(self):
        decoded = decode_access_token("not.a.valid.token")
        assert decoded is None

    def test_empty_token_returns_none(self):
        decoded = decode_access_token("")
        assert decoded is None

    def test_tampered_token_returns_none(self):
        token = create_access_token({"sub": "user1"})
        # Tamper with the token
        tampered = token[:-5] + "XXXXX"
        decoded = decode_access_token(tampered)
        assert decoded is None

    def test_create_api_key_token(self):
        import uuid

        api_key_id = uuid.uuid4()
        user_id = uuid.uuid4()
        token = create_api_key_token(api_key_id, user_id)
        decoded = decode_access_token(token)
        assert decoded is not None
        assert decoded["sub"] == str(user_id)
        assert decoded["api_key_id"] == str(api_key_id)
        assert decoded["type"] == "api_key"
