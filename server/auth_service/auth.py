"""Authentication and JWT token management."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import uuid
import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .config import settings
from .models import User, Token
from .database import get_db
import logging

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token security
security = HTTPBearer()


class AuthService:
    """Authentication service for managing users and tokens."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash.

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password

        Returns:
            True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(
        user_id: int,
        username: str,
        is_admin: bool = False,
        expires_delta: Optional[timedelta] = None
    ) -> tuple[str, str, datetime]:
        """Create JWT access token.

        Args:
            user_id: User ID
            username: Username
            is_admin: Whether user is admin
            expires_delta: Token expiration time

        Returns:
            Tuple of (token, jti, expiration_datetime)
        """
        if expires_delta is None:
            expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

        expire = datetime.utcnow() + expires_delta
        jti = str(uuid.uuid4())

        to_encode = {
            "sub": str(user_id),
            "username": username,
            "is_admin": is_admin,
            "type": "access",
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": jti
        }

        encoded_jwt = jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )

        return encoded_jwt, jti, expire

    @staticmethod
    def create_refresh_token(
        user_id: int,
        username: str,
        expires_delta: Optional[timedelta] = None
    ) -> tuple[str, str, datetime]:
        """Create JWT refresh token.

        Args:
            user_id: User ID
            username: Username
            expires_delta: Token expiration time

        Returns:
            Tuple of (token, jti, expiration_datetime)
        """
        if expires_delta is None:
            expires_delta = timedelta(days=settings.refresh_token_expire_days)

        expire = datetime.utcnow() + expires_delta
        jti = str(uuid.uuid4())

        to_encode = {
            "sub": str(user_id),
            "username": username,
            "type": "refresh",
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": jti
        }

        encoded_jwt = jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )

        return encoded_jwt, jti, expire

    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """Decode and verify JWT token.

        Args:
            token: JWT token

        Returns:
            Decoded token payload

        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.PyJWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )

    @staticmethod
    def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
        """Authenticate a user by username and password.

        Args:
            db: Database session
            username: Username
            password: Plain text password

        Returns:
            User object if authentication successful, None otherwise
        """
        user = db.query(User).filter(User.username == username).first()

        if not user:
            return None

        if not AuthService.verify_password(password, user.hashed_password):
            return None

        if not user.is_active:
            return None

        return user

    @staticmethod
    def save_token(
        db: Session,
        user_id: int,
        token_type: str,
        jti: str,
        expires_at: datetime,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Token:
        """Save token to database.

        Args:
            db: Database session
            user_id: User ID
            token_type: Token type ('access' or 'refresh')
            jti: JWT ID
            expires_at: Expiration datetime
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Token object
        """
        token = Token(
            user_id=user_id,
            token_type=token_type,
            jti=jti,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(token)
        db.commit()
        db.refresh(token)
        return token

    @staticmethod
    def revoke_token(db: Session, jti: str) -> bool:
        """Revoke a token.

        Args:
            db: Database session
            jti: JWT ID

        Returns:
            True if token was revoked, False if not found
        """
        token = db.query(Token).filter(Token.jti == jti).first()
        if token:
            token.is_revoked = True
            token.revoked_at = datetime.utcnow()
            db.commit()
            return True
        return False

    @staticmethod
    def is_token_revoked(db: Session, jti: str) -> bool:
        """Check if a token is revoked.

        Args:
            db: Database session
            jti: JWT ID

        Returns:
            True if token is revoked, False otherwise
        """
        token = db.query(Token).filter(Token.jti == jti).first()
        if token:
            return token.is_revoked
        return False


# Dependency for getting current user from token
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current user from bearer token.

    Args:
        credentials: HTTP authorization credentials
        db: Database session

    Returns:
        Current user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    # Decode token
    payload = AuthService.decode_token(token)

    # Check token type
    if payload.get("type") != "access":
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

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )

    return user


# Dependency for requiring admin user
async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current admin user.

    Args:
        current_user: Current user from token

    Returns:
        Current user if admin

    Raises:
        HTTPException: If user is not admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user
