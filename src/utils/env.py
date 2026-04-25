from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


@lru_cache(maxsize=1)
def load_project_dotenv() -> Path:
    """Load the repository .env file once and return its path."""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(env_path, override=False)
    return env_path
