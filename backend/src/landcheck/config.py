"""Settings from environment variables (prefix LANDCHECK_) or the repo-root .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LANDCHECK_",
        env_file=REPO_ROOT / ".env",
        extra="ignore",
    )

    # Comma-separated list of origins allowed to call the API from a browser.
    cors_origins: str = "http://localhost:5173"
    # Folder with one mock result file per risk (used until real modules exist).
    mocks_dir: Path = REPO_ROOT / "contracts" / "mocks"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
