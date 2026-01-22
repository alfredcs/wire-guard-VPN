"""Pydantic schemas for request/response validation."""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime


# User Schemas
class UserBase(BaseModel):
    """Base user schema."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    """Schema for user creation."""
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """Schema for user update."""
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """Schema for user response."""
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Authentication Schemas
class LoginRequest(BaseModel):
    """Schema for login request."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Schema for token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenRefreshRequest(BaseModel):
    """Schema for token refresh request."""
    refresh_token: str


class TokenValidateResponse(BaseModel):
    """Schema for token validation response."""
    valid: bool
    user_id: Optional[int] = None
    username: Optional[str] = None
    expires_at: Optional[datetime] = None


# VPN Schemas
class VPNProvisionRequest(BaseModel):
    """Schema for VPN provision request."""
    device_name: Optional[str] = Field(None, max_length=50)


class VPNConfigResponse(BaseModel):
    """Schema for VPN configuration response."""
    interface: dict
    peer: dict
    config_file: str  # Complete WireGuard config as string


class PeerResponse(BaseModel):
    """Schema for peer response."""
    id: int
    user_id: int
    username: Optional[str] = None
    assigned_ip: str
    is_active: bool
    created_at: datetime
    last_handshake: Optional[datetime] = None
    transfer_rx: int
    transfer_tx: int

    model_config = ConfigDict(from_attributes=True)


class VPNStatusResponse(BaseModel):
    """Schema for VPN status response."""
    connected: bool
    assigned_ip: Optional[str] = None
    last_handshake: Optional[datetime] = None
    transfer_rx: int = 0
    transfer_tx: int = 0


# Admin Schemas
class UserListResponse(BaseModel):
    """Schema for user list response."""
    total: int
    users: list[UserResponse]


class PeerListResponse(BaseModel):
    """Schema for peer list response."""
    total: int
    peers: list[PeerResponse]


class ServerStatusResponse(BaseModel):
    """Schema for server status response."""
    status: str
    wireguard_interface: str
    active_peers: int
    total_users: int
    uptime: Optional[str] = None


# Generic Response Schemas
class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    status: str = "success"


class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str
    detail: Optional[str] = None
    status: str = "error"
