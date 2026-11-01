"""Página inicial — apresenta o problema e o caminho de aprendizado."""

from __future__ import annotations

import streamlit as st

from src.ui.theme import page_header

page_header(
    "Quais dois ônibus estão mais perto um do outro?",
    "Um problema clássico de algoritmos, resolvido com dados reais dos ônibus de São Paulo.",
)

st.markdown(
    """
<div class="tb-hero">
  <div class="tb-hero-text">
    <p>Imagine os ônibus de uma linha como <b>pontos em um mapa</b>. Queremos achar o <b>par de pontos mais próximos</b>.</p>
    <p>O jeito óbvio é medir a distância de <b>cada ônibus para todos os outros</b>. Funciona, mas com muitos pontos
    fica lento: 1.000 pontos já dão quase <b>500 mil</b> comparações.</p>
    <p>O <b>Dividir e Conquistar</b> resolve o mesmo problema com bem menos trabalho: <b>corta o mapa ao meio</b>,
    resolve cada metade e depois só confere o que está <b>perto da linha de corte</b>.</p>
  </div>
  <div class="tb-hero-stat">
    <div class="tb-vs"><span class="lbl">Força bruta</span><span class="num coral">499.500</span><span class="sub">comparações para 1.000 pontos</span></div>
    <div class="tb-vs"><span class="lbl">Dividir e Conquistar</span><span class="num teal">1.131</span><span class="sub">comparações para os mesmos pontos</span></div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="tb-kicker">Siga nesta ordem</div>', unsafe_allow_html=True)

steps = [
    ("1", "Como funciona", "Veja o algoritmo resolver 7 pontos, passo a passo, com explicação de cada decisão.", "pages/algorithm_demo.py", ":material/school:"),
    ("2", "Ônibus ao vivo", "Escolha uma linha de São Paulo e veja no mapa os dois ônibus mais próximos agora.", "pages/monitoring.py", ":material/map:"),
    ("3", "Qual é mais rápido?", "Coloque os dois algoritmos para competir e veja a diferença crescer com o número de pontos.", "pages/benchmarking.py", ":material/speed:"),
]
for col, (num, title, text, page, icon) in zip(st.columns(3), steps):
    with col:
        st.markdown(
            f'<div class="tb-step-card"><span class="tb-step-num">{num}</span><h3>{title}</h3><p>{text}</p></div>',
            unsafe_allow_html=True,
        )
        st.page_link(page, label=f"Abrir: {title}", icon=icon, use_container_width=True)

st.caption(
    "Sem token da SPTrans? Escolha **Simulados** na barra lateral e tudo funciona do mesmo jeito. "
    "Lembre: dois ônibus próximos não significam, por si só, um problema na operação."
)
