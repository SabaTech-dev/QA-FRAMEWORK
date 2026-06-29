import os
import warnings
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from functools import lru_cache


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
    redis_password: Optional[str] = os.getenv("REDIS_PASSWORD")

    # JWT - REQUIRED in production
    secret_key: Optional[str] = os.getenv("JWT_SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # QA Framework Integration
    qa_framework_api_url: str = os.getenv("QA_FRAMEWORK_API_URL", "http://localhost:8001")

    # Frontend
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # Stripe - REQUIRED for billing
    STRIPE_API_KEY: Optional[str] = os.getenv("STRIPE_API_KEY")
    STRIPE_WEBHOOK_SECRET: Optional[str] = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    # Stripe Price IDs (LIVE)
    STRIPE_PRICE_FREE: str = os.getenv("STRIPE_PRICE_FREE", "price_1TEvdOI1MtlKoNQt5aepkf0d")
    STRIPE_PRICE_PRO: str = os.getenv("STRIPE_PRICE_PRO", "price_1TEvdOI1MtlKoNQtonZGU7S7")
    STRIPE_PRICE_ENTERPRISE: str = os.getenv("STRIPE_PRICE_ENTERPRISE", "price_1TEvdPI1MtlKoNQtdRE8CP5m")
    
    # Stripe Product IDs (LIVE)
    STRIPE_PRODUCT_FREE: str = os.getenv("STRIPE_PRODUCT_FREE", "prod_UDMMUYX064DjtC")
    STRIPE_PRODUCT_PRO: str = os.getenv("STRIPE_PRODUCT_PRO", "prod_UDMMlPYySnUofh")
    STRIPE_PRODUCT_ENTERPRISE: str = os.getenv("STRIPE_PRODUCT_ENTERPRISE", "prod_UDMM2Yuc2VJAK3")

    # Feature Flags
    ENABLE_BILLING: bool = os.getenv("ENABLE_BILLING", "false").lower() == "true"
    
    # Browser-Use AI-Powered Test Automation
    BROWSER_USE_LLM_PROVIDER: str = os.getenv("BROWSER_USE_LLM_PROVIDER", "groq")
    BROWSER_USE_MODEL: str = os.getenv("BROWSER_USE_MODEL", "llama-3.3-70b-versatile")
    
    # Browser-Use AI-Powered Test Automation
    BROWSER_USE_LLM_PROVIDER: str = os.getenv("BROWSER_USE_LLM_PROVIDER", "groq")
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    BROWSER_USE_MODEL: str = os.getenv("BROWSER_USE_MODEL", "llama-3.3-70b-versatile")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
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
                required_vars.update({
                    "STRIPE_API_KEY": self.STRIPE_API_KEY,
                    "STRIPE_WEBHOOK_SECRET": self.STRIPE_WEBHOOK_SECRET,
                })
            
            missing = [k for k, v in required_vars.items() if not v]
            if missing:
                raise ValueError(
                    f"Missing required environment variables in production: {', '.join(missing)}. "
                    "Set these variables before starting the application."
                )
    
    def _warn_insecure_defaults(self):
        """Warn when using insecure default values."""
        if self.ENVIRONMENT != "production":
            warning_messages = []
            
            if not self.database_url:
                warning_messages.append("DATABASE_URL not set - using in-memory SQLite (not suitable for production)")
            
            if not self.secret_key:
                # Generate a development-only secret key for JWT
                secret_key_str = "dev-secret-key-not-for-production-use"
                object.__setattr__(self, 'secret_key', secret_key_str)
                warning_messages.append("JWT_SECRET_KEY not set - using dev fallback (sessions will not persist across restarts)")
            
            if self.ENABLE_BILLING and not self.STRIPE_API_KEY:
                warning_messages.append("Billing enabled but STRIPE_API_KEY not set - billing will fail")
            
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
