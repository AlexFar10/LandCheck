"""Settings from environment variables or the repo-root .env file (PRD Section 11.5)."""

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
# Labelled sample data, served until the pilot dataset (LC-15) exists.
SAMPLE_DATASET_DIR = Path(__file__).resolve().parent / "fixtures" / "sample"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LANDCHECK_",
        env_file=REPO_ROOT / ".env",
        extra="ignore",
    )

    # HTTP port. PORT has no LANDCHECK_ prefix because the platform (Coolify) sets it.
    port: int = Field(default=3000, validation_alias=AliasChoices("PORT"))
    # Dataset folder in the PRD Section 7.4 layout. Unset means the bundled sample fixture.
    # Target once LC-15 lands: datasets/pilot-pechea/v1
    dataset_dir: Path | None = None
    # Comma-separated browser origins allowed to call the API. Empty in production, where the
    # web app is served from the same origin. Local dev uses the Vite proxy, so no CORS either.
    cors_origins: str = ""

    @property
    def resolved_dataset_dir(self) -> Path:
        return self.dataset_dir if self.dataset_dir is not None else SAMPLE_DATASET_DIR

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
