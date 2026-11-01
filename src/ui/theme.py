"""Identidade visual do TwoBus (CSS + componentes HTML simples)."""

from __future__ import annotations

import html
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

SP_TZ = ZoneInfo("America/Sao_Paulo")

COLORS = {
    "navy": "#0A1628",
    "navy2": "#11233F",
    "navy3": "#1A3358",
    "teal": "#2DD4BF",
    "teal_dark": "#0F9488",
    "sky": "#60A5FA",
    "white": "#E6EEF8",
    "muted": "#8BA3C7",
    "amber": "#FBBF24",
    "coral": "#FB7185",
    "grey": "#64748B",
}

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"], .stMarkdown, .stText, p, label { font-family: 'Inter', sans-serif; }
h1, h2, h3, h4 { font-family: 'Outfit', sans-serif !important; letter-spacing: -0.01em; }
code, pre { font-family: 'JetBrains Mono', monospace !important; }

[data-testid="stAppViewContainer"] {
  background: radial-gradient(950px 620px at 4% -12%, rgba(45,212,191,0.13), transparent 65%),
              radial-gradient(750px 460px at 106% 4%, rgba(96,165,250,0.12), transparent 65%),
              linear-gradient(180deg, #091423 0%, #0A1628 70%, #0b192d 100%);
}
[data-testid="stSidebar"] { background: linear-gradient(180deg, #0D203A 0%, #0A1628 100%); border-right: 1px solid rgba(96,165,250,.16); }
.block-container { padding-top: 2.6rem; max-width: 1480px; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebarHeader"] { padding-bottom: .4rem; }
[data-testid="stSidebarHeader"] img { height: 2.4rem; }
[data-testid="stSidebar"] .tb-kicker { margin: 0 0 .9rem; font-size: .62rem; color:#7FA0C4; }
.tb-status { display:inline-flex; align-items:center; gap:.35rem; padding:.3rem .7rem; border-radius:999px; font-size:.76rem; font-weight:600; margin:.1rem 0 .35rem; }
.tb-status.ok   { background:rgba(45,212,191,.12); color:#5EEAD4; border:1px solid rgba(45,212,191,.4); }
.tb-status.idle { background:rgba(96,165,250,.10); color:#93C5FD; border:1px solid rgba(96,165,250,.32); }
.tb-status.err  { background:rgba(251,113,133,.12); color:#FDA4AF; border:1px solid rgba(251,113,133,.42); }
[data-testid="stSidebarNav"] { margin-top: .7rem; }
[data-testid="stSidebarNav"] a { border-radius: 10px; margin: .18rem .35rem; }
[data-testid="stSidebarNav"] a:hover { background: rgba(45,212,191,.10); }
div.stButton > button[kind="primary"] { border:0; color:#082033; font-weight:750;
  background:linear-gradient(110deg,#31E6CD,#60A5FA); box-shadow:0 6px 20px rgba(45,212,191,.17); }
div.stButton > button[kind="primary"]:hover { color:#061a2c; filter:brightness(1.07); }
div[data-testid="stTabs"] button { font-weight:600; }

.tb-header { display:flex; align-items:center; justify-content:space-between; gap:1rem;
  padding: 1.3rem 1.55rem; border-radius: 20px; margin-bottom: 1.2rem;
  background:linear-gradient(120deg,rgba(17,35,63,.98),rgba(18,61,78,.82));
  border:1px solid rgba(45,212,191,.22); box-shadow:0 20px 40px rgba(0,0,0,.18); position:relative; overflow:hidden; }
.tb-header::after { content:""; position:absolute; right:10%; top:-62px; width:170px; height:170px;
  border:1px solid rgba(45,212,191,.10); border-radius:50%; box-shadow:0 0 0 38px rgba(45,212,191,.035),0 0 0 77px rgba(45,212,191,.025); pointer-events:none; }
.tb-header h1 { margin:0; font-size:clamp(1.55rem,2vw,2rem); color:#F8FAFC; }
.tb-header p { margin:.22rem 0 0; color:#B1C6DF; font-size:.95rem; }

.tb-badge { display:inline-flex; align-items:center; gap:.4rem; padding:.35rem .8rem; border-radius:999px;
  font-size:.78rem; font-weight:600; letter-spacing:.04em; text-transform:uppercase; white-space:nowrap; }
.tb-badge.real { background: rgba(45,212,191,0.14); color:#5EEAD4; border:1px solid rgba(45,212,191,0.45); }
.tb-badge.demo { background: rgba(251,191,36,0.14); color:#FCD34D; border:1px solid rgba(251,191,36,0.5); }
.tb-dot { width:8px; height:8px; border-radius:50%; background: currentColor; animation: tbpulse 1.8s infinite; }
@keyframes tbpulse { 0%{opacity:1; transform:scale(1)} 50%{opacity:.35; transform:scale(.7)} 100%{opacity:1; transform:scale(1)} }

.tb-card { background:linear-gradient(160deg,rgba(23,48,82,.96),rgba(13,31,54,.98)); border:1px solid rgba(124,159,199,.16);
  border-radius:16px; padding:1rem 1.1rem; height:100%; min-height:118px; box-shadow:0 8px 24px rgba(0,0,0,.13); transition:transform .15s ease,border-color .15s ease; }
.tb-card:hover { transform: translateY(-2px); border-color: rgba(45,212,191,0.45); }
.tb-card .lbl { color:#8BA3C7; font-size:.76rem; text-transform:uppercase; letter-spacing:.06em; font-weight:600; }
.tb-card .val { color:#F8FAFC; font-family:'Outfit',sans-serif; font-size:clamp(1.05rem,1.45vw,1.5rem); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font-weight:600; margin-top:.15rem; line-height:1.2; }
.tb-card .sub { color:#8BA3C7; font-size:.8rem; margin-top:.2rem; }
.tb-card.teal  { border-left: 4px solid #2DD4BF; }
.tb-card.amber { border-left: 4px solid #FBBF24; }
.tb-card.coral { border-left: 4px solid #FB7185; }
.tb-card.sky   { border-left: 4px solid #60A5FA; }

.tb-note { border-radius: 12px; padding: .7rem .95rem; font-size: .88rem; margin:.4rem 0;
  background: rgba(96,165,250,0.08); border:1px solid rgba(96,165,250,0.25); color:#C7D7EE; }
.tb-note.warn { background: rgba(251,191,36,0.08); border-color: rgba(251,191,36,0.35); color:#FDE68A; }

.tb-step { background:#0E1D35; border:1px solid #1A3358; border-radius:14px; padding:1rem 1.1rem; }
.tb-step h4 { margin:0 0 .35rem 0; color:#5EEAD4; }
.tb-code { background:#081222; border:1px solid #1A3358; border-radius:12px; padding:.6rem .2rem; font-family:'JetBrains Mono',monospace; font-size:.8rem; }
.tb-code div { padding: .08rem .8rem; white-space: pre; color:#8BA3C7; }
.tb-code div.on { background: rgba(45,212,191,0.16); color:#F8FAFC; border-left:3px solid #2DD4BF; }
.tb-chip { display:inline-block; padding:.12rem .5rem; margin:.12rem; border-radius:8px; background:#1A3358; color:#E6EEF8;
  font-family:'JetBrains Mono',monospace; font-size:.8rem; }
.tb-chip.on { background:#0F9488; color:#fff; }
.tb-chip.hot { background:#B45309; color:#fff; }

.tb-kicker { color:#2DD4BF; font:700 .72rem 'Inter',sans-serif; letter-spacing:.15em; text-transform:uppercase; margin:1rem 0 .45rem; }
.tb-lesson { border:1px solid rgba(45,212,191,.22); border-radius:18px; padding:1.1rem 1.2rem;
  background:linear-gradient(135deg,rgba(25,53,85,.92),rgba(11,29,51,.96)); box-shadow:0 12px 28px rgba(0,0,0,.12); }
.tb-lesson h3 { margin:0 0 .35rem; color:#F8FAFC; font-size:1.15rem; }
.tb-lesson p { color:#B4C8E0; margin:.3rem 0; }
.tb-phase-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.6rem; margin:.8rem 0 1.15rem; }
.tb-phase { border:1px solid #25415f; border-radius:12px; padding:.7rem .8rem; background:rgba(17,35,63,.72); }
.tb-phase.active { border-color:#2DD4BF; background:rgba(45,212,191,.12); box-shadow:inset 0 0 0 1px rgba(45,212,191,.12); }
.tb-phase .num { color:#2DD4BF; font:700 .72rem 'JetBrains Mono',monospace; }
.tb-phase .name { display:block; color:#F2F7FF; font-weight:650; font-size:.87rem; }
.tb-phase .desc { color:#91A9C9; font-size:.72rem; line-height:1.3; }
.tb-code { margin-top:.5rem; }
.tb-tree-node { text-align:center; border:1px solid #294664; background:rgba(17,35,63,.85); border-radius:12px; padding:.45rem; margin:.2rem 0; color:#B6C8DD; font:600 .78rem 'JetBrains Mono',monospace; }
.tb-tree-node.active { border-color:#2DD4BF; background:rgba(45,212,191,.16); color:#F6FFFE; box-shadow:0 0 18px rgba(45,212,191,.08); }
.tb-hero { display:grid; grid-template-columns:1.5fr 1fr; gap:1.4rem; align-items:center; margin:.2rem 0 1.4rem;
  padding:1.3rem 1.5rem; border-radius:18px; background:rgba(17,35,63,.55); border:1px solid rgba(124,159,199,.16); }
.tb-hero-text p { color:#C7D7EE; font-size:1.02rem; line-height:1.6; margin:.35rem 0; }
.tb-hero-text b { color:#F8FAFC; }
.tb-hero-stat { display:grid; gap:.7rem; }
.tb-race { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.8rem; margin:1rem 0 1.2rem; }
.tb-vs { display:flex; flex-direction:column; gap:.15rem; padding:.9rem 1.1rem; border-radius:14px;
  background:linear-gradient(160deg,rgba(23,48,82,.96),rgba(13,31,54,.98)); border:1px solid rgba(124,159,199,.16); }
.tb-vs .lbl { color:#8BA3C7; font-size:.76rem; text-transform:uppercase; letter-spacing:.06em; font-weight:600; }
.tb-vs .num { font:700 2.1rem 'Outfit',sans-serif; color:#F8FAFC; line-height:1.1; }
.tb-vs .num.coral { color:#FB7185; } .tb-vs .num.teal { color:#2DD4BF; }
.tb-vs .sub { color:#8BA3C7; font-size:.82rem; }
.tb-step-card { position:relative; padding:1.1rem 1.2rem 1rem; border-radius:16px; min-height:150px; margin-bottom:.5rem;
  background:linear-gradient(160deg,rgba(23,48,82,.96),rgba(13,31,54,.98)); border:1px solid rgba(45,212,191,.22); }
.tb-step-card h3 { margin:.5rem 0 .3rem; font-size:1.15rem; color:#F8FAFC; }
.tb-step-card p { color:#A9BFDA; font-size:.9rem; margin:0; }
.tb-step-num { display:inline-grid; place-items:center; width:1.9rem; height:1.9rem; border-radius:50%;
  background:linear-gradient(135deg,#2DD4BF,#60A5FA); color:#0A1628; font:700 .95rem 'Outfit',sans-serif; }
@media (max-width:750px) { .tb-header { align-items:flex-start; flex-direction:column; } .tb-phase-grid { grid-template-columns:repeat(2,1fr); } .tb-hero, .tb-race { grid-template-columns:1fr; } }
div[data-testid="stMetricValue"] { font-family:'Outfit',sans-serif; }
</style>
"""


def apply_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def mode_badge(mode: str) -> str:
    if mode == "demo":
        return '<span class="tb-badge demo"><span class="tb-dot"></span>Modo Demonstração · dados simulados</span>'
    return '<span class="tb-badge real"><span class="tb-dot"></span>Modo Real · API SPTrans</span>'


def page_header(title: str, subtitle: str, mode: str | None = None) -> None:
    badge = mode_badge(mode) if mode else ""
    st.markdown(
        f'<div class="tb-header"><div><h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div>{badge}</div>',
        unsafe_allow_html=True,
    )


def card(label: str, value: str, sub: str = "", tone: str = "teal") -> str:
    return (
        f'<div class="tb-card {tone}"><div class="lbl">{html.escape(label)}</div>'
        f'<div class="val" title="{html.escape(value)}">{html.escape(value)}</div><div class="sub">{html.escape(sub)}</div></div>'
    )


def cards_row(items: list[tuple[str, str, str, str]]) -> None:
    cols = st.columns(len(items))
    for col, (label, value, sub, tone) in zip(cols, items):
        col.markdown(card(label, value, sub, tone), unsafe_allow_html=True)


def note(text: str, warn: bool = False) -> None:
    st.markdown(f'<div class="tb-note {"warn" if warn else ""}">{text}</div>', unsafe_allow_html=True)


def fmt_local(dt: datetime | None, with_date: bool = False) -> str:
    if dt is None:
        return "—"
    fmt = "%d/%m/%Y %H:%M:%S" if with_date else "%H:%M:%S"
    return dt.astimezone(SP_TZ).strftime(fmt)


def fmt_meters(d: float | None) -> str:
    if d is None:
        return "—"
    if d >= 1000:
        return f"{d / 1000:,.2f} km".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{d:,.1f} m".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_age(seconds: float | None) -> str:
    if seconds is None:
        return "sem horário"
    if seconds < 0:
        return f"{-seconds:.0f} s no futuro"
    if seconds < 90:
        return f"há {seconds:.0f} s"
    return f"há {seconds / 60:.1f} min"
