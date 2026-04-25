"""
Tests for Agent Identity Trust system.

Run: pytest tests/test_agent_identity.py -v
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from citadel.agent_identity.identity import AgentIdentity, AgentCredentials, IdentityManager
from citadel.agent_identity.trust_score import TrustScorer, TrustLevel, TrustScore
from citadel.agent_identity.auth import AgentAuthService


class MockDBPool:
    """Mock asyncpg pool for testing."""
    
    def __init__(self, data=None):
        self.data = data or {}
        self.conn = MagicMock()
        self.conn.fetchrow = AsyncMock()
        self.conn.fetch = AsyncMock()
        self.conn.execute = AsyncMock()
        self.conn.fetchval = AsyncMock(return_value=0)
    
    def acquire(self):
        return self.conn
    
    async def __aenter__(self):
        return self.conn
    
    async def __aexit__(self, *args):
        pass


class TestAgentIdentity:
    """Test core identity data structures."""
    
    def test_agent_identity_creation(self):
        identity = AgentIdentity(
            agent_id="test-agent-1",
            tenant_id="dev_tenant",
            public_key="pk_test",
            secret_key_hash="hmac$sha256$100000$salt$hash",
        )
        assert identity.agent_id == "test-agent-1"
        assert identity.tenant_id == "dev_tenant"
        assert identity.verification_status == "pending"
        assert identity.trust_level == "unverified"
    
    def test_agent_identity_to_dict(self):
        identity = AgentIdentity(
            agent_id="test-agent-1",
            tenant_id="dev_tenant",
            public_key="pk_test",
            secret_key_hash="hash",
        )
        d = identity.to_dict()
        assert d["agent_id"] == "test-agent-1"
        assert "public_key" in d
        assert "secret_key_hash" not in d  # Should not expose hash
    
    def test_agent_credentials_creation(self):
        creds = AgentCredentials(
            agent_id="test-agent",
            secret_key="sk_test_secret",
            public_key="pk_test",
            api_key="ak_test123",
        )
        assert creds.agent_id == "test-agent"
        assert creds.api_key == "ak_test123"
        assert "public_key" in creds.to_dict()
    
    def test_trust_level_enum(self):
        assert TrustLevel.REVOKED.value == "revoked"
        assert TrustLevel.UNVERIFIED.value == "unverified"
        assert TrustLevel.STANDARD.value == "standard"
        assert TrustLevel.TRUSTED.value == "trusted"
        assert TrustLevel.HIGHLY_TRUSTED.value == "highly_trusted"


class TestTrustScorer:
    """Test trust score calculation."""
    
    @pytest.fixture
    def mock_db(self):
        pool = MockDBPool()
        pool.conn.__aenter__ = AsyncMock(return_value=pool.conn)
        pool.conn.__aexit__ = AsyncMock(return_value=False)
        return pool
    
    @pytest.mark.asyncio
    async def test_missing_identity(self, mock_db):
        mock_db.conn.fetchrow.return_value = None
        scorer = TrustScorer(mock_db)
        score = await scorer.calculate_score("missing-agent")
        assert score.score == 0.0
        assert score.level == TrustLevel.REVOKED
    
    @pytest.mark.asyncio
    async def test_verified_identity(self, mock_db):
        mock_db.conn.fetchrow.side_effect = [
            {
                "agent_id": "test-agent",
                "verification_status": "verified",
                "created_at": datetime.utcnow() - timedelta(days=30),
            },
            {
                "agent_id": "test-agent",
                "actions_today": 50,
                "health_score": 100,
                "quarantined": False,
                "token_spend": 1000,
                "token_budget": 100000,
            },
        ]
        scorer = TrustScorer(mock_db)
        score = await scorer.calculate_score("test-agent")
        assert score.score > 0.5
        assert score.level in [TrustLevel.STANDARD, TrustLevel.TRUSTED, TrustLevel.HIGHLY_TRUSTED]
    
    @pytest.mark.asyncio
    async def test_quarantined_agent(self, mock_db):
        mock_db.conn.fetchrow.side_effect = [
            {
                "agent_id": "test-agent",
                "verification_status": "verified",
                "created_at": datetime.utcnow() - timedelta(days=30),
            },
            {
                "agent_id": "test-agent",
                "actions_today": 50,
                "health_score": 100,
                "quarantined": True,
                "token_spend": 1000,
                "token_budget": 100000,
            },
        ]
        scorer = TrustScorer(mock_db)
        score = await scorer.calculate_score("test-agent")
        # Quarantine gives -0.30 but other factors still positive
        assert score.score < 0.7  # Significantly lower than non-quarantined
        assert score.level in [TrustLevel.UNVERIFIED, TrustLevel.STANDARD]  # Lowered level
    
    @pytest.mark.asyncio
    async def test_new_unverified_agent(self, mock_db):
        mock_db.conn.fetchrow.side_effect = [
            {
                "agent_id": "test-agent",
                "verification_status": "pending",
                "created_at": datetime.utcnow(),
            },
            None,  # No agent row yet
        ]
        scorer = TrustScorer(mock_db)
        score = await scorer.calculate_score("test-agent")
        assert 0.0 <= score.score <= 1.0
        assert score.level == TrustLevel.UNVERIFIED


class TestIdentityManager:
    """Test cryptographic functions."""
    
    @pytest.fixture
    def mock_db(self):
        pool = MockDBPool()
        pool.conn.__aenter__ = AsyncMock(return_value=pool.conn)
        pool.conn.__aexit__ = AsyncMock(return_value=False)
        return pool
    
    def test_keypair_generation(self, mock_db):
        manager = IdentityManager(mock_db)
        public_key, secret_key = manager._generate_keypair()
        assert public_key is not None
        assert secret_key is not None
        assert public_key != secret_key
        assert len(public_key) > 20
    
    def test_secret_hashing(self, mock_db):
        manager = IdentityManager(mock_db)
        secret = "test-secret-123"
        hashed = manager._hash_secret(secret)
        assert hashed != secret
        assert manager._verify_secret(secret, hashed) is True
        assert manager._verify_secret("wrong-secret", hashed) is False
    
    def test_api_key_generation(self, mock_db):
        manager = IdentityManager(mock_db)
        api_key = manager._generate_api_key("agent-1", "dev_tenant")
        assert api_key.startswith("ak_")
        assert len(api_key) > 10
    
    @pytest.mark.asyncio
    async def test_register_agent(self, mock_db):
        manager = IdentityManager(mock_db)
        mock_db.conn.execute.return_value = None
        
        result = await manager.register_agent("test-agent", "dev_tenant", "Test Agent", "op-1")
        
        assert result.agent_id == "test-agent"
        assert result.api_key.startswith("ak_")
        assert len(result.secret_key) > 0
        assert len(result.public_key) > 0


class TestAgentAuthService:
    """Test agent authentication service."""
    
    @pytest.fixture
    def mock_db(self):
        pool = MockDBPool()
        pool.conn.__aenter__ = AsyncMock(return_value=pool.conn)
        pool.conn.__aexit__ = AsyncMock(return_value=False)
        return pool
    
    @pytest.fixture
    def auth_service(self, mock_db):
        return AgentAuthService(mock_db)
    
    @pytest.mark.asyncio
    async def test_register_agent(self, auth_service, mock_db):
        mock_db.conn.execute.return_value = None
        
        result = await auth_service.register(
            agent_id="test-agent",
            tenant_id="dev_tenant",
            name="Test Agent",
            owner="op-1",
        )
        
        assert result["agent_id"] == "test-agent"
        assert result["api_key"].startswith("ak_")
        assert len(result["secret_key"]) > 0
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self, auth_service, mock_db):
        secret = "test-secret"
        secret_hash = auth_service.identity_manager._hash_secret(secret)
        
        mock_db.conn.fetchrow.return_value = {
            "agent_id": "test-agent",
            "tenant_id": "dev_tenant",
            "public_key": "pk_test",
            "secret_key_hash": secret_hash,
            "trust_level": "unverified",
            "verification_status": "pending",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        result = await auth_service.authenticate(
            agent_id="test-agent",
            secret_key=secret,
        )
        
        assert result is not None
        assert result["agent_id"] == "test-agent"
    
    @pytest.mark.asyncio
    async def test_authenticate_wrong_secret(self, auth_service, mock_db):
        mock_db.conn.fetchrow.return_value = {
            "agent_id": "test-agent",
            "secret_key_hash": auth_service.identity_manager._hash_secret("correct-secret"),
        }
        
        result = await auth_service.authenticate(
            agent_id="test-agent",
            secret_key="wrong-secret",
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_generate_challenge(self, auth_service, mock_db):
        mock_db.conn.execute.return_value = None
        
        result = await auth_service.generate_challenge("test-agent")
        
        assert "challenge" in result
        assert "expires_in" in result
        assert result["expires_in"] == 300
    
    @pytest.mark.asyncio
    async def test_verify_request_signature_timestamp(self, auth_service, mock_db):
        mock_db.conn.fetchrow.return_value = {
            "agent_id": "test-agent",
            "tenant_id": "dev_tenant",
            "public_key": "pk_test",
            "secret_key_hash": "hash",
            "trust_level": "unverified",
            "verification_status": "pending",
            "created_at": datetime.utcnow() - timedelta(days=1),
            "last_verified_at": None,
        }
        
        # Old timestamp should fail
        old_ts = str(int((datetime.utcnow() - timedelta(minutes=10)).timestamp()))
        result = await auth_service.verify_request_signature(
            agent_id="test-agent",
            signature="aGVsbG8=",  # base64 "hello"
            timestamp=old_ts,
            method="GET",
            path="/test",
        )
        assert result is False
        
        # Recent timestamp should pass basic check
        recent_ts = str(int(datetime.utcnow().timestamp()))
        long_sig = "a" * 64  # base64-like string, decoded length ~48 >= 32
        result = await auth_service.verify_request_signature(
            agent_id="test-agent",
            signature=long_sig,
            timestamp=recent_ts,
            method="GET",
            path="/test",
        )
        assert result is True  # Basic format check passes


class TestOWASPMiddleware:
    """Test OWASP security middleware controls."""
    
    def test_security_headers_present(self):
        from citadel.security.owasp_middleware import SecurityHeadersMiddleware
        
        middleware = SecurityHeadersMiddleware(None)
        csp = middleware._default_csp()
        assert "default-src" in csp
        assert "frame-ancestors 'none'" in csp
    
    def test_input_validation_patterns(self):
        from citadel.security.owasp_middleware import InputValidationMiddleware
        
        # Create instance for instance methods
        middleware = InputValidationMiddleware(None)
        
        # SQL injection pattern
        result = middleware._check_patterns(
            "SELECT * FROM users",
            InputValidationMiddleware.SQL_INJECTION_PATTERNS,
            "sql"
        )
        assert result == "sql"
        
        # Safe input
        result = middleware._check_patterns(
            "Hello World",
            InputValidationMiddleware.SQL_INJECTION_PATTERNS,
            "sql"
        )
        assert result is None
    
    def test_ssrf_url_validation(self):
        from citadel.security.owasp_middleware import SSRFProtectionMiddleware
        
        middleware = SSRFProtectionMiddleware(None)
        
        # Blocked URLs
        assert middleware._validate_url("http://localhost:8080") is False
        assert middleware._validate_url("http://127.0.0.1/admin") is False
        
        # Allowed URLs
        assert middleware._validate_url("https://api.example.com") is True


class TestSREInfrastructure:
    """Test SRE components — import directly to avoid __init__ deps."""
    
    def test_health_check_result(self):
        from citadel.sre.health_checks import HealthCheckResult, HealthStatus
        
        result = HealthCheckResult(
            name="test",
            status=HealthStatus.HEALTHY,
            message="All good",
            response_time_ms=10.0,
        )
        
        assert result.status == HealthStatus.HEALTHY
        assert result.to_dict()["status"] == "healthy"
    
    def test_slo_definition(self):
        from citadel.sre.slos import SLODefinition
        
        slo = SLODefinition(
            name="availability",
            description="System availability",
            target=0.999,
            window="30d",
            metric="availability_ratio",
            unit="percent",
            alert_threshold=0.995,
        )
        
        assert slo.name == "availability"
        assert slo.target == 0.999
    
    def test_alert_manager_creation(self):
        from citadel.sre.alerting import AlertManager, AlertSeverity, ConsoleChannel
        
        console = ConsoleChannel()
        manager = AlertManager(channels=[console])
        
        assert manager is not None
        assert AlertSeverity.WARNING.value == "warning"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
