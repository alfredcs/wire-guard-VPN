"""Client configuration management."""

from pathlib import Path
import json
from typing import Optional
import os

# Configuration paths
CONFIG_DIR = Path.home() / ".vpn-client"
CONFIG_FILE = CONFIG_DIR / "config.json"
WG_CONFIG_DIR = Path("/usr/local/etc/wireguard")
WG_CONFIG_FILE = WG_CONFIG_DIR / "wg-vpn.conf"

# Keychain configuration
KEYCHAIN_SERVICE = "com.vpn.client"
KEYCHAIN_ACCESS_TOKEN = "access_token"
KEYCHAIN_REFRESH_TOKEN = "refresh_token"


class ClientConfig:
    """Client configuration manager."""

    def __init__(self):
        self.config_dir = CONFIG_DIR
        self.config_file = CONFIG_FILE
        self._config = self._load_config()

    def _load_config(self) -> dict:
        """Load configuration from file."""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_config(self):
        """Save configuration to file."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self._config, f, indent=2)
        # Set restrictive permissions
        os.chmod(self.config_file, 0o600)

    def get(self, key: str, default=None):
        """Get configuration value."""
        return self._config.get(key, default)

    def set(self, key: str, value):
        """Set configuration value."""
        self._config[key] = value
        self._save_config()

    def delete(self, key: str):
        """Delete configuration value."""
        if key in self._config:
            del self._config[key]
            self._save_config()

    def clear(self):
        """Clear all configuration."""
        self._config = {}
        self._save_config()


# Global config instance
config = ClientConfig()
