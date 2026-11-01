"""Como funciona — o algoritmo em 6 passos sobre os 7 pontos de exemplo.

Os números de cada passo vêm da trilha de eventos da execução real.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from src.algorithms import closest_pair_brute_force, closest_pair_divide_conquer
from src.config import DATA_DIR
from src.services.benchmark import load_points_csv
from src.ui.theme import COLORS, page_header

points = load_points_csv(DATA_DIR / "sample_7_points.csv")
result = closest_pair_divide_conquer(points, trace=True)
brute = closest_pair_brute_force(points)
events = result.events
by_id = {p.id: p for p in points}

# Eventos-chave da chamada principal (profundidade 0).
top_divide = next(e for e in events if e["type"] == "divide" and e["depth"] == 0)
top_combine = next(e for e in events if e["type"] == "combine" and e["depth"] == 0)
top_strip = next(e for e in events if e["type"] == "strip" and e["depth"] == 0)
left_ids, right_ids = top_divide["left"], top_divide["right"]
mid_x, delta = top_divide["mid_x"], top_combine["delta"]
lb, rb, best = top_combine["left_best"], top_combine["right_best"], events[-1]["best"]


def pair(p: dict) -> str:
    return f"{p['a']}–{p['b']}"


STEPS = [
    {
        "title": "O problema",
        "text": f"Temos **{len(points)} pontos** (pense em {len(points)} ônibus). Queremos os **dois mais próximos**. "
        f"A força bruta mediria todos os pares: **{brute.evaluations} comparações**. Dá para fazer melhor?",
    },
    {
        "title": "Dividir: cortar ao meio",
        "text": f"Ordenamos os pontos da esquerda para a direita e traçamos uma **linha vertical no meio**. "
        f"Agora temos dois problemas menores: **{', '.join(left_ids)}** à esquerda e **{', '.join(right_ids)}** à direita.",
    },
    {
        "title": "Conquistar: resolver a esquerda",
        "text": f"Com poucos pontos, comparamos direto. O par mais próximo da esquerda é **{pair(lb)} = {lb['distance']:.2f}**.",
        "line": (lb, "teal"),
    },
    {
        "title": "Conquistar: resolver a direita",
        "text": f"A direita é dividida de novo (a mesma ideia, repetida). O melhor da direita é "
        f"**{pair(rb)} = {rb['distance']:.2f}**.",
        "line": (rb, "amber"),
    },
    {
        "title": "Combinar: olhar perto do corte",
        "text": f"O melhor até agora é **δ = {delta:.2f}**. Mas pode existir um par com **um ponto de cada lado**! "
        f"Ele só pode estar **perto da linha**: na faixa de largura δ para cada lado. Pontos fora dela "
        "estão longe demais e são ignorados.",
        "strip": True,
    },
    {
        "title": "Resultado",
        "text": f"Na faixa encontramos **{pair(best)} = {best['distance']:.2f}**, menor que δ. Essa é a resposta! "
        f"Sem a etapa de combinar, teríamos respondido {pair(lb)}, que está **errado**.",
        "line": (best, "coral"),
        "strip": True,
    },
]

page_header("Como funciona", "Dividir e Conquistar em 6 passos, com 7 pontos de exemplo.")

st.session_state.setdefault("demo_chapter", 0)
step = st.session_state["demo_chapter"]

nav_l, nav_mid, nav_r = st.columns([1, 4, 1], vertical_alignment="center")
if nav_l.button("← Voltar", disabled=step == 0, width="stretch"):
    step -= 1
if nav_r.button("Avançar →", disabled=step == len(STEPS) - 1, type="primary", width="stretch"):
    step += 1
st.session_state["demo_chapter"] = step
nav_mid.progress((step + 1) / len(STEPS), text=f"Passo {step + 1} de {len(STEPS)}")

s = STEPS[step]
col_chart, col_text = st.columns([3, 2], gap="large")

with col_text:
    st.markdown(
        f'<div class="tb-lesson"><div class="tb-kicker">Passo {step + 1}</div><h3>{s["title"]}</h3></div>',
        unsafe_allow_html=True,
    )
    st.markdown(s["text"])
    if step == len(STEPS) - 1:
        st.success(
            f"**Dividir e Conquistar:** {result.evaluations} comparações  \n"
            f"**Força bruta:** {brute.evaluations} comparações  \n"
            "Mesma resposta, menos trabalho. Com milhares de pontos a diferença fica enorme (veja o passo 3 do menu)."
        )

with col_chart:
    fig = go.Figure()
    show_split = step >= 1
    if s.get("strip"):
        fig.add_vrect(
            x0=mid_x - delta, x1=mid_x + delta, fillcolor=COLORS["amber"], opacity=0.16, line_width=0,
            annotation_text="faixa central", annotation_position="bottom", annotation_font_color=COLORS["amber"],
        )
    if show_split:
        fig.add_vline(x=mid_x, line_dash="dash", line_color=COLORS["amber"], line_width=2)

    if step == 0:
        colors = [COLORS["sky"]] * len(points)
    elif s.get("strip"):
        in_strip = set(top_strip["strip"])
        colors = [COLORS["amber"] if p.id in in_strip else COLORS["grey"] for p in points]
    else:
        colors = [COLORS["teal"] if p.id in left_ids else COLORS["sky"] for p in points]

    if "line" in s:
        p, tone = s["line"]
        a, b = by_id[p["a"]], by_id[p["b"]]
        fig.add_trace(go.Scatter(
            x=[a.x, b.x], y=[a.y, b.y], mode="lines", line=dict(color=COLORS[tone], width=5), hoverinfo="skip", showlegend=False,
        ))
        colors = [COLORS[tone] if pt.id in (p["a"], p["b"]) else c for pt, c in zip(points, colors)]

    fig.add_trace(go.Scatter(
        x=[p.x for p in points], y=[p.y for p in points], mode="markers+text",
        text=[p.id for p in points], textposition="top center", textfont=dict(size=15, color="#F8FAFC"),
        marker=dict(size=22, color=colors, line=dict(color="#ffffff", width=1.5)),
        hovertemplate="%{text}<extra></extra>", showlegend=False,
    ))
    if show_split:
        fig.add_annotation(x=mid_x - 0.3, y=12.3, text="esquerda", showarrow=False, xanchor="right", font=dict(color=COLORS["teal"]))
        fig.add_annotation(x=mid_x + 0.3, y=12.3, text="direita", showarrow=False, xanchor="left", font=dict(color=COLORS["sky"]))
    fig.update_layout(
        template="plotly_dark", height=470, margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(range=[-0.5, 13.5], showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(range=[-0.5, 13], showgrid=False, zeroline=False, showticklabels=False, scaleanchor="x", scaleratio=1),
        paper_bgcolor="rgba(17,35,63,0.6)", plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

with st.expander("Por que é mais rápido? (a conta)"):
    st.markdown(
        r"""
Cada nível **corta o problema ao meio** e a etapa de combinar faz um trabalho proporcional a $n$
(na faixa, cada ponto só precisa ser comparado com no máximo 7 vizinhos):

$$T(n) = 2\,T(n/2) + O(n) \;\Rightarrow\; O(n \log n) \qquad \text{contra} \qquad O(n^2) \text{ da força bruta}$$
        """
    )
