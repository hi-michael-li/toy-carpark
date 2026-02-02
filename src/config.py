from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "CarPark API"
    debug: bool = False
    environment: str = "production"

    # Database
    database_url: str = "sqlite+aiosqlite:///./carpark.db"

    # Security
    secret_key: str = "change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    # Parking Settings
    default_grace_period_minutes: int = 15
    max_reservation_days_ahead: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
