"""Tests for WireGuard management module."""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "server"))

from auth_service.wireguard import WireGuardManager
from auth_service.models import Peer


class TestKeyGeneration:
    """Test WireGuard key generation."""

    @patch('subprocess.run')
    def test_generate_keypair(self, mock_run):
        """Test keypair generation."""
        # Mock private key generation
        mock_private = Mock()
        mock_private.stdout = "PRIVATE_KEY_HERE\n"
        mock_private.returncode = 0

        # Mock public key generation
        mock_public = Mock()
        mock_public.stdout = "PUBLIC_KEY_HERE\n"
        mock_public.returncode = 0

        mock_run.side_effect = [mock_private, mock_public]

        private_key, public_key = WireGuardManager.generate_keypair()

        assert private_key == "PRIVATE_KEY_HERE"
        assert public_key == "PUBLIC_KEY_HERE"
        assert mock_run.call_count == 2

    @patch('subprocess.run')
    def test_generate_preshared_key(self, mock_run):
        """Test preshared key generation."""
        mock_result = Mock()
        mock_result.stdout = "PRESHARED_KEY_HERE\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        psk = WireGuardManager.generate_preshared_key()

        assert psk == "PRESHARED_KEY_HERE"
        mock_run.assert_called_once()


class TestIPAllocation:
    """Test IP address allocation."""

    def test_get_next_available_ip(self, db_session, test_user):
        """Test getting next available IP."""
        ip = WireGuardManager.get_next_available_ip(db_session)

        assert ip.startswith("10.0.0.")
        assert ip.endswith("/32")
        assert ip != "10.0.0.1/32"  # Server IP

    def test_get_next_available_ip_with_existing(self, db_session, test_user):
        """Test IP allocation with existing peers."""
        # Create a peer with IP 10.0.0.2
        peer = Peer(
            user_id=test_user.id,
            public_key="test_key",
            private_key="test_private",
            assigned_ip="10.0.0.2/32",
            is_active=True
        )
        db_session.add(peer)
        db_session.commit()

        # Get next IP
        ip = WireGuardManager.get_next_available_ip(db_session)

        # Should skip 10.0.0.1 (server) and 10.0.0.2 (taken)
        assert ip == "10.0.0.3/32"


class TestConfigGeneration:
    """Test WireGuard configuration generation."""

    @patch.object(WireGuardManager, 'get_server_public_key')
    def test_generate_client_config(self, mock_get_server_key, test_user):
        """Test client configuration generation."""
        mock_get_server_key.return_value = "SERVER_PUBLIC_KEY"

        peer = Peer(
            user_id=test_user.id,
            public_key="CLIENT_PUBLIC_KEY",
            private_key="CLIENT_PRIVATE_KEY",
            assigned_ip="10.0.0.2/32",
            allowed_ips="0.0.0.0/0",
            is_active=True
        )

        config = WireGuardManager.generate_client_config(
            peer,
            "vpn.example.com"
        )

        assert "[Interface]" in config
        assert "[Peer]" in config
        assert "CLIENT_PRIVATE_KEY" in config
        assert "10.0.0.2/32" in config
        assert "SERVER_PUBLIC_KEY" in config
        assert "vpn.example.com:51820" in config


class TestPeerManagement:
    """Test peer management operations."""

    @patch('subprocess.run')
    def test_add_peer_to_interface(self, mock_run):
        """Test adding peer to WireGuard interface."""
        mock_run.return_value = Mock(returncode=0)

        WireGuardManager.add_peer_to_interface(
            public_key="PUBLIC_KEY",
            allowed_ips="10.0.0.2/32"
        )

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "wg" in call_args
        assert "set" in call_args
        assert "PUBLIC_KEY" in call_args

    @patch('subprocess.run')
    def test_remove_peer_from_interface(self, mock_run):
        """Test removing peer from WireGuard interface."""
        mock_run.return_value = Mock(returncode=0)

        WireGuardManager.remove_peer_from_interface("PUBLIC_KEY")

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "wg" in call_args
        assert "set" in call_args
        assert "remove" in call_args


class TestAPIVPNEndpoints:
    """Test VPN API endpoints."""

    @patch.object(WireGuardManager, 'generate_keypair')
    @patch.object(WireGuardManager, 'generate_preshared_key')
    @patch.object(WireGuardManager, 'add_peer_to_interface')
    @patch.object(WireGuardManager, 'get_server_public_key')
    def test_provision_vpn(
        self,
        mock_server_key,
        mock_add_peer,
        mock_psk,
        mock_keypair,
        client,
        auth_headers
    ):
        """Test VPN provisioning."""
        mock_keypair.return_value = ("PRIVATE_KEY", "PUBLIC_KEY")
        mock_psk.return_value = "PSK"
        mock_server_key.return_value = "SERVER_KEY"
        mock_add_peer.return_value = None

        response = client.post(
            "/api/v1/vpn/provision",
            headers=auth_headers,
            json={}
        )

        assert response.status_code == 200
        data = response.json()
        assert "interface" in data
        assert "peer" in data
        assert "config_file" in data
        assert data["interface"]["private_key"] == "PRIVATE_KEY"

    def test_get_vpn_status_no_peer(self, client, auth_headers):
        """Test VPN status with no peer."""
        response = client.get(
            "/api/v1/vpn/status",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is False

    @patch.object(WireGuardManager, 'remove_peer_from_interface')
    def test_disconnect_vpn(self, mock_remove, client, auth_headers, db_session, test_user):
        """Test VPN disconnection."""
        # Create a peer first
        peer = Peer(
            user_id=test_user.id,
            public_key="test_key",
            private_key="test_private",
            assigned_ip="10.0.0.2/32",
            is_active=True
        )
        db_session.add(peer)
        db_session.commit()

        mock_remove.return_value = None

        response = client.delete(
            "/api/v1/vpn/disconnect",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data["message"].lower()
