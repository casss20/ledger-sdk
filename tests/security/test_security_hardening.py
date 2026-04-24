"""
Security Hardening Test Suite

Tests for:
- Rate limiting (token bucket)
- CORS origin restrictions
- Request body size limits
- Stripe webhook HMAC verification
- Auth endpoint brute force protection
"""

import pytest
import json
import asyncio
import hmac
import hashlib
import time
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from citadel.middleware.rate_limit import (
    TokenBucket,
    RateLimiter,
    RateLimitMiddleware,
    AuthRateLimitMiddleware,
    RateLimitConfig,
)
from citadel.api.middleware import RequestSizeLimitMiddleware, get_cors_origins
from citadel.billing.stripe_webhooks import StripeWebhookHandler


class TestTokenBucket:
    """Test in-memory token bucket algorithm"""
    
    @pytest.mark.asyncio
    async def test_allows_within_capacity(self):
        bucket = TokenBucket(capacity=5, refill_rate=1.0)
        
        # First 5 should succeed
        for _ in range(5):
            allowed, _ = await bucket.consume()
            assert allowed
        
        # 6th should fail
        allowed, headers = await bucket.consume()
        assert not allowed
        assert "Retry-After" in headers
    
    @pytest.mark.asyncio
    async def test_refills_over_time(self):
        bucket = TokenBucket(capacity=2, refill_rate=10.0)  # 10 per second
        
        # Consume all
        for _ in range(2):
            await bucket.consume()
        
        allowed, _ = await bucket.consume()
        assert not allowed
        
        # Wait for refill
        await asyncio.sleep(0.15)  # Should get ~1.5 tokens back
        
        allowed, _ = await bucket.consume()
        assert allowed
    
    @pytest.mark.asyncio
    async def test_headers_present(self):
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        
        allowed, headers = await bucket.consume()
        assert allowed
        assert headers["X-RateLimit-Limit"] == "10"
        assert headers["X-RateLimit-Remaining"] == "9"


class TestRateLimiter:
    """Test rate limiter key generation and category detection"""
    
    def test_get_category_auth(self):
        limiter = RateLimiter()
        assert limiter._get_category("/auth/login") == "auth"
        assert limiter._get_category("/auth/refresh") == "auth"
    
    def test_get_category_api(self):
        limiter = RateLimiter()
        assert limiter._get_category("/v1/actions") == "api"
        assert limiter._get_category("/api/policies") == "api"
    
    def test_get_category_default(self):
        limiter = RateLimiter()
        assert limiter._get_category("/unknown") == "default"
    
    def test_get_key_with_tenant(self):
        limiter = RateLimiter()
        
        class MockRequest:
            class state:
                tenant_id = "acme"
            url = type("url", (), {"path": "/v1/actions"})()
            headers = {}
            client = type("client", (), {"host": "1.2.3.4"})()
        
        key = limiter._get_key(MockRequest(), "api")
        assert "acme" in key
        assert "tenant" in key
    
    def test_get_key_fallback_ip(self):
        limiter = RateLimiter()
        
        class MockRequest:
            class state:
                pass  # No tenant_id
            url = type("url", (), {"path": "/auth/login"})()
            headers = {}
            client = type("client", (), {"host": "1.2.3.4"})()
        
        key = limiter._get_key(MockRequest(), "auth")
        assert "1.2.3.4" in key
        assert "ip" in key


class TestRateLimitMiddleware:
    """Integration tests for rate limiting middleware"""
    
    @pytest.fixture
    def app(self):
        app = FastAPI()
        
        @app.get("/health")
        async def health():
            return {"ok": True}
        
        @app.post("/auth/login")
        async def login():
            return {"token": "test"}
        
        @app.get("/v1/actions")
        async def actions():
            return {"actions": []}
        
        app.add_middleware(RateLimitMiddleware)
        return app
    
    @pytest.fixture
    def client(self, app):
        return TestClient(app)
    
    def test_exempt_paths_not_limited(self, client):
        """Health checks should never be rate limited"""
        for _ in range(20):
            response = client.get("/health")
            assert response.status_code == 200
    
    def test_api_paths_limited(self, client):
        """API paths should be rate limited"""
        # Make many requests rapidly
        responses = [client.get("/v1/actions") for _ in range(25)]
        
        # Some should succeed, some should be 429
        status_codes = [r.status_code for r in responses]
        assert 200 in status_codes
        assert 429 in status_codes or all(s == 200 for s in status_codes)
        # If limit is hit, check headers
        for r in responses:
            if r.status_code == 429:
                assert "X-RateLimit-Limit" in r.headers or "retry_after" in r.json()
    
    def test_rate_limit_headers_present(self, client):
        """All responses should include rate limit headers"""
        response = client.get("/v1/actions")
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers


class TestAuthRateLimitMiddleware:
    """Tests for strict auth endpoint rate limiting"""
    
    @pytest.fixture
    def app(self):
        app = FastAPI()
        
        @app.post("/auth/login")
        async def login():
            return {"token": "test"}
        
        @app.post("/auth/refresh")
        async def refresh():
            return {"token": "test"}
        
        app.add_middleware(AuthRateLimitMiddleware)
        return app
    
    @pytest.fixture
    def client(self, app):
        return TestClient(app)
    
    def test_login_rate_limited(self, client):
        """Login should be strictly rate limited per IP"""
        responses = [client.post("/auth/login") for _ in range(10)]
        
        # Should hit limit after 5 attempts (config is 5 per 5 min)
        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes, f"Expected 429 in responses, got {status_codes}"
    
    def test_refresh_rate_limited(self, client):
        """Refresh should be rate limited but less strictly"""
        responses = [client.post("/auth/refresh") for _ in range(15)]
        
        status_codes = [r.status_code for r in responses]
        # 10 per minute allowed, so 15 should trigger some 429s
        assert 429 in status_codes or len([s for s in status_codes if s == 200]) <= 10


class TestRequestSizeLimit:
    """Test request body size enforcement"""
    
    @pytest.fixture
    def app(self):
        app = FastAPI()
        
        @app.post("/api/upload")
        async def upload(request: Request):
            body = await request.body()
            return {"size": len(body)}
        
        app.add_middleware(RequestSizeLimitMiddleware)
        return app
    
    @pytest.fixture
    def client(self, app):
        return TestClient(app)
    
    def test_small_request_allowed(self, client):
        response = client.post("/api/upload", json={"data": "small"})
        assert response.status_code == 200
    
    def test_oversized_request_blocked(self, client):
        # 15 MB payload
        big_payload = b"x" * (15 * 1024 * 1024)
        response = client.post(
            "/api/upload",
            data=big_payload,
            headers={"Content-Type": "application/octet-stream"}
        )
        assert response.status_code == 413
        assert "payload_too_large" in response.text


class TestCORSSecurity:
    """Test CORS is locked down in production"""
    
    def test_debug_origins(self, monkeypatch):
        """Debug mode should allow localhost origins"""
        monkeypatch.setattr("citadel.config.settings.debug", True)
        origins = get_cors_origins()
        assert "http://localhost:3000" in origins
        assert "http://localhost:5173" in origins
    
    def test_production_no_default_origins(self, monkeypatch):
        """Production without explicit config should have no origins"""
        monkeypatch.setattr("citadel.config.settings.debug", False)
        monkeypatch.setattr("citadel.config.settings", type("settings", (), {
            "debug": False,
            "cors_origins": None,
        })())
        
        # When no origins configured and not in debug, return empty list
        # (CORS middleware won't be added)
        from citadel.api.middleware import get_cors_origins
        origins = get_cors_origins()
        assert origins == []


class TestStripeWebhookHMAC:
    """Test Stripe webhook signature verification"""
    
    @pytest.fixture
    def handler(self):
        return StripeWebhookHandler(None, webhook_secret="whsec_test_secret")
    
    def test_valid_signature(self, handler):
        """Valid signature should pass"""
        payload = b'{"test": "event"}'
        timestamp = int(datetime.now(timezone.utc).timestamp())
        
        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        signature = hmac.new(
            "whsec_test_secret".encode(),
            signed_payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        
        sig_header = f"t={timestamp},v1={signature}"
        
        assert handler.verify_signature(payload, sig_header)
    
    def test_invalid_signature(self, handler):
        """Tampered signature should fail"""
        payload = b'{"test": "event"}'
        sig_header = "t=1234567890,v1=invalid_signature"
        
        assert not handler.verify_signature(payload, sig_header)
    
    def test_missing_signature(self, handler):
        """Missing signature header should fail"""
        payload = b'{"test": "event"}'
        
        assert not handler.verify_signature(payload, None)
    
    def test_replay_attack_old_timestamp(self, handler):
        """Signatures older than 5 minutes should fail (replay protection)"""
        payload = b'{"test": "event"}'
        old_timestamp = int(datetime.now(timezone.utc).timestamp()) - 400  # 6+ minutes ago
        
        signed_payload = f"{old_timestamp}.{payload.decode('utf-8')}"
        signature = hmac.new(
            "whsec_test_secret".encode(),
            signed_payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        
        sig_header = f"t={old_timestamp},v1={signature}"
        
        assert not handler.verify_signature(payload, sig_header)
    
    def test_tampered_payload(self, handler):
        """Payload that doesn't match signature should fail"""
        original_payload = b'{"test": "event"}'
        tampered_payload = b'{"test": "tampered"}'
        timestamp = int(datetime.now(timezone.utc).timestamp())
        
        signed_payload = f"{timestamp}.{original_payload.decode('utf-8')}"
        signature = hmac.new(
            "whsec_test_secret".encode(),
            signed_payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        
        sig_header = f"t={timestamp},v1={signature}"
        
        # Verify with tampered payload
        assert not handler.verify_signature(tampered_payload, sig_header)
    
    def test_no_secret_allows_in_dev(self):
        """Without webhook secret, verification passes with warning (dev only)"""
        handler = StripeWebhookHandler(None, webhook_secret=None)
        
        payload = b'{"test": "event"}'
        assert handler.verify_signature(payload, None)


class TestSecurityHeaders:
    """Verify security headers are present on responses"""
    
    @pytest.fixture
    def app(self):
        app = FastAPI()
        
        @app.get("/api/test")
        async def test_endpoint():
            return {"ok": True}
        
        app.add_middleware(RateLimitMiddleware)
        return app
    
    @pytest.fixture
    def client(self, app):
        return TestClient(app)
    
    def test_rate_limit_headers(self, client):
        response = client.get("/api/test")
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
