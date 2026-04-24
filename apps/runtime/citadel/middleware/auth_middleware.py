"""
Authentication middleware for FastAPI.

Routes:
  - POST /auth/login → JWT token
  - POST /auth/refresh → New JWT
  - POST /auth/logout → Revoke JWT
  - POST /auth/keys → Create API key
  - GET /auth/keys → List API keys
"""

from fastapi import Request, HTTPException, Depends, FastAPI, Body
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging
from urllib.parse import parse_qs

from citadel.auth.jwt_token import JWTService, JWTError
from citadel.auth.api_key import APIKeyService, APIKeyError
from citadel.auth.operator import OperatorService

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authenticate requests using JWT (dashboard) or API key (SDK).
    
    Determines which auth method to use based on endpoint:
      - Dashboard endpoints: Require JWT in Authorization header
      - SDK endpoints: Require API key in X-API-Key header
    """
    
    # Endpoints that don't require auth
    EXEMPT_PATHS = {
        "/health",
        "/healthz",
        "/v1/health",
        "/v1/health/live",
        "/v1/health/ready",
        "/docs",
        "/openapi.json",
        "/auth/login",      # Login endpoint
        "/auth/refresh",    # Token refresh
        "/redoc",
        "/v1/billing/webhooks", # Stripe webhooks
    }
    
    # Endpoints that require API key
    SDK_PATHS = {
        "/api/actions",
        "/api/approvals",
        "/api/policies",
        "/v1", # including /v1 routes that are meant for SDK
    }
    
    # Endpoints that require JWT
    DASHBOARD_PATHS = {
        "/dashboard",
        "/api/dashboard",
        "/auth/logout",
        "/auth/keys",
    }
    
    def __init__(self, app, jwt_service: JWTService):
        super().__init__(app)
        self.jwt_service = jwt_service
    
    async def dispatch(self, request: Request, call_next):
        # Exempt paths (health, docs, login)
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)
        
        # SDK endpoints require API key
        if any(request.url.path.startswith(path) for path in self.SDK_PATHS):
            return await self._auth_api_key(request, call_next)
        
        # Dashboard endpoints require JWT
        if any(request.url.path.startswith(path) for path in self.DASHBOARD_PATHS):
            return await self._auth_jwt(request, call_next)
        
        # Default: allow (could be stricter)
        return await call_next(request)
    
    async def _auth_api_key(self, request: Request, call_next):
        """Authenticate SDK request using API key"""
        api_key_id = request.headers.get("X-API-Key")
        api_key_secret = request.headers.get("X-API-Secret")
        
        if not api_key_id or not api_key_secret:
            logger.warning(f"Missing API key credentials: {request.url.path}")
            return JSONResponse(
                status_code=401,
                content={"error": "Missing X-API-Key and X-API-Secret headers"}
            )
        
        try:
            db_pool = request.app.state.db_pool
            cache = getattr(request.app.state, "cache", None)
            api_key_service = APIKeyService(db_pool, cache)
            api_key = await api_key_service.verify(api_key_id, api_key_secret)
            
            # Store in request state for downstream use
            request.state.api_key = api_key
            request.state.tenant_id = api_key.tenant_id
            
            return await call_next(request)
            
        except APIKeyError as e:
            logger.warning(f"API key verification failed: {e}")
            return JSONResponse(
                status_code=401,
                content={"error": str(e)}
            )
    
    async def _auth_jwt(self, request: Request, call_next):
        """Authenticate dashboard request using JWT"""
        auth_header = request.headers.get("Authorization")
        
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning(f"Missing JWT token: {request.url.path}")
            return JSONResponse(
                status_code=401,
                content={"error": "Missing Authorization header"}
            )
        
        token = auth_header[7:]  # Remove "Bearer "
        
        try:
            claims = self.jwt_service.verify_token(token)
            
            # Additional check: could check revocation cache here
            if getattr(request.app.state, "cache", None):
                is_revoked = await request.app.state.cache.get(f"revoked_token:{claims.jti}")
                if is_revoked:
                    return JSONResponse(
                        status_code=401,
                        content={"error": "Token has been revoked"}
                    )
            
            # Store in request state for downstream use
            request.state.user_id = claims.user_id
            request.state.tenant_id = claims.tenant_id
            request.state.role = claims.role.value
            request.state.claims = claims
            
            return await call_next(request)
            
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return JSONResponse(
                status_code=401,
                content={"error": str(e)}
            )

# API Endpoints mock dependencies
async def get_db(request: Request):
    return request.app.state.db_pool

async def get_cache(request: Request):
    return getattr(request.app.state, "cache", None)

def setup_auth_endpoints(app: FastAPI, jwt_service: JWTService):
    """Register authentication endpoints"""
    
    @app.post("/auth/login")
    async def login(
        request: Request,
        db = Depends(get_db),
    ):
        """
        Login endpoint - authenticate operator and return JWT tokens.
        """
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            payload = await request.json()
            username = payload.get("username")
            password = payload.get("password")
        else:
            form = parse_qs((await request.body()).decode("utf-8"))
            username = form.get("username", [None])[0]
            password = form.get("password", [None])[0]

        if not username or not password:
            raise HTTPException(status_code=400, detail="Username and password are required")

        operator_service = OperatorService(db)
        operator = await operator_service.authenticate(username, password)
        
        if not operator:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        access_token = jwt_service.create_token(
            user_id=operator.operator_id,
            tenant_id=operator.tenant_id,
            email=operator.email,
            role=operator.role,
            token_type="access"
        )
        
        refresh_token = jwt_service.create_token(
            user_id=operator.operator_id,
            tenant_id=operator.tenant_id,
            email=operator.email,
            role=operator.role,
            token_type="refresh"
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": 3600,
            "token_type": "Bearer"
        }
    
    @app.post("/auth/refresh")
    async def refresh(
        refresh_token: str = Body(...),
        cache = Depends(get_cache),
    ):
        """Refresh expired access token using refresh token"""
        try:
            access_token = jwt_service.refresh_token(refresh_token, cache)
            return {
                "access_token": access_token,
                "expires_in": 3600,
                "token_type": "Bearer"
            }
        except JWTError as e:
            return JSONResponse(status_code=401, content={"error": str(e)})
    
    @app.post("/auth/logout")
    async def logout(
        request: Request,
        cache = Depends(get_cache),
    ):
        """Logout — revoke JWT token"""
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            await jwt_service.revoke_token(token, cache)
        
        return {"success": True}
    
    @app.post("/auth/keys")
    async def create_api_key(
        request: Request,
        name: str = Body(...),
        db = Depends(get_db),
        cache = Depends(get_cache),
    ):
        """Create new API key (requires JWT auth)"""
        tenant_id = getattr(request.state, "tenant_id", "acme")
        
        service = APIKeyService(db, cache)
        response = await service.create(tenant_id, name, "live")
        
        return {
            "key_id": response.key_id,
            "key_secret": response.key_secret,
            "warning": "Save your key secret — it won't be shown again"
        }
    
    @app.get("/auth/keys")
    async def list_api_keys(
        request: Request,
        db = Depends(get_db),
        cache = Depends(get_cache),
    ):
        """List all API keys for tenant (requires JWT auth)"""
        tenant_id = getattr(request.state, "tenant_id", "acme")
        
        service = APIKeyService(db, cache)
        keys = await service.list_keys(tenant_id)
        
        return {
            "keys": [
                {
                    "key_id": key.key_id,
                    "name": key.name,
                    "created_at": key.created_at.isoformat(),
                    "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
                    "status": key.status.value,
                }
                for key in keys
            ]
        }
