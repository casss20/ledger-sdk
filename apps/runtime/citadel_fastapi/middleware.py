"""
Citadel FastAPI Middleware — Security, auth, rate limiting, audit logging.

Fixed: JWT secret loaded from environment, no hardcoded defaults in production.
"""

import os
import time
import uuid
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import Request, Response, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware

from citadel.governance.rate_limit import RateLimiter, RateLimitExceeded
from citadel.governance.audit import AuditService


# ============================================================================
# JWT HANDLING (FIXED — env-driven)
# ============================================================================

class JWTConfig:
    """JWT configuration loaded from environment."""
    
    SECRET: Optional[str] = None
    ALGORITHM: str = "HS256"
    EXPIRY_HOURS: int = 24
    
    @classmethod
    def load(cls):
        """Load configuration from environment."""
        cls.SECRET = os.getenv("JWT_SECRET")
        env = os.getenv("ENV", "development")
        
        if env == "production" and not cls.SECRET:
            raise RuntimeError("JWT_SECRET must be set in production")
        
        # Dev fallback (insecure, logs warning)
        if not cls.SECRET:
            import warnings
            warnings.warn("JWT_SECRET not set — using insecure dev fallback!")
            cls.SECRET = "dev-" + os.urandom(16).hex()


class TokenPayload:
    """JWT token payload."""
    def __init__(
        self,
        sub: str,
        role: str,
        iat: datetime,
        exp: datetime,
        jti: str,
        business_id: Optional[int] = None
    ):
        self.sub = sub
        self.role = role
        self.iat = iat
        self.exp = exp
        self.jti = jti
        self.business_id = business_id


class JWTHandler:
    """JWT token creation and validation."""
    
    @staticmethod
    def create_token(subject: str, role: str, business_id: Optional[int] = None) -> str:
        """Create a new JWT token."""
        try:
            import jwt
        except ImportError:
            raise ImportError("Install PyJWT: pip install PyJWT")
        
        JWTConfig.load()
        now = datetime.utcnow()
        expiry = now + timedelta(hours=JWTConfig.EXPIRY_HOURS)
        
        payload = {
            "sub": subject,
            "role": role,
            "business_id": business_id,
            "iat": now,
            "exp": expiry,
            "jti": str(uuid.uuid4())
        }
        
        return jwt.encode(payload, JWTConfig.SECRET, algorithm=JWTConfig.ALGORITHM)
    
    @staticmethod
    def validate_token(token: str) -> TokenPayload:
        """Validate and decode JWT token."""
        try:
            import jwt
        except ImportError:
            raise ImportError("Install PyJWT: pip install PyJWT")
        
        JWTConfig.load()
        
        try:
            payload = jwt.decode(
                token, JWTConfig.SECRET, algorithms=[JWTConfig.ALGORITHM]
            )
            return TokenPayload(
                sub=payload["sub"],
                role=payload["role"],
                iat=payload["iat"],
                exp=payload["exp"],
                jti=payload["jti"],
                business_id=payload.get("business_id")
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(401, "Token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(401, "Invalid token")


# ============================================================================
# MIDDLEWARE
# ============================================================================

security_scheme = HTTPBearer(auto_error=False)


class LedgerMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for Citadel governance.
    
    Handles:
    - Request ID generation
    - Rate limiting
    - JWT authentication
    - Audit logging
    """
    
    PUBLIC_PATHS = [
        ("GET", "/health"),
        ("GET", "/health/live"),
        ("POST", "/auth/login"),
    ]
    
    def __init__(
        self,
        app,
        rate_limiter: RateLimiter,
        audit: Optional[AuditService] = None,
    ):
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.audit = audit
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Get client info
        client_ip = request.client.host if request.client else "unknown"
        
        # Check if public route
        is_public = self._is_public_route(request.method, request.url.path)
        
        # Rate limiting
        tier = self._get_tier(request)
        allowed, remaining = await self.rate_limiter.check(client_ip, tier)
        
        if not allowed:
            if self.audit:
                await self.audit.log(
                    actor=client_ip,
                    action="rate_limit_exceeded",
                    resource=request.url.path,
                    risk="medium",
                    approved=False,
                    payload={"tier": tier}
                )
            
            retry_after = await self.rate_limiter.get_retry_after(client_ip)
            return Response(
                content=json.dumps({"detail": "Rate limit exceeded"}),
                status_code=429,
                headers={
                    "Content-Type": "application/json",
                    "Retry-After": str(retry_after),
                    "X-Request-ID": request_id
                }
            )
        
        # Authentication (skip for public routes)
        user = None
        if not is_public:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "")
                try:
                    user = JWTHandler.validate_token(token)
                    request.state.user = user
                except HTTPException:
                    return self._error_response(401, "Invalid authentication", request_id)
            else:
                return self._error_response(401, "Authentication required", request_id)
        
        # Process request
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Log to audit
            if self.audit and user:
                await self.audit.log(
                    actor=user.sub,
                    action=f"{request.method}_{request.url.path}",
                    resource=request.url.path,
                    risk="low",
                    approved=True,
                    payload={
                        "duration_ms": (time.time() - start_time) * 1000,
                        "status_code": response.status_code
                    }
                )
            
            # Add headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            
            return response
            
        except Exception as e:
            if self.audit and user:
                await self.audit.log(
                    actor=user.sub,
                    action=f"{request.method}_{request.url.path}",
                    resource=request.url.path,
                    risk="high",
                    approved=False,
                    payload={"error": str(e)}
                )
            raise
    
    def _is_public_route(self, method: str, path: str) -> bool:
        """Check if route is public (no auth required)."""
        for public_method, public_path in self.PUBLIC_PATHS:
            if method == public_method and path == public_path:
                return True
        return False
    
    def _get_tier(self, request: Request) -> str:
        """Determine rate limit tier based on path."""
        path = request.url.path
        
        if any(x in path for x in ["/admin", "/killswitch"]):
            return "sensitive"
        if request.headers.get("Authorization"):
            return "standard"
        return "public"
    
    def _error_response(self, status: int, detail: str, request_id: str) -> Response:
        """Create error response."""
        return Response(
            content=json.dumps({"detail": detail}),
            status_code=status,
            headers={"Content-Type": "application/json", "X-Request-ID": request_id}
        )


# ============================================================================
# DEPENDENCIES
# ============================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme)
) -> TokenPayload:
    """FastAPI dependency to get current authenticated user."""
    if not credentials:
        raise HTTPException(401, "Authentication required")
    return JWTHandler.validate_token(credentials.credentials)


__all__ = [
    "LedgerMiddleware",
    "JWTHandler",
    "JWTConfig",
    "TokenPayload",
    "get_current_user",
    "security_scheme"
]
