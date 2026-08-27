import os
import secrets
import warnings
from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from functools import lru_cache

# Minimum length for any secret provided in production (review R2, card f3231394)
MIN_SECRET_LENGTH = 32


class Settings(BaseSettings):
    """Application settings with environment-based configuration.

    Security: All sensitive values MUST be provided via environment variables.
    Defaults are ONLY for local development and will trigger warnings.
    """

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Database - REQUIRED in production
    database_url: Optional[str] = os.getenv("DATABASE_URL")

    # Redis
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_password: Optional[SecretStr] = os.getenv("REDIS_PASSWORD")

    # JWT - REQUIRED in production
    secret_key: Optional[SecretStr] = os.getenv("JWT_SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # QA Framework Integration
    qa_framework_api_url: str = os.getenv("QA_FRAMEWORK_API_URL", "http://localhost:8001")

    # Frontend
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # Stripe - REQUIRED for billing
    STRIPE_API_KEY: Optional[SecretStr] = os.getenv("STRIPE_API_KEY")
    STRIPE_WEBHOOK_SECRET: Optional[SecretStr] = os.getenv("STRIPE_WEBHOOK_SECRET")

    # Stripe Price IDs - from environment only (public by design, but no
    # committed defaults: hygiene follow-up of review R2, card f3231394)
    STRIPE_PRICE_FREE: Optional[str] = os.getenv("STRIPE_PRICE_FREE")
    STRIPE_PRICE_PRO: Optional[str] = os.getenv("STRIPE_PRICE_PRO")
    STRIPE_PRICE_ENTERPRISE: Optional[str] = os.getenv("STRIPE_PRICE_ENTERPRISE")

    # Stripe Product IDs (LIVE)
    STRIPE_PRODUCT_FREE: str = os.getenv("STRIPE_PRODUCT_FREE", "prod_UDMMUYX064DjtC")
    STRIPE_PRODUCT_PRO: str = os.getenv("STRIPE_PRODUCT_PRO", "prod_UDMMlPYySnUofh")
    STRIPE_PRODUCT_ENTERPRISE: str = os.getenv("STRIPE_PRODUCT_ENTERPRISE", "prod_UDMM2Yuc2VJAK3")

    # Feature Flags
    ENABLE_BILLING: bool = os.getenv("ENABLE_BILLING", "false").lower() == "true"

    # Browser-Use AI-Powered Test Automation
    BROWSER_USE_LLM_PROVIDER: str = os.getenv("BROWSER_USE_LLM_PROVIDER", "groq")
    BROWSER_USE_MODEL: str = os.getenv("BROWSER_USE_MODEL", "llama-3.3-70b-versatile")
    GROQ_API_KEY: Optional[SecretStr] = os.getenv("GROQ_API_KEY")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def _normalize_environment(cls, value):
        """Normalize case/whitespace variants so " Production " cannot skip
        the production fail-closed validation."""
        if isinstance(value, str):
            return value.strip().lower()
        return value

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._validate_production_config()
        self._warn_insecure_defaults()

    def _validate_production_config(self):
        """Validate that all required variables are set in production."""
        if self.ENVIRONMENT == "production":
            required_vars = {
                "DATABASE_URL": self.database_url,
                "JWT_SECRET_KEY": self.secret_key,
            }

            if self.ENABLE_BILLING:
                required_vars.update(
                    {
                        "STRIPE_API_KEY": self.STRIPE_API_KEY,
                        "STRIPE_WEBHOOK_SECRET": self.STRIPE_WEBHOOK_SECRET,
                        "STRIPE_PRICE_FREE": self.STRIPE_PRICE_FREE,
                        "STRIPE_PRICE_PRO": self.STRIPE_PRICE_PRO,
                        "STRIPE_PRICE_ENTERPRISE": self.STRIPE_PRICE_ENTERPRISE,
                    }
                )

            def _plain(v):
                return v.get_secret_value() if isinstance(v, SecretStr) else v

            missing = [
                k
                for k, v in required_vars.items()
                # SecretStr is always truthy; inspect the underlying value.
                if _plain(v) is None or not _plain(v)
            ]
            if missing:
                raise ValueError(
                    f"Missing required environment variables in production: {', '.join(missing)}. "
                    "Set these variables before starting the application."
                )

            self._validate_secret_strength(_plain)

    def _validate_secret_strength(self, _plain):
        """Reject weak (<32 chars) secrets in production (review R2, card f3231394).

        Only applied when the secret is present; absence is handled by the
        required-vars check above.
        """
        if self.ENVIRONMENT != "production":
            return
        secret_vars = {
            "JWT_SECRET_KEY": self.secret_key,
            "REDIS_PASSWORD": self.redis_password,
            "STRIPE_API_KEY": self.STRIPE_API_KEY,
            "STRIPE_WEBHOOK_SECRET": self.STRIPE_WEBHOOK_SECRET,
            "GROQ_API_KEY": self.GROQ_API_KEY,
        }
        too_short = [
            k
            for k, v in secret_vars.items()
            if v is not None and len(_plain(v)) < MIN_SECRET_LENGTH
        ]
        if too_short:
            raise ValueError(
                f"Weak secrets in production (min {MIN_SECRET_LENGTH} chars): "
                f"{', '.join(too_short)}. Generate high-entropy values "
                "(e.g. openssl rand -base64 48) and set them via environment."
            )

    def _warn_insecure_defaults(self):
        """Warn when using insecure default values."""
        if self.ENVIRONMENT != "production":
            warning_messages = []

            if not self.database_url:
                warning_messages.append(
                    "DATABASE_URL not set - using in-memory SQLite (not suitable for production)"
                )

            if not self.secret_key:
                # Dev-only fallback: a per-process random secret. Nothing is
                # committed, so tokens signed in dev are unguessable but do
                # not survive a restart. Production never reaches this path
                # (_validate_production_config crashes first).
                object.__setattr__(self, "secret_key", SecretStr(secrets.token_urlsafe(48)))
                warning_messages.append(
                    "JWT_SECRET_KEY not set - using ephemeral dev fallback (sessions will not persist across restarts)"
                )

            if self.ENABLE_BILLING and not self.STRIPE_API_KEY:
                warning_messages.append(
                    "Billing enabled but STRIPE_API_KEY not set - billing will fail"
                )

            for warning in warning_messages:
                warnings.warn(warning, UserWarning)

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "development"

    @property
    def async_database_url(self) -> str:
        """Get database URL formatted for async drivers (asyncpg)."""
        if not self.database_url:
            return "sqlite+aiosqlite:///./qafw.db"

        # Convert postgresql:// to postgresql+asyncpg:// for async support
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Backward compatibility - will be deprecated
settings = get_settings()
