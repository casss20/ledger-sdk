"""
Citadel Configuration

Production settings via Pydantic Settings with .env file support.
Includes startup validation to prevent accidental insecure deployments.
"""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Citadel application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="CITADEL_",
        extra="ignore",
    )
    
    # App
    app_name: str = "Citadel-governance"
    app_version: str = "0.2.1"
    debug: bool = False
    
    # CORS Origins (comma-separated)
    # Must be set explicitly in production. Empty = no CORS origins allowed.
    cors_origins: str = ""
    
    @property
    def allowed_cors_origins(self) -> List[str]:
        if self.debug:
            # NEVER return wildcard with credentials — return localhost list only
            return [
                "http://localhost:3000",
                "http://localhost:5173",
                "http://localhost:8080",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173",
            ]
        if not self.cors_origins:
            return []
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
    
    # Database
    # SECURITY: No default credentials. Must be set via CITADEL_DATABASE_URL env var.
    # Example: postgresql://user:pass@localhost:5432/citadel
    database_url: str = ""
    db_min_size: int = 2
    db_max_size: int = 10
    
    # API Security
    api_key_header: str = "X-API-Key"
    # Format: "key:scope1,scope2|key2:scope1" or "key1,key2" for backward compat
    # SECURITY: Default empty — must be set in production. Dev scripts should export CITADEL_API_KEYS.
    api_keys: str = ""  # No default keys — startup validation will warn if empty in prod
    require_auth: bool = True
    # SECURITY: Default empty — must be set in production. Dev/testing will auto-generate a random one-time secret.
    citadel_jwt_secret: str = ""
    citadel_admin_bootstrap_username: str = "admin"
    citadel_admin_bootstrap_password: Optional[str] = None
    citadel_admin_bootstrap_tenant: str = "demo-tenant"
    citadel_admin_bootstrap_email: str = "admin@citadel.dev"
    citadel_admin_bootstrap_role: str = "admin"
    
    # Rate Limiting
    rate_limit_requests: int = 100  # per window
    rate_limit_window_seconds: int = 60
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # json or text
    
    # Metrics
    metrics_enabled: bool = True
    metrics_endpoint: str = "/metrics"
    
    # Billing (Stripe)
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    stripe_price_pro_id: Optional[str] = None
    app_url: str = "http://localhost:5173"
    
    # Agent Identity Trust Settings
    agent_identity_enabled: bool = True
    agent_auth_header: str = "X-Agent-Signature"
    agent_challenge_ttl_seconds: int = 300  # 5 minutes
    agent_max_failed_challenges: int = 5
    agent_trust_score_threshold: float = 0.40
    
    # OWASP Security Settings
    security_headers_enabled: bool = True
    hsts_max_age: int = 31536000  # 1 year
    hsts_include_subdomains: bool = True
    input_validation_enabled: bool = True
    ssrf_protection_enabled: bool = True
    error_sanitization_enabled: bool = True
    
    # SRE / Alerting Settings
    alerting_webhook_url: Optional[str] = None
    alerting_enabled: bool = False
    slo_enabled: bool = True
    health_check_timeout_seconds: float = 5.0
    
    # Compliance Settings
    compliance_mode: str = "standard"  # standard, strict, audit
    audit_retention_days: int = 90
    encryption_at_rest: bool = True
    
    @property
    def valid_api_keys(self) -> List[str]:
        """Backward compatibility: extract plaintext keys from api_keys string."""
        if not self.api_keys:
            return []
        result = []
        for segment in self.api_keys.split(","):
            segment = segment.strip()
            if not segment:
                continue
            if ":" in segment:
                key_part, _ = segment.split(":", 1)
                result.append(key_part.strip())
            else:
                result.append(segment)
        return result
    
    @property
    def database_dsn(self) -> str:
        return self.database_url
    
    def validate_secrets(self) -> List[str]:
        """
        Validate that secrets are not using default values in production.
        
        Returns list of error messages. Empty list = all good.
        Call this at startup and refuse to start if errors exist and debug=False.
        """
        # Skip validation in testing mode
        if os.environ.get("CITADEL_TESTING") == "true":
            return []
        
        errors = []
        if not self.citadel_jwt_secret:
            errors.append(
                "CRITICAL: citadel_jwt_secret is not set. "
                "Set a strong random secret via CITADEL_JWT_SECRET env var."
            )
        if not self.api_keys:
            errors.append(
                "CRITICAL: api_keys is not set. "
                "Set production keys via CITADEL_API_KEYS env var."
            )
        if self.citadel_admin_bootstrap_password is None:
            errors.append(
                "WARNING: citadel_admin_bootstrap_password is not set. "
                "The admin account will have a weak default password."
            )
        return errors


# Singleton
settings = Settings()
