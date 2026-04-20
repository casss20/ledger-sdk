"""
Ledger Configuration

Production settings via Pydantic Settings with .env file support.
"""

from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Ledger application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # App
    app_name: str = "ledger-governance"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # Database
    database_url: str = "postgresql://ledger:ledger@localhost:5432/ledger_test"
    db_min_size: int = 2
    db_max_size: int = 10
    
    # API Security
    api_key_header: str = "X-API-Key"
    api_keys: str = "dev-key-for-testing"  # Comma-separated list of valid keys
    require_auth: bool = True
    
    # Rate Limiting
    rate_limit_requests: int = 100  # per window
    rate_limit_window_seconds: int = 60
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # json or text
    
    # Metrics
    metrics_enabled: bool = True
    metrics_endpoint: str = "/metrics"
    
    @property
    def valid_api_keys(self) -> List[str]:
        if not self.api_keys:
            return []
        return [k.strip() for k in self.api_keys.split(",") if k.strip()]
    
    @property
    def database_dsn(self) -> str:
        return self.database_url


# Singleton
settings = Settings()
