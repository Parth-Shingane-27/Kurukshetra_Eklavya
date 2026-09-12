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

    # Email+password auth
    jwt_secret: str = "change-me-jwt-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Context-Aware Form Assistance (browser extension / mobile toggle)
    assistance_session_expire_seconds: int = 900
    """How long the opaque session_id (minted when a citizen clicks "Apply Now") stays
    exchangeable for an assistance_token — covers "citizen clicks Apply, extension loads,
    validates" without staying valid indefinitely."""
    assistance_token_expire_seconds: int = 1800
    """How long the exchanged assistance_token itself is usable for explain-text calls —
    longer than the session_id's window since the citizen may spend real time on the form."""
    assistance_screenshot_max_bytes: int = 3_000_000
    """Rejects an oversized screenshot crop before it's ever decoded/sent to the LLM (Section
    8's "screenshot size limits") — 3MB comfortably covers a cropped form region without
    allowing a full, arbitrarily large page capture through."""

    document_upload_max_bytes: int = 8_000_000
    """Rejects an oversized document upload before it's ever decoded/stored — 8MB comfortably
    covers a scanned document/photo of a physical document without allowing arbitrarily large
    uploads. No verification/parsing is performed on uploaded content — see
    app/modules/document_uploads (citizen-declared documents are stored as-is for the citizen's
    own reference and to auto-mark that document type as held)."""

    # Form Guide — YouTube tutorial recommendation (Section 17)
    youtube_api_key: str | None = None
    """Server-side only — never sent to the frontend. Video recommendation degrades to
    "unavailable" (Form Guide itself is unaffected) when unset, matching this app's existing
    BR-010-style pattern for every other optional external-service integration."""
    youtube_video_cache_ttl_days: int = 30
    """How long a found (or explicitly not-found) video recommendation is trusted before
    re-querying YouTube — avoids re-searching on every Form Guide open."""

    # Live web search (Tavily) — feeds the existing RAG-refresh and new scheme-discovery
    # curator-review pipelines with real internet results instead of only the static local
    # corpus. Blank disables both (they fall back to corpus-only behavior), matching this app's
    # existing BR-010-style degrade pattern for every other optional external-service integration.
    tavily_api_key: str | None = None

    seed_schemes_on_startup: bool = True

    # RAG layer (Section: Shared Policy Knowledge Service)
    chroma_persist_dir: str = "./data/chroma"
    embedding_model: str = "gemini-embedding-001"
    rag_top_k: int = 5
    policy_corpus_path: str = "../gov_schemes_cleaned.json"
    bm25_index_path: str = "./data/bm25_index.pkl"

    # Scheme catalog deadline lookup (public, citizen-independent) — how long a scheme's
    # cached deadline text is trusted before re-running retrieval, matching the
    # youtube_video_cache_ttl_days precedent above. Shorter than the video TTL since
    # application deadlines change more often than which tutorial video is best.
    scheme_deadline_cache_ttl_days: int = 14

    # Citizen-facing personalized live web scheme search (app/modules/web_scheme_search) — how
    # long a citizen's search results are trusted before a dashboard load triggers a fresh
    # Tavily+Gemini search for them. Shorter than the deadline-lookup TTL since this is a full
    # search, not a single lookup, and the "Refresh" button lets a citizen bypass it anytime.
    web_scheme_cache_ttl_hours: int = 24

    # Comma-separated list — the frontend dev server (5173) and its production preview (4173)
    # by default. A real hosted deployment (Section 24) would set this to its actual origin.
    cors_origins: str = "http://localhost:5173,http://localhost:4173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
