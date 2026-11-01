"""Página 2 — Análise de proximidade ao longo do tempo (snapshots gravados)."""

from __future__ import annotations

from collections import Counter

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from src.services.analysis import analyze_snapshot, positions_df_to_snapshot, proximity_timeline
from src.services.demo_data import SCENARIOS
from src.services.snapshots import collect_demo
from src.ui.maps import build_map
from src.ui.state import current_mode, repository
from src.ui.theme import COLORS, SP_TZ, cards_row, fmt_local, fmt_meters, note, page_header

repo = repository()
mode = current_mode()
ss = st.session_state

page_header(
    "Análise de proximidade",
    "Evolução da menor distância entre veículos nos snapshots armazenados.",
    mode,
)
note(
    "Esta análise identifica <b>candidatos a agrupamento</b>. Dois ônibus próximos não formam, por si só, um comboio "
    "(<i>bus bunching</i>): para isso seria preciso analisar itinerário, sentido, horários programados e headway."
)

# ----------------------------------------------- geração de dados simulados
if mode == "demo":
    with st.expander("🧪 Gerar snapshots simulados para esta análise"):
        c1, c2, c3 = st.columns([2, 1, 1], vertical_alignment="bottom")
        key = c1.selectbox("Cenário", list(SCENARIOS), format_func=lambda k: f"{SCENARIOS[k].line.sign} — {SCENARIOS[k].description}")
        n = c2.number_input("Passos (60 s cada)", 5, 240, 30)
        if c3.button("Gerar", width="stretch"):
            line = SCENARIOS[key].line
            created = sum(collect_demo(line, k, repo, True).created for k in range(int(n)))
            st.success(f"{created} snapshot(s) novo(s) gravado(s) para {line.sign} (duplicatas ignoradas).")

lines = repo.list_lines()
lines = lines[lines["source"] == mode] if not lines.empty else lines
if lines.empty:
    st.info(
        "Ainda não há snapshots "
        + ("reais" if mode == "real" else "simulados")
        + " gravados. Faça consultas na página de Monitoramento"
        + (" ou gere snapshots acima." if mode == "demo" else ".")
    )
    st.stop()

c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
idx = c1.selectbox(
    "Linha / sentido",
    options=list(lines.index),
    format_func=lambda i: f"{lines.loc[i, 'line_sign']} · {lines.loc[i, 'direction_label']} · "
    f"cl={lines.loc[i, 'line_code']} · {lines.loc[i, 'collections']} coleta(s)",
)
sel = lines.loc[idx]
threshold = float(ss["threshold_m"])
c2.metric("Limite experimental", f"{threshold:.0f} m", help="Altere na barra lateral.")

tl = proximity_timeline(repo, mode, int(sel["line_code"]), threshold, ss["stale_s"], ss["exclude_stale"])
if tl.empty:
    st.info("Sem coletas para esta linha.")
    st.stop()

valid = tl.dropna(subset=["min_distance_m"])
below = tl[tl["below_threshold"]]
pairs = Counter(zip(below["vehicle_a"], below["vehicle_b"]))
top_pair, top_count = (pairs.most_common(1)[0] if pairs else (None, 0))
cards_row(
    [
        ("Coletas", str(len(tl)), f"{fmt_local(tl['collected_at_utc'].min(), True)} → {fmt_local(tl['collected_at_utc'].max())}", "sky"),
        ("Abaixo do limite", f"{len(below)}", f"{(len(below) / len(tl) * 100):.0f}% das coletas", "amber" if len(below) else "teal"),
        ("Maior sequência", f"{int(tl['consecutive'].max())} coleta(s)", "mesmo par abaixo do limite", "amber" if tl["consecutive"].max() >= 2 else "teal"),
        ("Par mais recorrente", " ↔ ".join(top_pair) if top_pair else "—", f"{top_count} ocorrência(s)", "teal"),
        ("Menor distância", fmt_meters(valid["min_distance_m"].min() if not valid.empty else None), "em todo o período", "sky"),
    ]
)

# ---------------------------------------------------------------- gráfico
x_local = tl["collected_at_utc"].map(lambda d: d.astimezone(SP_TZ))
fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=x_local,
        y=tl["min_distance_m"],
        mode="lines+markers",
        line=dict(color=COLORS["teal"], width=2.5),
        marker=dict(
            size=[12 if b else 7 for b in tl["below_threshold"]],
            color=[COLORS["amber"] if b else COLORS["teal"] for b in tl["below_threshold"]],
            line=dict(color="#0A1628", width=1),
        ),
        customdata=tl[["vehicle_a", "vehicle_b", "consecutive", "collection_id"]].values,
        hovertemplate="%{x|%d/%m %H:%M:%S}<br>Distância: %{y:.1f} m<br>Par: %{customdata[0]} ↔ %{customdata[1]}"
        "<br>Sequência: %{customdata[2]}<br>Coleta #%{customdata[3]}<extra></extra>",
        name="Menor distância",
    )
)
fig.add_hline(
    y=threshold, line_dash="dash", line_color=COLORS["coral"], annotation_text=f"limite {threshold:.0f} m", annotation_font_color=COLORS["coral"]
)
fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(17,35,63,0.6)",
    height=380,
    margin=dict(l=10, r=10, t=30, b=10),
    yaxis_title="Distância mínima (m)",
    xaxis_title="Horário da coleta (São Paulo)",
    showlegend=False,
)
st.plotly_chart(fig, width="stretch")

# ------------------------------------------------------------ ocorrências
st.markdown("#### Coletas e ocorrências")
only_below = st.toggle("Mostrar apenas coletas abaixo do limite", value=False)
show = (below if only_below else tl).copy()
show["Horário da coleta"] = show["collected_at_utc"].map(lambda d: fmt_local(d, True))
show = show.rename(
    columns={
        "collection_id": "Coleta",
        "valid_vehicles": "Veículos válidos",
        "stale_vehicles": "Desatualizados",
        "vehicle_a": "Veículo A",
        "vehicle_b": "Veículo B",
        "min_distance_m": "Distância (m)",
        "consecutive": "Sequência do par",
        "status": "Classificação",
    }
)[["Coleta", "Horário da coleta", "Veículos válidos", "Desatualizados", "Veículo A", "Veículo B", "Distância (m)", "Sequência do par", "Classificação"]]


def _hl(row):
    return ["background-color: rgba(251,191,36,0.15)" if row["Classificação"].startswith("Candidato") else ""] * len(row)


st.dataframe(
    show.style.apply(_hl, axis=1).format({"Distância (m)": "{:.1f}"}, na_rep="—"),
    hide_index=True,
    width="stretch",
    height=min(420, 38 + 35 * len(show)),
)
st.caption("“Sequência do par” = número de coletas consecutivas em que o MESMO par permaneceu abaixo do limite.")

# ------------------------------------------------------ inspeção de coleta
st.markdown("#### Inspecionar uma coleta")
cid = st.selectbox(
    "Coleta",
    options=list(tl["collection_id"])[::-1],
    format_func=lambda c: f"#{c} · {fmt_local(tl.loc[tl.collection_id == c, 'collected_at_utc'].iloc[0], True)}",
)
cols = repo.list_collections(source=mode, line_code=int(sel["line_code"]))
crow = cols[cols["id"] == cid].iloc[0]
snap = positions_df_to_snapshot(crow, repo.get_positions(int(cid)))
an = analyze_snapshot(snap, ss["stale_s"], ss["exclude_stale"])
st_folium(
    build_map(an, str(sel["line_sign"]), str(sel["direction_label"]), mode),
    height=440,
    use_container_width=True,
    returned_objects=[],
    key="prox_map",
)

# ------------------------------------------------------------- exportação
st.markdown("#### Exportação")
c1, c2 = st.columns(2)
c1.download_button(
    "⬇️ CSV desta linha",
    repo.export_dataframe(source=mode, line_code=int(sel["line_code"])).to_csv(index=False).encode("utf-8"),
    file_name=f"twobus_{mode}_{sel['line_code']}.csv",
    mime="text/csv",
    width="stretch",
)
c2.download_button(
    "⬇️ CSV da série de distâncias",
    tl.assign(collected_at_utc=tl["collected_at_utc"].map(lambda d: d.isoformat())).to_csv(index=False).encode("utf-8"),
    file_name=f"twobus_{mode}_{sel['line_code']}_serie.csv",
    mime="text/csv",
    width="stretch",
)
