"""Runtime configuration, loaded from environment variables.

All settings are prefixed with ``RQS_`` (Revenue Quality Service), e.g.
``RQS_API_KEY``. Values can also live in a local ``.env`` file (never commit it).
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RQS_", env_file=".env", extra="ignore")

    # --- Security -----------------------------------------------------------
    # The API key required on every /analyse call. The default is intentionally
    # an obvious placeholder so that an unconfigured deployment is easy to spot.
    api_key: str = "dev-local-key-change-me"
    api_key_header: str = "X-API-Key"

    # --- Domain -------------------------------------------------------------
    currency: str = "SAR"

    # --- Upload guardrails --------------------------------------------------
    max_upload_bytes: int = 10 * 1024 * 1024  # 10 MB hard cap on the CSV

    # --- CORS ---------------------------------------------------------------
    # Comma-separated list of origins allowed to call the API from a browser.
    # Defaults to the Vite dev server. Set RQS_CORS_ALLOW_ORIGINS in production.
    cors_allow_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached singleton so the env is read once per process."""
    return Settings()
