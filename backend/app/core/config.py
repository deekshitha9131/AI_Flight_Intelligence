from typing import List
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "AI Flight Intelligence"
    APP_ENV: str = "development"
    SECRET_KEY: str = "your-secret-key-here"
    DATABASE_URL: str = "postgresql://user:password@localhost/dbname"
    LLM_API_KEY: str = "your-llm-api-key"
    LLM_MODEL: str = "gemini-3.6-flash"
    LLM_TIMEOUT: int = 30
    FLIGHT_API_KEY: str = "your-flight-api-key"
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DUFFEL_BASE_URL: str = "https://api.duffel.com/air"
    DUFFEL_TIMEOUT: int = 30

    class Config:
        env_file = Path(__file__).resolve().parents[2] / ".env"

settings = Settings()