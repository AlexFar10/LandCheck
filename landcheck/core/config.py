"""Thresholds live in config/thresholds.yaml (versioned), not in module code."""
from functools import lru_cache
from pathlib import Path

import yaml

CONFIG = Path(__file__).resolve().parents[2] / "config" / "thresholds.yaml"


@lru_cache
def thresholds() -> dict:
    return yaml.safe_load(CONFIG.read_text())
