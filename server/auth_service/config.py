"""Configuration management for VPN authentication service."""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings."""

    # Database
    database_url: str = "sqlite:///vpn.db"

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # WireGuard
    wg_interface: str = "wg0"
    wg_port: int = 51820
    wg_address: str = "10.0.0.1/24"
    wg_network: str = "10.0.0.0/24"
    wg_dns: str = "1.1.1.1,8.8.8.8"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8443
    api_workers: int = 4

    # TLS
    tls_enabled: bool = False
    tls_cert_path: Optional[str] = None
    tls_key_path: Optional[str] = None

    # Security
    rate_limit_per_minute: int = 60
    bcrypt_rounds: int = 12

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
