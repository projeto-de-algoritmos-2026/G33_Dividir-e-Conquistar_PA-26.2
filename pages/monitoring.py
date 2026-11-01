"""Ônibus ao vivo: linha → posições → par mais próximo no mapa."""

from __future__ import annotations

import time
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from src.api.sptrans_client import SPTransAuthError, SPTransError
from src.geo.coordinates import vehicles_to_points
from src.models import BusLine
from src.services.analysis import analyze_snapshot
from src.services.demo_data import SCENARIOS
from src.services.snapshots import collect_demo, collect_real
from src.ui.maps import build_map
from src.ui.state import current_mode, repository, settings_cached, sptrans_client
from src.ui.theme import cards_row, fmt_age, fmt_local, fmt_meters, note, page_header

settings = settings_cached()
repo = repository()
mode = current_mode()

page_header(
    "Ônibus ao vivo",
    "Escolha uma linha: cada ônibus vira um ponto e o algoritmo encontra os dois mais próximos.",
    mode,
)

ss = st.session_state
ss.setdefault("demo_steps", {})
ss.setdefault("search_results", [])

# =========================================================== seleção da linha
line: BusLine | None = None

if mode == "real":
    if not settings.has_token:
        st.error("Configure `SPTRANS_API_TOKEN` no arquivo `.env` ou use o Modo Demonstração na barra lateral.")
        st.stop()
    with st.form("search_form", border=False):
        c1, c2 = st.columns([5, 1], vertical_alignment="bottom")
        term = c1.text_input(
            "Qual linha?", placeholder="Digite o número ou o nome, ex.: 8000, 875A, Lapa", key="search_term"
        )
        submitted = c2.form_submit_button("🔎 Buscar", width="stretch")
    if submitted:
        try:
            ss["search_results"] = sptrans_client().search_lines(term)
            ss["api_status"] = "ok"
            if not ss["search_results"]:
                st.info("Nenhuma linha encontrada para esse termo.")
        except SPTransAuthError as exc:
            ss["api_status"] = str(exc)
            st.error(f"Falha de autenticação: {exc}")
            st.info(
                "Confira se a conta de desenvolvedor foi confirmada e se a chave em `SPTRANS_API_TOKEN` "
                "é a do aplicativo em **Meus Aplicativos**. A documentação não detalha o motivo de uma "
                "resposta `false`. Se atualizar o `.env`, clique em **Recarregar** "
                "na barra lateral. O Modo Demonstração continua disponível."
            )
        except SPTransError as exc:
            st.error(f"Não foi possível consultar a SPTrans: {exc}")

    results: list[BusLine] = ss["search_results"]
    if results:
        groups: dict[tuple, list[BusLine]] = {}
        for ln in results:
            groups.setdefault((ln.sign, ln.main_terminal, ln.secondary_terminal), []).append(ln)
        c1, c2 = st.columns([2, 3])
        gkey = c1.selectbox(
            "Linha",
            options=list(groups),
            format_func=lambda k: f"{k[0]} — {k[1]} ⇄ {k[2]}",
        )
        options = sorted(groups[gkey], key=lambda l: l.direction)
        line = c2.radio(
            "Sentido",
            options=options,
            format_func=lambda l: f"{l.origin} → {l.destination}",
        )
else:
    c1, c2 = st.columns([2, 3])
    key = c1.selectbox(
        "Linha simulada",
        options=list(SCENARIOS),
        format_func=lambda k: f"{SCENARIOS[k].line.sign} — {SCENARIOS[k].line.secondary_terminal}",
    )
    line = SCENARIOS[key].line
    c2.markdown("&nbsp;")
    c2.caption(f"🧪 {SCENARIOS[key].description} Cada consulta avança 1 minuto no tempo simulado.")

if line is None:
    note("Pesquise uma linha para começar (ex.: <b>8000</b>). Sem internet? Escolha <b>Simulados</b> na barra lateral.")
    st.stop()

if ss.get("mon_line") != line:
    ss["mon_line"] = line
    ss.pop("mon_snapshot", None)
    ss.pop("mon_error", None)
    ss["mon_last_fetch"] = 0.0

# ================================================================ controles
min_interval = 30 if mode == "real" else 3
default_interval = settings.refresh_interval_s if mode == "real" else 5
query = st.button("📡 Buscar ônibus agora", type="primary")
with st.expander("Opções"):
    o1, o2, o3, o4 = st.columns(4, vertical_alignment="bottom")
    auto = o1.toggle("Atualizar sozinho", key=f"auto_{mode}")
    interval = o2.number_input(
        "A cada (s)",
        min_value=min_interval,
        max_value=600,
        value=max(min_interval, default_interval),
        step=5 if mode == "demo" else 15,
        key=f"interval_{mode}",
        help="Com dados reais o mínimo é 30 s, para não sobrecarregar a SPTrans.",
    )
    save = o3.checkbox("Salvar histórico", value=True, key="save_snapshot", help="Guarda cada consulta no banco SQLite.")
    if mode == "demo":
        step = ss["demo_steps"].get(line.code, 0)
        if o4.button("↺ Recomeçar simulação", width="stretch"):
            ss["demo_steps"][line.code] = 0
            ss.pop("mon_snapshot", None)


def fetch(line: BusLine) -> None:
    """Exatamente UMA consulta (real ou simulada)."""
    ss["mon_last_fetch"] = time.time()
    try:
        if line.source == "demo":
            step = ss["demo_steps"].get(line.code, 0)
            outcome = collect_demo(line, step, repo, save)
            ss["demo_steps"][line.code] = step + 1
            ss["mon_step"] = step
        else:
            outcome = collect_real(sptrans_client(), line, repo, save)
        ss["mon_snapshot"] = outcome.snapshot
        ss["mon_saved"] = (outcome.collection_id, outcome.created)
        ss.pop("mon_error", None)
    except SPTransAuthError as exc:
        ss["mon_error"] = f"Falha de autenticação: {exc}"
    except SPTransError as exc:
        ss["mon_error"] = f"Erro ao consultar a SPTrans: {exc}"


if query:
    fetch(line)


# ============================================================= painel vivo
@st.fragment(run_every=interval if auto else None)
def live_panel() -> None:
    # Só consulta se o intervalo realmente passou (evita chamadas a cada interação).
    if auto and time.time() - ss.get("mon_last_fetch", 0.0) >= interval - 0.5:
        fetch(line)

    if ss.get("mon_error"):
        st.error(ss["mon_error"])
    snap = ss.get("mon_snapshot")
    if snap is None:
        note("Clique em <b>Buscar ônibus agora</b> para ver os veículos da linha no mapa.")
        st_folium(build_map(None, "", "", mode), height=480, use_container_width=True, returned_objects=[], key="mon_map")
        return

    an = analyze_snapshot(snap, ss["stale_s"], ss["exclude_stale"])
    threshold = float(ss["threshold_m"])
    below = an.found and an.dc.distance < threshold

    status_txt, status_tone = ("Muito perto!", "amber") if below else (("Distância normal", "teal") if an.found else ("Sem par", "sky"))
    cards_row(
        [
            ("Ônibus no mapa", str(len(an.used)), f"atualizado às {fmt_local(snap.collected_at_utc)}", "sky"),
            ("Os dois mais próximos", " e ".join(an.dc.pair_ids) if an.found else "—", f"linha {line.sign}", "teal"),
            ("Distância entre eles", fmt_meters(an.dc.distance if an.found else None), "em linha reta", "teal"),
            ("Situação", status_txt, f"\"perto\" = menos de {threshold:.0f} m", status_tone),
        ]
    )

    if an.found:
        note(
            f"🧠 <b>Dividir e Conquistar</b> fez <b>{an.dc.evaluations}</b> comparação(ões); a <b>força bruta</b> fez "
            f"<b>{an.bf.evaluations}</b>. "
            + ("✅ Os dois chegaram à mesma resposta." if an.results_match else "❌ As respostas divergiram!")
            + " Com tão poucos ônibus a diferença é pequena; ela aparece com muitos pontos (passo 3)."
        )
    else:
        st.info("São necessários pelo menos dois ônibus com posição válida.")
    if snap.source == "demo":
        note("🧪 <b>Dados simulados</b>: nada aqui veio da SPTrans.", warn=True)
    for w in an.warnings:
        note("⚠️ " + w, warn=True)
    if below:
        note(
            f"🔶 {an.dc.pair_ids[0]} e {an.dc.pair_ids[1]} estão a só {fmt_meters(an.dc.distance)}. "
            "Isso pode indicar ônibus andando juntos, mas não é prova: eles podem estar no terminal ou em pistas opostas.",
            warn=True,
        )

    fmap = build_map(an, line.sign, line.direction_label, snap.source)
    st_folium(fmap, height=560, use_container_width=True, returned_objects=[], key="mon_map")
    st.caption("🟡 os dois mais próximos · 🟢 demais ônibus · ⚪ posição antiga (ignorada). A linha tracejada é a distância em linha reta, não o caminho pelas ruas.")

    with st.expander(f"Ver dados dos ônibus ({len(snap.vehicles)})"):
        pts = {p.id: p for p in vehicles_to_points(snap.vehicles)}
        pair = set(an.dc.pair_ids or ())
        used = {v.vehicle_id for v in an.used}
        rows = [
            {
                "Prefixo": s.vehicle.vehicle_id,
                "Latitude": s.vehicle.latitude,
                "Longitude": s.vehicle.longitude,
                "X UTM (m)": pts[s.vehicle.vehicle_id].x,
                "Y UTM (m)": pts[s.vehicle.vehicle_id].y,
                "Posição capturada": fmt_local(s.vehicle.position_time_utc, True),
                "Idade": fmt_age(s.age_s),
                "Situação": "Par mais próximo"
                if s.vehicle.vehicle_id in pair
                else ("Válido" if s.vehicle.vehicle_id in used else f"Excluído ({s.reason})"),
            }
            for s in an.statuses
        ]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    if auto:
        nxt = max(0, interval - (time.time() - ss.get("mon_last_fetch", 0)))
        st.caption(f"🔄 Atualizando sozinho a cada {interval} s · próxima em ~{nxt:.0f} s")


live_panel()
