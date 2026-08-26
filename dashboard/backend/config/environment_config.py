"""
Multi-Environment Configuration for QA-Framework
Support for dev, staging, and production environments
"""

import os
from typing import Optional, Dict, Any
from enum import Enum
from pathlib import Path
from pydantic import BaseSettings, Field, validator


class Environment(str, Enum):
    """Supported environments."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class EnvironmentConfig(BaseSettings):
    """
    Multi-environment configuration with validation.

    Configuration hierarchy (highest to lowest priority):
    1. Environment variables
    2. Environment-specific .env file
    3. Default .env file
    4. Hardcoded defaults
    """

    # Environment
    ENVIRONMENT: Environment = Field(
        default=Environment.DEVELOPMENT, description="Current environment"
    )

    # Application
    APP_NAME: str = Field(default="QA-Framework", description="Application name")
    APP_VERSION: str = Field(default="1.0.0", description="Application version")
    DEBUG: bool = Field(default=False, description="Debug mode")

    # Security — REQUIRED, no committed fallback (incident 112853a6, CWE-798).
    # Instantiation fails unless the value comes from the environment/.env.
    SECRET_KEY: str = Field(
        ...,
        description="Secret key for signing (required: env or .env file only)",
        min_length=32,
    )
    JWT_SECRET_KEY: str = Field(
        ...,
        description="JWT signing key (required: env or .env file only)",
        min_length=32,
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    JWT_EXPIRE_MINUTES: int = Field(default=30, description="JWT expiration in minutes")

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://localhost:5432/qa_framework_dev",
        description="Database connection URL",
    )
    DATABASE_POOL_SIZE: int = Field(default=5, description="Database pool size")
    DATABASE_POOL_MAX_OVERFLOW: int = Field(default=10, description="Database max overflow")

    # Redis
    REDIS_HOST: str = Field(default="localhost", description="Redis host")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    REDIS_DB: int = Field(default=0, description="Redis database")
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis password")

    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="json", description="Logging format (json|text)")
    LOG_FILE: Optional[str] = Field(default=None, description="Log file path")

    # API
    API_PREFIX: str = Field(default="/api/v1", description="API prefix")
    API_DOCS_ENABLED: bool = Field(default=True, description="Enable API docs")
    CORS_ORIGINS: list = Field(
        default=["http://localhost:3000"], description="CORS allowed origins"
    )

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    RATE_LIMIT_DEFAULT: int = Field(default=100, description="Default rate limit")

    # Cache
    CACHE_ENABLED: bool = Field(default=True, description="Enable caching")
    CACHE_TTL: int = Field(default=300, description="Default cache TTL in seconds")

    # Feature Flags
    FEATURE_NEW_DASHBOARD: bool = Field(default=False, description="Enable new dashboard")
    FEATURE_ADVANCED_REPORTING: bool = Field(default=False, description="Enable advanced reporting")
    FEATURE_AI_INSIGHTS: bool = Field(default=False, description="Enable AI insights")

    # External Services
    SENTRY_DSN: Optional[str] = Field(default=None, description="Sentry DSN")
    PROMETHEUS_ENABLED: bool = Field(default=False, description="Enable Prometheus metrics")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()

    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == Environment.DEVELOPMENT

    def is_staging(self) -> bool:
        """Check if running in staging environment."""
        return self.ENVIRONMENT == Environment.STAGING

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == Environment.PRODUCTION

    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.ENVIRONMENT == Environment.TESTING

    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration."""
        return {
            "url": self.DATABASE_URL,
            "pool_size": self.DATABASE_POOL_SIZE,
            "max_overflow": self.DATABASE_POOL_MAX_OVERFLOW,
            "echo": self.DEBUG,  # Enable SQL logging in debug mode
        }

    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration."""
        config = {
            "host": self.REDIS_HOST,
            "port": self.REDIS_PORT,
            "db": self.REDIS_DB,
            "decode_responses": True,
        }
        if self.REDIS_PASSWORD:
            config["password"] = self.REDIS_PASSWORD
        return config

    def get_feature_flags(self) -> Dict[str, bool]:
        """Get all feature flags."""
        return {
            "new_dashboard": self.FEATURE_NEW_DASHBOARD,
            "advanced_reporting": self.FEATURE_ADVANCED_REPORTING,
            "ai_insights": self.FEATURE_AI_INSIGHTS,
        }

    def validate_production_security(self) -> list:
        """
        Validate security settings for production.

        Returns:
            List of security warnings
        """
        warnings = []

        if self.is_production():
            if self.DEBUG:
                warnings.append("DEBUG mode is enabled in production!")

            if "dev-" in self.SECRET_KEY:
                warnings.append("Development-looking SECRET_KEY in production!")

            if "dev-" in self.JWT_SECRET_KEY:
                warnings.append("Development-looking JWT_SECRET_KEY in production!")

        return warnings


# Environment-specific configuration loaders
def load_environment_config(env: Optional[Environment] = None) -> EnvironmentConfig:
    """
    Load environment-specific configuration.

    Args:
        env: Environment to load (auto-detected if None)

    Returns:
        EnvironmentConfig instance
    """
    # Auto-detect environment
    if env is None:
        env_str = os.getenv("ENVIRONMENT", "development").lower()
        try:
            env = Environment(env_str)
        except ValueError:
            env = Environment.DEVELOPMENT

    # Set environment variable for config loading
    os.environ["ENVIRONMENT"] = env.value

    # Load environment-specific .env file
    env_file = Path(f".env.{env.value}")
    if env_file.exists():
        config = EnvironmentConfig(env_file=str(env_file))
    else:
        # Fall back to default .env
        config = EnvironmentConfig()

    # Validate production security
    if env == Environment.PRODUCTION:
        warnings = config.validate_production_security()
        if warnings:
            import logging

            logger = logging.getLogger(__name__)
            for warning in warnings:
                logger.warning(f"SECURITY WARNING: {warning}")

    return config


# Global configuration instance
_config: Optional[EnvironmentConfig] = None


def get_config() -> EnvironmentConfig:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = load_environment_config()
    return _config


def reload_config() -> EnvironmentConfig:
    """Reload configuration from environment."""
    global _config
    _config = load_environment_config()
    return _config
