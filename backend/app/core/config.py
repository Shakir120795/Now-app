"""Application settings, loaded from environment (12-factor)."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "Luxe Commerce"
    env: str = "development"
    debug: bool = False
    secret_key: str = "change-me"
    api_v1_prefix: str = "/api/v1"

    # Auth
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    otp_ttl_seconds: int = 300
    otp_max_attempts: int = 5

    # Infra
    database_url: str = "postgresql+asyncpg://luxe:luxe@localhost:5432/luxe"
    redis_url: str = "redis://localhost:6379/0"

    # Payments
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None
    razorpay_webhook_secret: str | None = None
    phonepe_merchant_id: str | None = None
    phonepe_salt_key: str | None = None
    phonepe_salt_index: int = 1

    # Integrations
    google_maps_api_key: str | None = None
    fcm_credentials_json: str | None = None
    sms_provider: str = "msg91"
    msg91_auth_key: str | None = None

    # Storage
    s3_endpoint: str | None = None
    s3_bucket: str = "luxe-media"
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_region: str = "ap-south-1"

    # Locale
    default_currency: str = "INR"
    default_locale: str = "en"
    timezone: str = Field(default="Asia/Kolkata")

    @model_validator(mode="after")
    def _enforce_strong_secret(self) -> "Settings":
        # Refuse to boot outside development with a weak/default JWT secret.
        if self.env != "development":
            if self.secret_key in {"change-me", "change-me-in-prod"} or len(self.secret_key) < 32:
                raise ValueError(
                    "SECRET_KEY must be a strong random value of at least 32 characters "
                    "when ENV is not 'development'."
                )
        return self

    @property
    def sync_database_url(self) -> str:
        """Sync URL for Alembic (psycopg)."""
        return self.database_url.replace("+asyncpg", "+psycopg")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
