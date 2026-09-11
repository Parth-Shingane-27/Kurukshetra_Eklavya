from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "asbo"

    gemini_api_key: str | None = None
    # "gemini-2.0-flash" (the previous default) has since been retired upstream (404 as of
    # this writing); "gemini-flash-latest" is a rolling alias rather than a dated snapshot,
    # so it shouldn't need updating again as models are retired.
    gemini_model: str = "gemini-flash-latest"

    admin_credential: str = "change-me-admin-token"

    seed_schemes_on_startup: bool = True

    # RAG layer (Section: Shared Policy Knowledge Service)
    chroma_persist_dir: str = "./data/chroma"
    embedding_model: str = "gemini-embedding-001"
    rag_top_k: int = 5
    policy_corpus_path: str = "../gov_schemes_cleaned.json"
    bm25_index_path: str = "./data/bm25_index.pkl"

    # Comma-separated list — the frontend dev server (5173) and its production preview (4173)
    # by default. A real hosted deployment (Section 24) would set this to its actual origin.
    cors_origins: str = "http://localhost:5173,http://localhost:4173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
