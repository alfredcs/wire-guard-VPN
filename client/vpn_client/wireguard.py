"""WireGuard client management."""

import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
import logging
import os

from .config import WG_CONFIG_DIR, WG_CONFIG_FILE

logger = logging.getLogger(__name__)

# WireGuard interface name for MacOS
WG_INTERFACE = "utun3"


class WireGuardClient:
    """WireGuard client manager."""

    @staticmethod
    def write_config(config_content: str) -> Path:
        """Write WireGuard configuration file.

        Args:
            config_content: WireGuard configuration content

        Returns:
            Path to config file

        Raises:
            Exception: If writing config fails
        """
        try:
            # Create config directory if it doesn't exist
            WG_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

            # Write config file
            with open(WG_CONFIG_FILE, 'w') as f:
                f.write(config_content)

            # Set restrictive permissions (read/write for owner only)
            os.chmod(WG_CONFIG_FILE, 0o600)

            logger.info(f"Configuration written to {WG_CONFIG_FILE}")
            return WG_CONFIG_FILE

        except Exception as e:
            logger.error(f"Failed to write config: {e}")
            raise Exception(f"Failed to write WireGuard configuration: {str(e)}")

    @staticmethod
    def connect() -> None:
        """Connect to VPN using wg-quick.

        Raises:
            Exception: If connection fails
        """
        if not WG_CONFIG_FILE.exists():
            raise Exception("VPN not configured. Please provision first.")

        try:
            # Check if already connected
            if WireGuardClient.is_connected():
                logger.info("VPN already connected")
                return

            # Use wg-quick to bring up the interface
            result = subprocess.run(
                ["sudo", "wg-quick", "up", str(WG_CONFIG_FILE)],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                # Check if already exists
                if "already exists" in result.stderr or "Address already in use" in result.stderr:
                    logger.info("VPN interface already exists")
                    return
                raise Exception(f"Failed to connect: {result.stderr}")

            logger.info("VPN connected successfully")

        except FileNotFoundError:
            raise Exception("wg-quick not found. Please install WireGuard tools.")
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            raise

    @staticmethod
    def disconnect() -> None:
        """Disconnect from VPN.

        Raises:
            Exception: If disconnection fails
        """
        try:
            # Use wg-quick to bring down the interface
            result = subprocess.run(
                ["sudo", "wg-quick", "down", str(WG_CONFIG_FILE)],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                # Check if interface doesn't exist
                if "does not exist" in result.stderr or "No such device" in result.stderr:
                    logger.info("VPN interface doesn't exist")
                    return
                raise Exception(f"Failed to disconnect: {result.stderr}")

            logger.info("VPN disconnected successfully")

        except FileNotFoundError:
            raise Exception("wg-quick not found. Please install WireGuard tools.")
        except Exception as e:
            logger.error(f"Disconnection failed: {e}")
            raise

    @staticmethod
    def is_connected() -> bool:
        """Check if VPN is connected.

        Returns:
            True if connected, False otherwise
        """
        try:
            result = subprocess.run(
                ["wg", "show"],
                capture_output=True,
                text=True,
                check=False
            )

            # If wg show returns successfully and has output, we're connected
            if result.returncode == 0 and result.stdout.strip():
                # Check if our config interface is in the output
                return WG_CONFIG_FILE.stem in result.stdout or WG_INTERFACE in result.stdout

            return False

        except FileNotFoundError:
            logger.warning("wg command not found")
            return False
        except Exception as e:
            logger.error(f"Failed to check connection status: {e}")
            return False

    @staticmethod
    def get_status() -> Optional[Dict[str, Any]]:
        """Get VPN connection status.

        Returns:
            Status dictionary or None if not connected
        """
        if not WireGuardClient.is_connected():
            return None

        try:
            result = subprocess.run(
                ["wg", "show"],
                capture_output=True,
                text=True,
                check=True
            )

            # Parse output
            output = result.stdout
            status = {
                "connected": True,
                "interface": None,
                "endpoint": None,
                "latest_handshake": None,
                "transfer": None
            }

            # Simple parsing
            lines = output.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith("interface:"):
                    status["interface"] = line.split(": ")[1]
                elif line.startswith("endpoint:"):
                    status["endpoint"] = line.split(": ")[1]
                elif line.startswith("latest handshake:"):
                    status["latest_handshake"] = line.split(": ")[1]
                elif line.startswith("transfer:"):
                    status["transfer"] = line.split(": ")[1]

            return status

        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return None

    @staticmethod
    def remove_config() -> None:
        """Remove VPN configuration file."""
        try:
            if WG_CONFIG_FILE.exists():
                WG_CONFIG_FILE.unlink()
                logger.info("VPN configuration removed")
        except Exception as e:
            logger.error(f"Failed to remove config: {e}")
            raise Exception(f"Failed to remove configuration: {str(e)}")
