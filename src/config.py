"""Configuração carregada de variáveis de ambiente (.env)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

load_dotenv(PROJECT_ROOT / ".env")


def reload_local_env() -> bool:
    """Recarrega explicitamente o .env após edição local (o arquivo tem precedência)."""
    path = PROJECT_ROOT / ".env"
    if not path.is_file():
        return False
    load_dotenv(path, override=True)
    return True

DEFAULT_HOST = "https://api.olhovivo.sptrans.com.br"
DEFAULT_VERSION = "v2.1"
_VERSION_SUFFIX = re.compile(r"/v\d+(\.\d+)?/?$")


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


def build_base_url(base: str, version: str) -> str:
    """Monta a URL base. Se ``base`` já termina em /vX.Y, usa como está."""
    base = (base or DEFAULT_HOST).rstrip("/")
    if _VERSION_SUFFIX.search(base):
        return base
    return f"{base}/{version.strip('/') or DEFAULT_VERSION}"


@dataclass(frozen=True)
class Settings:
    api_token: str
    base_url: str
    timeout_s: int
    refresh_interval_s: int
    stale_threshold_s: int
    db_path: Path

    @property
    def has_token(self) -> bool:
        return bool(self.api_token)


def get_settings() -> Settings:
    return Settings(
        api_token=_env("SPTRANS_API_TOKEN"),
        base_url=build_base_url(_env("SPTRANS_BASE_URL", DEFAULT_HOST), _env("SPTRANS_API_VERSION", DEFAULT_VERSION)),
        timeout_s=_env_int("SPTRANS_TIMEOUT_SECONDS", 15),
        # Intervalo mínimo de 30 s para não sobrecarregar a API.
        refresh_interval_s=max(30, _env_int("TWOBUS_REFRESH_SECONDS", 60)),
        stale_threshold_s=_env_int("TWOBUS_STALE_SECONDS", 180),
        db_path=Path(_env("TWOBUS_DB_PATH", str(DATA_DIR / "twobus.db"))),
    )
