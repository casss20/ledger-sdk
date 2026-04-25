"""
Citadel Configuration

Production settings via Pydantic Settings with .env file support.
"""

from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Citadel application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # App
    app_name: str = "Citadel-governance"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # CORS Origins (comma-separated)
    cors_origins: str = "https://dashboard-lemon-one-20.vercel.app,https://citadelsdk.com,https://dashboard.citadelsdk.com"
    
    @property
    def allowed_cors_origins(self) -> List[str]:
        if not self.cors_origins:
            return []
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
    
    # Database
    database_url: str = "postgresql://Citadel:Citadel@localhost:5432/citadel_test"
    db_min_size: int = 2
    db_max_size: int = 10
    
    # API Security
    api_key_header: str = "X-API-Key"
    api_keys: str = "dev-key-for-testing"  # Comma-separated list of valid keys
    require_auth: bool = True
    cors_origins: str = (
        "https://citadelsdk.com,"
        "https://www.citadelsdk.com,"
        "https://dashboard.citadelsdk.com,"
        "https://*.vercel.app"
    )
    
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
    
    @property
    def valid_api_keys(self) -> List[str]:
        if not self.api_keys:
            return []
        return [k.strip() for k in self.api_keys.split(",") if k.strip()]

    @property
    def allowed_cors_origins(self) -> List[str]:
        if self.debug:
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    @property
    def database_dsn(self) -> str:
        return self.database_url


# Singleton
settings = Settings()
