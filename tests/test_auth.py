"""Tests for authentication module."""

import pytest
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "server"))

from auth_service.auth import AuthService
from auth_service.models import User, Token


class TestPasswordHashing:
    """Test password hashing functionality."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "test_password_123"
        hashed = AuthService.hash_password(password)

        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "test_password_123"
        hashed = AuthService.hash_password(password)

        assert AuthService.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = AuthService.hash_password(password)

        assert AuthService.verify_password(wrong_password, hashed) is False


class TestTokenGeneration:
    """Test JWT token generation."""

    def test_create_access_token(self):
        """Test access token creation."""
        token, jti, expires = AuthService.create_access_token(
            user_id=1,
            username="testuser",
            is_admin=False
        )

        assert isinstance(token, str)
        assert len(token) > 0
        assert isinstance(jti, str)
        assert isinstance(expires, datetime)
        assert expires > datetime.utcnow()

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        token, jti, expires = AuthService.create_refresh_token(
            user_id=1,
            username="testuser"
        )

        assert isinstance(token, str)
        assert len(token) > 0
        assert isinstance(jti, str)
        assert isinstance(expires, datetime)
        assert expires > datetime.utcnow()

    def test_decode_token(self):
        """Test token decoding."""
        token, jti, expires = AuthService.create_access_token(
            user_id=1,
            username="testuser",
            is_admin=False
        )

        payload = AuthService.decode_token(token)

        assert payload["sub"] == "1"
        assert payload["username"] == "testuser"
        assert payload["is_admin"] is False
        assert payload["type"] == "access"
        assert payload["jti"] == jti

    def test_decode_expired_token(self):
        """Test decoding expired token."""
        from fastapi import HTTPException
        # Create token with negative expiry
        token, jti, expires = AuthService.create_access_token(
            user_id=1,
            username="testuser",
            is_admin=False,
            expires_delta=timedelta(seconds=-1)
        )

        with pytest.raises(HTTPException) as exc_info:
            AuthService.decode_token(token)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()


class TestAuthentication:
    """Test authentication functionality."""

    def test_authenticate_user_success(self, db_session, test_user):
        """Test successful user authentication."""
        user = AuthService.authenticate_user(
            db_session,
            "testuser",
            "password123"
        )

        assert user is not None
        assert user.username == "testuser"

    def test_authenticate_user_wrong_password(self, db_session, test_user):
        """Test authentication with wrong password."""
        user = AuthService.authenticate_user(
            db_session,
            "testuser",
            "wrong_password"
        )

        assert user is None

    def test_authenticate_user_not_found(self, db_session):
        """Test authentication with non-existent user."""
        user = AuthService.authenticate_user(
            db_session,
            "nonexistent",
            "password"
        )

        assert user is None

    def test_token_revocation(self, db_session, test_user):
        """Test token revocation."""
        # Create and save token
        token, jti, expires = AuthService.create_access_token(
            test_user.id,
            test_user.username,
            False
        )

        AuthService.save_token(
            db_session,
            test_user.id,
            "access",
            jti,
            expires
        )

        # Verify not revoked
        assert AuthService.is_token_revoked(db_session, jti) is False

        # Revoke token
        result = AuthService.revoke_token(db_session, jti)
        assert result is True

        # Verify revoked
        assert AuthService.is_token_revoked(db_session, jti) is True


class TestAPIAuthentication:
    """Test API authentication endpoints."""

    def test_register_user(self, client):
        """Test user registration."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "password123"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert "hashed_password" not in data

    def test_register_duplicate_username(self, client, test_user):
        """Test registration with duplicate username."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "different@example.com",
                "password": "password123"
            }
        )

        assert response.status_code == 400

    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "password123"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user):
        """Test login with wrong password."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "wrong_password"
            }
        )

        assert response.status_code == 401

    def test_validate_token(self, client, auth_headers):
        """Test token validation."""
        response = client.get(
            "/api/v1/auth/validate",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["username"] == "testuser"

    def test_logout(self, client, auth_headers):
        """Test logout."""
        response = client.post(
            "/api/v1/auth/logout",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data["message"].lower()
