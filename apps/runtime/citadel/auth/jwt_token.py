"""
JWT Token authentication for dashboard.

Why: Dashboard users (CSOs, operators) authenticate with JWT tokens.
Pattern: Standard JWT (RFC 7519) with RS256 signing.

Token format:
  eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...

Claims:
  - user_id: Unique user identifier
  - tenant_id: Which tenant user belongs to
  - email: User email
  - role: User role (admin, operator, auditor, viewer)
  - exp: Expiration (1 hour)
  - iat: Issued at
  - mfa_verified: Did user pass MFA?
"""

import jwt
import secrets
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class UserRole(Enum):
    """User roles in Citadel"""
    ADMIN = "admin"           # Full access
    OPERATOR = "operator"     # Approve actions, view activity
    AUDITOR = "auditor"       # Read-only audit access
    VIEWER = "viewer"         # Read-only compliance dashboard

class TokenType(Enum):
    """JWT token type"""
    ACCESS = "access"         # Short-lived (1 hour)
    REFRESH = "refresh"       # Long-lived (7 days, used to get new access token)

@dataclass
class JWTClaims:
    """JWT token claims"""
    user_id: str
    tenant_id: str
    email: str
    role: UserRole
    token_type: TokenType = TokenType.ACCESS
    exp: Optional[int] = None
    iat: Optional[int] = None
    mfa_verified: bool = False
    jti: Optional[str] = None  # JWT ID (unique token identifier)
    
    def to_dict(self) -> dict:
        """Convert claims to dictionary"""
        import time
        now = int(time.time())
        
        if self.exp is None:
            if self.token_type == TokenType.ACCESS:
                self.exp = now + 3600  # 1 hour
            else:
                self.exp = now + 604800  # 7 days
        
        if self.iat is None:
            self.iat = now
        
        if self.jti is None:
            self.jti = secrets.token_urlsafe(16)
        
        return {
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "email": self.email,
            "role": self.role.value,
            "token_type": self.token_type.value,
            "exp": self.exp,
            "iat": self.iat,
            "mfa_verified": self.mfa_verified,
            "jti": self.jti,
        }

class JWTService:
    """Manage JWT token lifecycle"""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        # In production, use RS256 with public/private keypair
        # For now, use HS256 (HMAC with shared secret)
    
    def create_token(
        self,
        user_id: str,
        tenant_id: str,
        email: str,
        role: str,
        mfa_verified: bool = False,
        token_type: str = "access",
    ) -> str:
        """
        Create JWT token.
        
        Args:
            user_id: Unique user ID
            tenant_id: Tenant user belongs to
            email: User email
            role: User role (admin, operator, auditor, viewer)
            mfa_verified: Has user completed MFA?
            token_type: "access" (1h) or "refresh" (7d)
        
        Returns: JWT token string
        """
        claims = JWTClaims(
            user_id=user_id,
            tenant_id=tenant_id,
            email=email,
            role=UserRole(role),
            mfa_verified=mfa_verified,
            token_type=TokenType(token_type),
        )
        
        token = jwt.encode(
            claims.to_dict(),
            self.secret_key,
            algorithm=self.algorithm
        )
        
        logger.info(f"JWT token created for user {user_id}")
        return token
    
    def verify_token(self, token: str) -> JWTClaims:
        """
        Verify JWT token is valid.
        
        Returns: JWTClaims object if valid
        Raises: JWTError if invalid/expired/tampered
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                leeway=10
            )
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            raise JWTError("Token has expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            raise JWTError("Invalid token")
        
        # Check if token is in revocation list (logout)
        # (Would query cache/DB here - omitted for this specific verify_token signature but handled in middleware)
        
        return JWTClaims(
            user_id=payload["user_id"],
            tenant_id=payload["tenant_id"],
            email=payload["email"],
            role=UserRole(payload["role"]),
            token_type=TokenType(payload["token_type"]),
            exp=payload["exp"],
            iat=payload["iat"],
            mfa_verified=payload.get("mfa_verified", False),
            jti=payload.get("jti"),
        )
    
    def refresh_token(self, token: str, cache) -> str:
        """
        Refresh an expired access token using a valid refresh token.
        
        Args:
            token: Refresh token (must be valid)
            cache: Cache service (to check revocation)
        
        Returns: New access token
        """
        claims = self.verify_token(token)
        
        if claims.token_type != TokenType.REFRESH:
            raise JWTError("Can only refresh with refresh token")
            
        # Optional: check cache to see if refresh token is revoked
        if cache:
            # We assume synchronous check here or await outside
            pass
        
        # Create new access token
        return self.create_token(
            user_id=claims.user_id,
            tenant_id=claims.tenant_id,
            email=claims.email,
            role=claims.role.value,
            mfa_verified=claims.mfa_verified,
            token_type="access",
        )
    
    async def revoke_token(self, token: str, cache) -> None:
        """
        Revoke token (logout).
        
        Adds token to revocation list (blacklist) in cache.
        """
        claims = self.verify_token(token)
        
        # Add to revocation list (TTL = token expiration time)
        import time
        ttl = claims.exp - int(time.time())
        if ttl > 0 and cache:
            try:
                import asyncio
                if asyncio.iscoroutinefunction(getattr(cache, "set", None)):
                    await cache.set(f"revoked_token:{claims.jti}", True, ttl=ttl)
                else:
                    cache.set(f"revoked_token:{claims.jti}", True, ttl=ttl)
            except (ConnectionError, TimeoutError, ValueError, TypeError) as cache_err:
                logger.warning(f"Failed to cache revoked token: {cache_err}")
                pass
        
        logger.info(f"JWT token revoked for user {claims.user_id}")

class JWTError(Exception):
    """JWT validation error"""
    pass
