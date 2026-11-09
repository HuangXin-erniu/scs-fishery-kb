from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "configs" / "corpus.yaml"
DEFAULT_PIPELINE = REPO_ROOT / "configs" / "pipeline.yaml"
DEFAULT_LEXICON = REPO_ROOT / "configs" / "lexicon.yaml"


class ConfigError(RuntimeError):
    """Raised when the local configuration is missing or invalid."""


def load_dotenv(path: Path | None = None) -> None:
    """Load KEY=VALUE lines from .env without overriding the environment."""
    env_path = path or REPO_ROOT / ".env"
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _env_path(name: str) -> Path:
    load_dotenv()
    value = os.environ.get(name)
    if not value:
        raise ConfigError(f"{name} is not set")
    path = Path(value).expanduser().resolve()
    if not path.is_dir():
        raise ConfigError(f"{name} does not point to a directory: {path}")
    return path


def data_root() -> Path:
    return _env_path("SCS_FKB_DATA_ROOT")


def run_root() -> Path:
    return _env_path("SCS_FKB_RUN_ROOT")


def sensitivity_ceiling() -> str:
    load_dotenv()
    return os.environ.get("SENSITIVITY_CEILING", "public")
