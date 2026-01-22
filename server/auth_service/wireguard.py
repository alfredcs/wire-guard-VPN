"""WireGuard VPN management."""

import subprocess
import ipaddress
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from .config import settings
from .models import Peer, User
import logging
import re

logger = logging.getLogger(__name__)


class WireGuardManager:
    """Manager for WireGuard VPN operations."""

    @staticmethod
    def generate_keypair() -> tuple[str, str]:
        """Generate WireGuard private and public key pair.

        Returns:
            Tuple of (private_key, public_key)

        Raises:
            RuntimeError: If key generation fails
        """
        try:
            # Generate private key
            private_key = subprocess.run(
                ["wg", "genkey"],
                capture_output=True,
                text=True,
                check=True
            ).stdout.strip()

            # Generate public key from private key
            public_key = subprocess.run(
                ["wg", "pubkey"],
                input=private_key,
                capture_output=True,
                text=True,
                check=True
            ).stdout.strip()

            return private_key, public_key

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to generate WireGuard keys: {e}")
            raise RuntimeError("Failed to generate WireGuard keys")
        except FileNotFoundError:
            logger.error("WireGuard tools not found. Is wg-tools installed?")
            raise RuntimeError("WireGuard tools not installed")

    @staticmethod
    def generate_preshared_key() -> str:
        """Generate WireGuard preshared key.

        Returns:
            Preshared key

        Raises:
            RuntimeError: If key generation fails
        """
        try:
            psk = subprocess.run(
                ["wg", "genpsk"],
                capture_output=True,
                text=True,
                check=True
            ).stdout.strip()
            return psk
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to generate preshared key: {e}")
            raise RuntimeError("Failed to generate preshared key")

    @staticmethod
    def get_next_available_ip(db: Session) -> str:
        """Get next available IP address in the VPN network.

        Args:
            db: Database session

        Returns:
            Next available IP address with /32 suffix

        Raises:
            HTTPException: If no IP addresses are available
        """
        # Parse network configuration
        network = ipaddress.IPv4Network(settings.wg_network)
        server_ip = ipaddress.IPv4Address(settings.wg_address.split('/')[0])

        # Get all assigned IPs
        assigned_ips = db.query(Peer.assigned_ip).all()
        assigned_ip_set = {
            ipaddress.IPv4Address(ip[0].split('/')[0])
            for ip in assigned_ips
        }

        # Find next available IP
        for ip in network.hosts():
            # Skip server IP and already assigned IPs
            if ip != server_ip and ip not in assigned_ip_set:
                return f"{ip}/32"

        raise HTTPException(
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
            detail="No available IP addresses in VPN network"
        )

    @staticmethod
    def add_peer(
        db: Session,
        user: User,
        public_key: str,
        private_key: str,
        assigned_ip: str,
        preshared_key: Optional[str] = None
    ) -> Peer:
        """Add a new WireGuard peer.

        Args:
            db: Database session
            user: User object
            public_key: Peer public key
            private_key: Peer private key
            assigned_ip: Assigned IP address
            preshared_key: Optional preshared key

        Returns:
            Created Peer object
        """
        # Create peer in database
        peer = Peer(
            user_id=user.id,
            public_key=public_key,
            private_key=private_key,
            preshared_key=preshared_key,
            assigned_ip=assigned_ip,
            is_active=True
        )
        db.add(peer)
        db.commit()
        db.refresh(peer)

        # Add peer to WireGuard interface
        try:
            WireGuardManager.add_peer_to_interface(
                public_key=public_key,
                allowed_ips=assigned_ip,
                preshared_key=preshared_key
            )
        except Exception as e:
            logger.error(f"Failed to add peer to interface: {e}")
            # Rollback database change
            db.delete(peer)
            db.commit()
            raise

        logger.info(f"Added peer for user {user.username} with IP {assigned_ip}")
        return peer

    @staticmethod
    def add_peer_to_interface(
        public_key: str,
        allowed_ips: str,
        preshared_key: Optional[str] = None
    ) -> None:
        """Add peer to WireGuard interface.

        Args:
            public_key: Peer public key
            allowed_ips: Allowed IP addresses
            preshared_key: Optional preshared key

        Raises:
            RuntimeError: If adding peer fails
        """
        try:
            cmd = [
                "wg", "set", settings.wg_interface,
                "peer", public_key,
                "allowed-ips", allowed_ips
            ]

            if preshared_key:
                cmd.extend(["preshared-key", "/dev/stdin"])

            result = subprocess.run(
                cmd,
                input=preshared_key if preshared_key else None,
                capture_output=True,
                text=True,
                check=True
            )

            logger.debug(f"Added peer {public_key} to interface")

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to add peer to interface: {e.stderr}")
            raise RuntimeError(f"Failed to add peer to WireGuard interface: {e.stderr}")

    @staticmethod
    def remove_peer(db: Session, peer: Peer) -> None:
        """Remove a WireGuard peer.

        Args:
            db: Database session
            peer: Peer object

        Raises:
            RuntimeError: If removing peer fails
        """
        try:
            # Remove from WireGuard interface
            WireGuardManager.remove_peer_from_interface(peer.public_key)

            # Mark as inactive in database
            peer.is_active = False
            db.commit()

            logger.info(f"Removed peer {peer.id} (IP: {peer.assigned_ip})")

        except Exception as e:
            logger.error(f"Failed to remove peer: {e}")
            raise

    @staticmethod
    def remove_peer_from_interface(public_key: str) -> None:
        """Remove peer from WireGuard interface.

        Args:
            public_key: Peer public key

        Raises:
            RuntimeError: If removing peer fails
        """
        try:
            subprocess.run(
                ["wg", "set", settings.wg_interface, "peer", public_key, "remove"],
                capture_output=True,
                text=True,
                check=True
            )
            logger.debug(f"Removed peer {public_key} from interface")

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to remove peer from interface: {e.stderr}")
            raise RuntimeError(f"Failed to remove peer from WireGuard interface: {e.stderr}")

    @staticmethod
    def get_server_public_key() -> str:
        """Get server's public key.

        Returns:
            Server public key

        Raises:
            RuntimeError: If getting public key fails
        """
        try:
            result = subprocess.run(
                ["wg", "show", settings.wg_interface, "public-key"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get server public key: {e.stderr}")
            raise RuntimeError("Failed to get server public key")

    @staticmethod
    def get_interface_status() -> Dict[str, Any]:
        """Get WireGuard interface status.

        Returns:
            Interface status information

        Raises:
            RuntimeError: If getting status fails
        """
        try:
            result = subprocess.run(
                ["wg", "show", settings.wg_interface],
                capture_output=True,
                text=True,
                check=True
            )

            # Parse output
            output = result.stdout
            status = {
                "interface": settings.wg_interface,
                "peers": []
            }

            # Simple parsing of wg output
            lines = output.split('\n')
            current_peer = None

            for line in lines:
                line = line.strip()
                if line.startswith("peer:"):
                    if current_peer:
                        status["peers"].append(current_peer)
                    current_peer = {"public_key": line.split(": ")[1]}
                elif current_peer:
                    if line.startswith("endpoint:"):
                        current_peer["endpoint"] = line.split(": ")[1]
                    elif line.startswith("allowed ips:"):
                        current_peer["allowed_ips"] = line.split(": ")[1]
                    elif line.startswith("latest handshake:"):
                        current_peer["latest_handshake"] = line.split(": ")[1]
                    elif line.startswith("transfer:"):
                        current_peer["transfer"] = line.split(": ")[1]

            if current_peer:
                status["peers"].append(current_peer)

            return status

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get interface status: {e.stderr}")
            raise RuntimeError("Failed to get WireGuard interface status")

    @staticmethod
    def generate_client_config(
        peer: Peer,
        server_endpoint: str
    ) -> str:
        """Generate WireGuard client configuration.

        Args:
            peer: Peer object
            server_endpoint: Server endpoint (IP:port or domain:port)

        Returns:
            Complete WireGuard configuration as string
        """
        try:
            server_public_key = WireGuardManager.get_server_public_key()
        except Exception as e:
            logger.error(f"Failed to get server public key: {e}")
            raise

        config = f"""[Interface]
PrivateKey = {peer.private_key}
Address = {peer.assigned_ip}
DNS = {settings.wg_dns}

[Peer]
PublicKey = {server_public_key}
Endpoint = {server_endpoint}:{settings.wg_port}
AllowedIPs = {peer.allowed_ips}
PersistentKeepalive = 25
"""

        if peer.preshared_key:
            config += f"PresharedKey = {peer.preshared_key}\n"

        return config

    @staticmethod
    def get_peer_stats(db: Session, user: User) -> Optional[Dict[str, Any]]:
        """Get peer statistics for a user.

        Args:
            db: Database session
            user: User object

        Returns:
            Peer statistics or None if no active peer
        """
        peer = db.query(Peer).filter(
            Peer.user_id == user.id,
            Peer.is_active == True
        ).first()

        if not peer:
            return None

        return {
            "assigned_ip": peer.assigned_ip,
            "last_handshake": peer.last_handshake,
            "transfer_rx": peer.transfer_rx,
            "transfer_tx": peer.transfer_tx,
            "is_active": peer.is_active
        }
