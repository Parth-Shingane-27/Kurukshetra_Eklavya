from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "asbo"

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"

    admin_credential: str = "change-me-admin-token"

    seed_schemes_on_startup: bool = True

    # Comma-separated list — the frontend dev server (5173) and its production preview (4173)
    # by default. A real hosted deployment (Section 24) would set this to its actual origin.
    cors_origins: str = "http://localhost:5173,http://localhost:4173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
