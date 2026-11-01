"""Qual é mais rápido? — corrida entre força bruta e Dividir e Conquistar."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from src.algorithms import closest_pair_divide_conquer
from src.services.benchmark import compare_on, generate_uniform_points
from src.ui.theme import COLORS, page_header

ss = st.session_state

page_header("Qual é mais rápido?", "Os dois algoritmos resolvem os mesmos pontos aleatórios. Quem trabalha menos?")

PLOT_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(17,35,63,0.6)",
    margin=dict(l=10, r=10, t=10, b=10),
    legend=dict(orientation="h", y=1.08),
)


def fmt_int(n: float) -> str:
    return f"{n:,.0f}".replace(",", ".")


def fmt_ms(s: float) -> str:
    ms = s * 1000
    return f"{ms:,.1f} ms".replace(",", "X").replace(".", ",").replace("X", ".") if ms < 1000 else f"{s:.1f} s".replace(".", ",")


# ============================================================ corrida
c1, c2 = st.columns([4, 1], vertical_alignment="bottom")
n = c1.select_slider("Quantos pontos?", options=[10, 100, 500, 1000, 2000, 3000, 5000], value=1000)
if c2.button("▶ Comparar", type="primary", width="stretch"):
    with st.spinner("Calculando..."):
        ss["race"] = (n, compare_on(generate_uniform_points(n, seed=42), repeats=3))

if ss.get("race"):
    rn, res = ss["race"]
    bf, dc = res["bf"], res["dc"]
    factor = bf["median_s"] / dc["median_s"] if dc["median_s"] > 0 else 0
    st.markdown(
        f"""
<div class="tb-race">
  <div class="tb-vs"><span class="lbl">Força bruta</span><span class="num coral">{fmt_int(bf['evaluations'])}</span>
    <span class="sub">comparações · {fmt_ms(bf['median_s'])}</span></div>
  <div class="tb-vs"><span class="lbl">Dividir e Conquistar</span><span class="num teal">{fmt_int(dc['evaluations'])}</span>
    <span class="sub">comparações · {fmt_ms(dc['median_s'])}</span></div>
  <div class="tb-vs"><span class="lbl">Resultado</span><span class="num">{f"{factor:.0f}×" if factor >= 1.5 else "≈ 1×"}</span>
    <span class="sub">mais rápido · {'✅ mesma resposta' if res['match'] else '❌ respostas diferentes'}</span></div>
</div>
""",
        unsafe_allow_html=True,
    )
    if rn <= 100:
        st.caption("Com poucos pontos a diferença é pequena (a força bruta pode até ganhar, por ser mais simples). Aumente o número de pontos.")
else:
    st.info("Escolha a quantidade de pontos e clique em **Comparar**.")


# ===================================================== curva de crescimento
@st.cache_data
def growth() -> tuple[list[int], list[float], list[int]]:
    sizes = [10, 250, 500, 1000, 1500, 2000, 2500, 3000]
    brute = [n * (n - 1) / 2 for n in sizes]
    dc = [closest_pair_divide_conquer(generate_uniform_points(n, seed=42)).evaluations for n in sizes]
    return sizes, brute, dc


st.markdown("#### Comparações necessárias conforme o número de pontos cresce")
sizes, brute_cmp, dc_cmp = growth()
fig = go.Figure()
fig.add_trace(go.Scatter(x=sizes, y=brute_cmp, name="Força bruta · O(n²)", mode="lines+markers", line=dict(color=COLORS["coral"], width=4)))
fig.add_trace(go.Scatter(x=sizes, y=dc_cmp, name="Dividir e Conquistar · O(n log n)", mode="lines+markers", line=dict(color=COLORS["teal"], width=4)))
fig.update_layout(
    xaxis_title="Número de pontos", yaxis_title="Comparações", height=420, **PLOT_LAYOUT,
)
st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
st.caption(
    "A força bruta cresce como uma parábola (dobrar os pontos ≈ quadruplicar o trabalho). "
    "Dividir e Conquistar cresce quase em linha reta."
)
