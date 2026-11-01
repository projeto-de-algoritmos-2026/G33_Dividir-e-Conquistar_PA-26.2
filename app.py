"""TwoBus — monitoramento da proximidade entre ônibus de São Paulo.

Aplicação acadêmica (Projeto de Algoritmos): demonstra o Par de Pontos Mais
Próximos por Divisão e Conquista sobre dados da API Olho Vivo (SPTrans).

Execução:  streamlit run app.py
"""

from __future__ import annotations

import logging

import streamlit as st

from src.api.sptrans_client import SPTransError
from src.ui.state import bind, init_state, reload_settings, settings_cached, sptrans_client
from src.ui.theme import apply_theme

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

st.set_page_config(
    page_title="TwoBus · Proximidade entre ônibus de São Paulo",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "TwoBus — Projeto de Algoritmos: Par de Pontos Mais Próximos por Divisão e Conquista."},
)
apply_theme()
init_state()
settings = settings_cached()

pages = [
    st.Page("pages/home.py", title="Início", icon=":material/home:", default=True),
    st.Page("pages/algorithm_demo.py", title="1 · Como funciona", icon=":material/school:"),
    st.Page("pages/monitoring.py", title="2 · Ônibus ao vivo", icon=":material/map:"),
    st.Page("pages/benchmarking.py", title="3 · Qual é mais rápido?", icon=":material/speed:"),
]
nav = st.navigation(pages)
st.logo("assets/logo.svg", icon_image="assets/icon.svg", size="large")


def connection_status() -> None:
    """Estado da integração com a SPTrans, sem nunca exibir token ou URL."""
    if not settings.has_token:
        st.error("SPTRANS_API_TOKEN não definido. Copie .env.example para .env e informe o token.")
        return
    status = st.session_state.get("api_status")
    if status is None:
        chip = '<span class="tb-status idle">● Token configurado</span>'
    elif status == "ok":
        chip = '<span class="tb-status ok">● Conectado à API Olho Vivo</span>'
    else:
        chip = '<span class="tb-status err">● Falha na conexão</span>'
    st.markdown(chip, unsafe_allow_html=True)
    if status not in (None, "ok"):
        st.caption(status)
    if not settings.base_url.lower().startswith("https://"):
        st.caption("⚠️ `SPTRANS_BASE_URL` não usa HTTPS: o token trafega sem criptografia.")
    c1, c2 = st.columns(2)
    if c1.button("Testar", width="stretch", help="Autentica na API com o token do .env."):
        try:
            sptrans_client().authenticate()
            st.session_state["api_status"] = "ok"
        except SPTransError as exc:
            st.session_state["api_status"] = str(exc)
        st.rerun()
    if c2.button("Recarregar", width="stretch", help="Lê o .env de novo após substituir a chave."):
        if reload_settings():
            st.session_state.pop("api_status", None)
            st.rerun()
        else:
            st.warning("Arquivo .env não encontrado. Crie-o a partir de .env.example.")


with st.sidebar:
    st.radio(
        "Dados dos ônibus",
        options=["real", "demo"],
        format_func=lambda m: "🛰️ Reais (SPTrans)" if m == "real" else "🧪 Simulados",
        **bind("mode"),
        horizontal=True,
    )
    if st.session_state["mode"] == "real":
        connection_status()

    with st.expander("Ajustes avançados"):
        st.number_input(
            "O que conta como \"perto\" (m)",
            min_value=10,
            max_value=5000,
            step=10,
            **bind("threshold_m"),
            help="Pares mais próximos que isso recebem um alerta no mapa.",
        )
        st.number_input(
            "Ignorar posições com mais de (s)",
            min_value=30,
            max_value=3600,
            step=30,
            **bind("stale_s"),
            help="Posições GPS antigas demais podem enganar o resultado.",
        )
        st.toggle("Ignorar posições antigas", **bind("exclude_stale"))

nav.run()
