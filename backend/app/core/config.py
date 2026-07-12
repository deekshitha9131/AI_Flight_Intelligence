from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration for the FastAPI backend.

    The settings object is loaded from the local .env file and validated using
    Pydantic so that configuration errors are surfaced early during startup.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application metadata
    app_name: str = Field(..., min_length=1, description="Application display name.")
    app_version: str = Field(default="1.0.0", min_length=1, description="Current API version.")
    environment: Literal["development", "testing", "staging", "production"] = Field(
        default="development",
        description="Runtime environment used to toggle behavior.",
    )

    # Database configuration
    database_url: str = Field(..., min_length=1, description="Primary database connection string.")

    # Security configuration
    secret_key: str = Field(..., min_length=16, description="Secret used for JWT signing and session protection.")
    jwt_algorithm: str = Field(default="HS256", min_length=1, description="JWT signing algorithm.")
    access_token_expire_minutes: int = Field(default=30, ge=1, description="JWT access token lifetime in minutes.")

    # Cache and queue configuration
    redis_url: str = Field(default="redis://localhost:6379", min_length=1, description="Redis connection string.")
    cors_origins: str = Field(default="http://localhost:3000", description="Comma-separated list of allowed origins.")

    # Third-party integrations
    amadeus_api_key: str = Field(default="", description="Amadeus API key.")
    amadeus_api_secret: str = Field(default="", description="Amadeus API secret.")

    @field_validator("environment", mode="before")
    @classmethod
    def validate_environment(cls, value: str | None) -> str:
        """Normalize the environment value to a lowercase supported value."""
        if value is None:
            return "development"
        return str(value).strip().lower()

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a parsed list for FastAPI middleware."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton settings instance for the application."""
    return Settings()


settings = get_settings()
