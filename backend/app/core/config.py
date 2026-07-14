from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    """
    Central application configuration.
    """

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application metadata
    app_name: str = Field(..., min_length=1)
    app_version: str = Field(default="1.0.0")
    environment: Literal["development", "testing", "staging", "production"] = Field(
        default="development"
    )

    # Database
    database_url: str = Field(..., min_length=1)

    # Security
    secret_key: str = Field(..., min_length=16)
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30, ge=1)
    refresh_token_expire_days: int = Field(default=7, ge=1)

    # Cache
    redis_url: str = Field(default="redis://localhost:6379")

    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"
    )

    # Amadeus
    amadeus_api_key: str = Field(default="")
    amadeus_api_secret: str = Field(default="")
    amadeus_base_url: str = Field(default="https://test.api.amadeus.com")
    amadeus_timeout_seconds: float = Field(default=10.0)

    # AI
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-3.5-turbo")

    @field_validator("environment", mode="before")
    @classmethod
    def validate_environment(cls, value):
        if value is None:
            return "development"

        return str(value).strip().lower()

    @property
    def cors_origins_list(self):
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
