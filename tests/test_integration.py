"""Integration tests for VPN server."""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "server"))

from auth_service.wireguard import WireGuardManager


class TestCompleteAuthFlow:
    """Test complete authentication flow."""

    def test_register_login_validate_logout(self, client):
        """Test complete authentication lifecycle."""
        # 1. Register
        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "integrationtest",
                "email": "integration@test.com",
                "password": "test123456"
            }
        )
        assert register_response.status_code == 201

        # 2. Login
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "integrationtest",
                "password": "test123456"
            }
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        access_token = tokens["access_token"]

        # 3. Validate token
        validate_response = client.get(
            "/api/v1/auth/validate",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert validate_response.status_code == 200
        assert validate_response.json()["valid"] is True

        # 4. Logout
        logout_response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert logout_response.status_code == 200


class TestVPNProvisioningFlow:
    """Test VPN provisioning flow."""

    @patch.object(WireGuardManager, 'generate_keypair')
    @patch.object(WireGuardManager, 'generate_preshared_key')
    @patch.object(WireGuardManager, 'add_peer_to_interface')
    @patch.object(WireGuardManager, 'get_server_public_key')
    @patch.object(WireGuardManager, 'remove_peer_from_interface')
    def test_provision_status_disconnect(
        self,
        mock_remove_peer,
        mock_server_key,
        mock_add_peer,
        mock_psk,
        mock_keypair,
        client,
        auth_headers
    ):
        """Test provision, status check, and disconnect flow."""
        # Setup mocks
        mock_keypair.return_value = ("PRIVATE_KEY", "PUBLIC_KEY")
        mock_psk.return_value = "PSK"
        mock_server_key.return_value = "SERVER_KEY"
        mock_add_peer.return_value = None
        mock_remove_peer.return_value = None

        # 1. Provision VPN
        provision_response = client.post(
            "/api/v1/vpn/provision",
            headers=auth_headers,
            json={}
        )
        assert provision_response.status_code == 200
        config = provision_response.json()
        assert "config_file" in config

        # 2. Check status
        status_response = client.get(
            "/api/v1/vpn/status",
            headers=auth_headers
        )
        assert status_response.status_code == 200
        status = status_response.json()
        assert "assigned_ip" in status

        # 3. Disconnect
        disconnect_response = client.delete(
            "/api/v1/vpn/disconnect",
            headers=auth_headers
        )
        assert disconnect_response.status_code == 200


class TestAdminOperations:
    """Test admin operations."""

    def test_admin_list_users(self, client, admin_headers, test_user):
        """Test admin listing users."""
        response = client.get(
            "/api/v1/admin/users",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2  # admin + test_user

    def test_admin_list_peers(self, client, admin_headers):
        """Test admin listing peers."""
        response = client.get(
            "/api/v1/admin/peers",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "peers" in data
        assert "total" in data

    def test_admin_server_status(self, client, admin_headers):
        """Test admin getting server status."""
        response = client.get(
            "/api/v1/admin/status",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "active_peers" in data
        assert "total_users" in data

    def test_non_admin_cannot_access_admin_endpoints(self, client, auth_headers):
        """Test that non-admin cannot access admin endpoints."""
        response = client.get(
            "/api/v1/admin/users",
            headers=auth_headers
        )

        assert response.status_code == 403


class TestTokenRefresh:
    """Test token refresh flow."""

    def test_refresh_token_flow(self, client, test_user):
        """Test refreshing access token."""
        # Login to get tokens
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "password123"
            }
        )
        tokens = login_response.json()
        refresh_token = tokens["refresh_token"]

        # Refresh access token
        refresh_response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()
        assert "access_token" in new_tokens
        assert new_tokens["access_token"] != tokens["access_token"]


class TestErrorHandling:
    """Test error handling."""

    def test_unauthorized_access(self, client):
        """Test accessing protected endpoint without token."""
        response = client.get("/api/v1/vpn/status")
        assert response.status_code == 403  # No Authorization header

    def test_invalid_token(self, client):
        """Test accessing with invalid token."""
        response = client.get(
            "/api/v1/vpn/status",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401

    def test_duplicate_username(self, client, test_user):
        """Test registering with duplicate username."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "different@example.com",
                "password": "password123"
            }
        )
        assert response.status_code == 400

    def test_invalid_login(self, client):
        """Test login with invalid credentials."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistent",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401
