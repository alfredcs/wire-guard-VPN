"""Database models for VPN authentication service."""

from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class User(Base):
    """User model."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    tokens = relationship("Token", back_populates="user", cascade="all, delete-orphan")
    peers = relationship("Peer", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"


class Token(Base):
    """Token model for JWT tokens."""

    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_type = Column(String(20), nullable=False)  # 'access' or 'refresh'
    jti = Column(String(36), unique=True, index=True, nullable=False)  # JWT ID
    is_revoked = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    ip_address = Column(String(45), nullable=True)  # Support IPv6
    user_agent = Column(String(255), nullable=True)

    # Relationships
    user = relationship("User", back_populates="tokens")

    def __repr__(self):
        return f"<Token(jti='{self.jti}', type='{self.token_type}', revoked={self.is_revoked})>"


class Peer(Base):
    """WireGuard peer model."""

    __tablename__ = "peers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    public_key = Column(String(44), unique=True, index=True, nullable=False)
    private_key = Column(String(44), nullable=False)  # Encrypted
    preshared_key = Column(String(44), nullable=True)
    assigned_ip = Column(String(18), unique=True, nullable=False)  # e.g., 10.0.0.2/32
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_handshake = Column(DateTime(timezone=True), nullable=True)
    endpoint = Column(String(50), nullable=True)
    allowed_ips = Column(String(255), default="0.0.0.0/0,::/0")
    transfer_rx = Column(Integer, default=0)  # Bytes received
    transfer_tx = Column(Integer, default=0)  # Bytes transmitted

    # Relationships
    user = relationship("User", back_populates="peers")

    def __repr__(self):
        return f"<Peer(user_id={self.user_id}, ip='{self.assigned_ip}', active={self.is_active})>"


class AuditLog(Base):
    """Audit log for tracking important actions."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(50), nullable=False)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(50), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False)  # 'success' or 'failure'
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<AuditLog(action='{self.action}', status='{self.status}')>"
