"""Estado compartilhado da interface (recursos em cache e preferências)."""

from __future__ import annotations

import streamlit as st

from src.api.sptrans_client import SPTransClient
from src.config import Settings, get_settings, reload_local_env
from src.storage.database import SnapshotRepository

DEFAULTS = {
    "mode": "demo",
    "threshold_m": 300,
    "exclude_stale": True,
}


def init_state() -> None:
    settings = settings_cached()
    for k, v in DEFAULTS.items():
        st.session_state.setdefault(k, v)
    st.session_state.setdefault("stale_s", settings.stale_threshold_s)
    if "mode_initialized" not in st.session_state:
        st.session_state["mode"] = "real" if settings.has_token else "demo"
        st.session_state["mode_initialized"] = True


def bind(key: str) -> dict:
    """Argumentos para um widget global que persiste ``key`` entre páginas.

    O widget usa a chave própria ``_key``; o valor é copiado para ``key`` (chave
    comum, nunca descartada pela limpeza de estado de widgets do Streamlit).
    """
    def _sync() -> None:
        st.session_state[key] = st.session_state[f"_{key}"]

    st.session_state[f"_{key}"] = st.session_state[key]
    return {"key": f"_{key}", "on_change": _sync}


@st.cache_resource
def settings_cached() -> Settings:
    return get_settings()


@st.cache_resource
def repository() -> SnapshotRepository:
    return SnapshotRepository(settings_cached().db_path)


@st.cache_resource
def sptrans_client() -> SPTransClient:
    """Uma única sessão HTTP autenticada por processo (reautentica se expirar)."""
    s = settings_cached()
    return SPTransClient(s.api_token, s.base_url, s.timeout_s)


def current_mode() -> str:
    return st.session_state.get("mode", "demo")


def reload_settings() -> bool:
    """Lê o .env novamente e descarta a sessão HTTP com a chave anterior."""
    if not reload_local_env():
        return False
    settings_cached.clear()
    sptrans_client.clear()
    return True
