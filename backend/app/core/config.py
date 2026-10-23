"""Configuration de l'application, chargée depuis l'environnement (.env)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

NotificationProviderName = Literal["console", "whatsapp_cloud", "twilio"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Général ---
    ENVIRONMENT: Literal["dev", "test", "prod"] = "dev"
    DEBUG: bool = False
    DEFAULT_TIMEZONE: str = "Africa/Casablanca"
    DEFAULT_PHONE_REGION: str = "MA"

    # --- Base de données ---
    # Postgres en docker-compose ; SQLite permet de lancer l'API sans Docker.
    DATABASE_URL: str = "sqlite+aiosqlite:///./gestion_arbitres.db"

    # --- Redis / file de jobs ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Auth ---
    JWT_SECRET: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_TTL_MINUTES: int = 15
    REFRESH_TOKEN_TTL_DAYS: int = 7
    INVITE_TOKEN_TTL_HOURS: int = 72
    REFRESH_COOKIE_NAME: str = "refresh_token"
    COOKIE_SECURE: bool = False  # True derrière HTTPS en production
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"

    # --- Frontend / CORS ---
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # --- Notifications ---
    NOTIFICATION_PROVIDER: NotificationProviderName = "console"
    NOTIFICATION_MAX_ATTEMPTS: int = 3
    WHATSAPP_API_BASE_URL: str = "https://graph.facebook.com/v21.0"
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_APP_SECRET: str = ""
    WHATSAPP_VERIFY_TOKEN: str = ""

    # --- Amorçage (scripts/seed.py) ---
    FIRST_ADMIN_EMAIL: str = "admin@example.com"
    FIRST_ADMIN_PASSWORD: str = "ChangeMe!2026"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
