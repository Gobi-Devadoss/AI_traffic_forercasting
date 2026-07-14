"""
Central application configuration.
Reads values from environment variables (or a .env file) with sane defaults
so the project runs out of the box for evaluation/demo purposes.
"""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    APP_NAME: str = "AI Traffic & Mobility Forecasting Platform"
    ENV: str = "development"

    # Database - defaults to a local SQLite file so the project runs with zero setup.
    # Swap to a PostgreSQL URL (e.g. postgresql://user:pass@host:5432/dbname) for production.
    DATABASE_URL: str = Field(default="sqlite:///./traffic_forecast.db")

    # JWT / auth
    SECRET_KEY: str = Field(default="CHANGE_THIS_SECRET_KEY_IN_PRODUCTION_1234567890")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12  # 12 hours

    # First admin bootstrap (created automatically on first startup if no admin exists)
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_EMAIL: str = "admin@traffic-ai.local"
    DEFAULT_ADMIN_PASSWORD: str = "Admin@12345"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"


settings = Settings()
