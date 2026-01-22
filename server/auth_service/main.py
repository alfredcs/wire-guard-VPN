"""FastAPI main application for VPN authentication service."""

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import logging
from datetime import datetime

from . import __version__
from .config import settings
from .database import get_db, init_db
from .models import User, Peer, AuditLog
from .schemas import (
    UserCreate, UserResponse, LoginRequest, TokenResponse,
    TokenRefreshRequest, TokenValidateResponse, VPNProvisionRequest,
    VPNConfigResponse, VPNStatusResponse, PeerResponse,
    UserListResponse, PeerListResponse, ServerStatusResponse,
    MessageResponse, ErrorResponse
)
from .auth import (
    AuthService, get_current_user, get_current_admin_user
)
from .wireguard import WireGuardManager

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="VPN Authentication Service",
    description="Bearer token authentication service for WireGuard VPN",
    version=__version__,
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    logger.info("Starting VPN Authentication Service")
    init_db()
    logger.info("Database initialized")


# Health check endpoint
@app.get("/health", response_model=MessageResponse)
async def health_check():
    """Health check endpoint."""
    return MessageResponse(message="Service is healthy", status="success")


# ============================================================================
# Authentication Endpoints
# ============================================================================

@app.post("/api/v1/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Register a new user."""
    # Check if username exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # Check if email exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )

    # Create user
    hashed_password = AuthService.hash_password(user_data.password)
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action="user_register",
        resource_type="user",
        resource_id=str(user.id),
        ip_address=request.client.host,
        status="success"
    )
    db.add(audit)
    db.commit()

    logger.info(f"User registered: {user.username}")
    return user


@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Login and get bearer tokens."""
    # Authenticate user
    user = AuthService.authenticate_user(db, login_data.username, login_data.password)
    if not user:
        # Audit log
        audit = AuditLog(
            action="user_login",
            resource_type="user",
            details=f"Failed login attempt for username: {login_data.username}",
            ip_address=request.client.host,
            status="failure"
        )
        db.add(audit)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    # Create tokens
    access_token, access_jti, access_expires = AuthService.create_access_token(
        user.id, user.username, user.is_admin
    )
    refresh_token, refresh_jti, refresh_expires = AuthService.create_refresh_token(
        user.id, user.username
    )

    # Save tokens to database
    ip_address = request.client.host
    user_agent = request.headers.get("user-agent")

    AuthService.save_token(
        db, user.id, "access", access_jti, access_expires,
        ip_address, user_agent
    )
    AuthService.save_token(
        db, user.id, "refresh", refresh_jti, refresh_expires,
        ip_address, user_agent
    )

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action="user_login",
        resource_type="user",
        resource_id=str(user.id),
        ip_address=ip_address,
        user_agent=user_agent,
        status="success"
    )
    db.add(audit)
    db.commit()

    logger.info(f"User logged in: {user.username}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60
    )


@app.post("/api/v1/auth/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: TokenRefreshRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token."""
    # Decode refresh token
    payload = AuthService.decode_token(refresh_data.refresh_token)

    # Check token type
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )

    # Check if token is revoked
    jti = payload.get("jti")
    if AuthService.is_token_revoked(db, jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked"
        )

    # Get user
    user_id = int(payload.get("sub"))
    user = db.query(User).filter(User.id == user_id).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    # Create new access token
    access_token, access_jti, access_expires = AuthService.create_access_token(
        user.id, user.username, user.is_admin
    )

    # Save new access token
    ip_address = request.client.host
    user_agent = request.headers.get("user-agent")

    AuthService.save_token(
        db, user.id, "access", access_jti, access_expires,
        ip_address, user_agent
    )

    logger.info(f"Token refreshed for user: {user.username}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_data.refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60
    )


@app.post("/api/v1/auth/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logout and revoke tokens."""
    # Get token from header
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = AuthService.decode_token(token)
        jti = payload.get("jti")

        # Revoke token
        AuthService.revoke_token(db, jti)

        # Audit log
        audit = AuditLog(
            user_id=current_user.id,
            action="user_logout",
            resource_type="user",
            resource_id=str(current_user.id),
            ip_address=request.client.host,
            status="success"
        )
        db.add(audit)
        db.commit()

        logger.info(f"User logged out: {current_user.username}")

    return MessageResponse(message="Logged out successfully")


@app.get("/api/v1/auth/validate", response_model=TokenValidateResponse)
async def validate_token(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Validate bearer token."""
    return TokenValidateResponse(
        valid=True,
        user_id=current_user.id,
        username=current_user.username
    )


# ============================================================================
# VPN Endpoints
# ============================================================================

@app.post("/api/v1/vpn/provision", response_model=VPNConfigResponse)
async def provision_vpn(
    provision_data: VPNProvisionRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Provision VPN configuration for user."""
    # Check if user already has an active peer
    existing_peer = db.query(Peer).filter(
        Peer.user_id == current_user.id,
        Peer.is_active == True
    ).first()

    if existing_peer:
        # Return existing configuration
        server_endpoint = request.client.host  # Should be server's public IP/domain
        config = WireGuardManager.generate_client_config(existing_peer, server_endpoint)

        return VPNConfigResponse(
            interface={
                "private_key": existing_peer.private_key,
                "address": existing_peer.assigned_ip,
                "dns": settings.wg_dns
            },
            peer={
                "public_key": WireGuardManager.get_server_public_key(),
                "endpoint": f"{server_endpoint}:{settings.wg_port}",
                "allowed_ips": existing_peer.allowed_ips
            },
            config_file=config
        )

    # Generate new peer
    try:
        # Generate keys
        private_key, public_key = WireGuardManager.generate_keypair()
        preshared_key = WireGuardManager.generate_preshared_key()

        # Get available IP
        assigned_ip = WireGuardManager.get_next_available_ip(db)

        # Add peer
        peer = WireGuardManager.add_peer(
            db=db,
            user=current_user,
            public_key=public_key,
            private_key=private_key,
            assigned_ip=assigned_ip,
            preshared_key=preshared_key
        )

        # Generate client config
        server_endpoint = request.base_url.hostname or "vpn.example.com"
        config = WireGuardManager.generate_client_config(peer, server_endpoint)

        # Audit log
        audit = AuditLog(
            user_id=current_user.id,
            action="vpn_provision",
            resource_type="peer",
            resource_id=str(peer.id),
            ip_address=request.client.host,
            status="success"
        )
        db.add(audit)
        db.commit()

        logger.info(f"VPN provisioned for user: {current_user.username}")

        return VPNConfigResponse(
            interface={
                "private_key": private_key,
                "address": assigned_ip,
                "dns": settings.wg_dns
            },
            peer={
                "public_key": WireGuardManager.get_server_public_key(),
                "endpoint": f"{server_endpoint}:{settings.wg_port}",
                "allowed_ips": peer.allowed_ips
            },
            config_file=config
        )

    except Exception as e:
        logger.error(f"Failed to provision VPN: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to provision VPN: {str(e)}"
        )


@app.get("/api/v1/vpn/status", response_model=VPNStatusResponse)
async def get_vpn_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get VPN connection status."""
    stats = WireGuardManager.get_peer_stats(db, current_user)

    if not stats:
        return VPNStatusResponse(connected=False)

    return VPNStatusResponse(
        connected=stats["is_active"],
        assigned_ip=stats["assigned_ip"],
        last_handshake=stats["last_handshake"],
        transfer_rx=stats["transfer_rx"],
        transfer_tx=stats["transfer_tx"]
    )


@app.delete("/api/v1/vpn/disconnect", response_model=MessageResponse)
async def disconnect_vpn(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disconnect from VPN and revoke access."""
    peer = db.query(Peer).filter(
        Peer.user_id == current_user.id,
        Peer.is_active == True
    ).first()

    if not peer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active VPN connection found"
        )

    try:
        WireGuardManager.remove_peer(db, peer)

        # Audit log
        audit = AuditLog(
            user_id=current_user.id,
            action="vpn_disconnect",
            resource_type="peer",
            resource_id=str(peer.id),
            ip_address=request.client.host,
            status="success"
        )
        db.add(audit)
        db.commit()

        logger.info(f"VPN disconnected for user: {current_user.username}")

        return MessageResponse(message="Disconnected from VPN successfully")

    except Exception as e:
        logger.error(f"Failed to disconnect VPN: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect VPN: {str(e)}"
        )


# ============================================================================
# Admin Endpoints
# ============================================================================

@app.get("/api/v1/admin/users", response_model=UserListResponse)
async def list_users(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """List all users (admin only)."""
    users = db.query(User).all()
    return UserListResponse(
        total=len(users),
        users=[UserResponse.model_validate(user) for user in users]
    )


@app.delete("/api/v1/admin/users/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Cannot delete yourself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    # Remove all peers
    peers = db.query(Peer).filter(Peer.user_id == user_id, Peer.is_active == True).all()
    for peer in peers:
        WireGuardManager.remove_peer(db, peer)

    # Delete user
    db.delete(user)
    db.commit()

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="user_delete",
        resource_type="user",
        resource_id=str(user_id),
        ip_address=request.client.host,
        status="success"
    )
    db.add(audit)
    db.commit()

    logger.info(f"User deleted: {user.username}")

    return MessageResponse(message=f"User {user.username} deleted successfully")


@app.get("/api/v1/admin/peers", response_model=PeerListResponse)
async def list_peers(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """List all active peers (admin only)."""
    peers = db.query(Peer).filter(Peer.is_active == True).all()

    peer_responses = []
    for peer in peers:
        user = db.query(User).filter(User.id == peer.user_id).first()
        peer_response = PeerResponse.model_validate(peer)
        peer_response.username = user.username if user else None
        peer_responses.append(peer_response)

    return PeerListResponse(
        total=len(peer_responses),
        peers=peer_responses
    )


@app.get("/api/v1/admin/status", response_model=ServerStatusResponse)
async def server_status(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get server status (admin only)."""
    active_peers = db.query(Peer).filter(Peer.is_active == True).count()
    total_users = db.query(User).count()

    try:
        wg_status = WireGuardManager.get_interface_status()
        status = "running"
    except Exception:
        status = "error"

    return ServerStatusResponse(
        status=status,
        wireguard_interface=settings.wg_interface,
        active_peers=active_peers,
        total_users=total_users
    )


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status": "error"
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
