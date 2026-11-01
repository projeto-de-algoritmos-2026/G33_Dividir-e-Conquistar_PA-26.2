"""Construção do mapa Folium a partir de uma análise de proximidade."""

from __future__ import annotations

import html

import folium

from src.services.analysis import ProximityAnalysis
from src.ui.theme import COLORS, fmt_age, fmt_local, fmt_meters

SP_CENTER = (-23.5505, -46.6333)


def build_map(analysis: ProximityAnalysis | None, line_label: str, direction_label: str, source: str) -> folium.Map:
    fmap = folium.Map(location=SP_CENTER, zoom_start=12, tiles="OpenStreetMap", control_scale=True)
    if analysis is None or not analysis.statuses:
        return fmap

    pair = set(analysis.dc.pair_ids or ())
    used_ids = {v.vehicle_id for v in analysis.used}
    tag = "SIMULADO" if source == "demo" else "SPTrans"

    bounds = []
    for st in analysis.statuses:
        v = st.vehicle
        bounds.append((v.latitude, v.longitude))
        in_pair = v.vehicle_id in pair
        excluded = v.vehicle_id not in used_ids
        color = COLORS["amber"] if in_pair else (COLORS["grey"] if excluded else COLORS["teal"])
        status = "Par mais próximo" if in_pair else ("Excluído (posição desatualizada)" if excluded else "Válido")
        acc = {True: "Sim", False: "Não", None: "—"}[v.accessible]
        popup = f"""
        <div style="font-family:Inter,sans-serif;font-size:12.5px;min-width:210px">
          <div style="font-size:15px;font-weight:700;margin-bottom:4px">🚌 {html.escape(v.vehicle_id)}
            <span style="font-size:10px;background:#eee;padding:1px 5px;border-radius:6px">{tag}</span></div>
          <b>Linha:</b> {html.escape(line_label)}<br>
          <b>Sentido:</b> {html.escape(direction_label)}<br>
          <b>Posição capturada:</b> {fmt_local(v.position_time_utc, True)} ({fmt_age(st.age_s)})<br>
          <b>Acessível:</b> {acc}<br>
          <b>Situação:</b> {status}
        </div>"""
        folium.CircleMarker(
            location=(v.latitude, v.longitude),
            radius=11 if in_pair else 7,
            color="#FFFFFF" if in_pair else color,
            weight=3 if in_pair else 1.5,
            fill=True,
            fill_color=color,
            fill_opacity=0.95 if not excluded else 0.5,
            tooltip=f"{v.vehicle_id} · {status}",
            popup=folium.Popup(popup, max_width=300),
        ).add_to(fmap)
        folium.Marker(
            location=(v.latitude, v.longitude),
            icon=folium.DivIcon(
                icon_size=(80, 18),
                icon_anchor=(-10, 22),
                html=f'<div style="font:600 11px Inter,sans-serif;color:{color};text-shadow:0 0 3px #000">{html.escape(v.vehicle_id)}</div>',
            ),
        ).add_to(fmap)

    if analysis.found:
        a = analysis.vehicle_by_id(analysis.dc.point_a.id)  # type: ignore[union-attr]
        b = analysis.vehicle_by_id(analysis.dc.point_b.id)  # type: ignore[union-attr]
        if a and b:
            # Segmento GEOMÉTRICO direto (não é rota rodoviária).
            folium.PolyLine(
                [(a.latitude, a.longitude), (b.latitude, b.longitude)],
                color=COLORS["amber"],
                weight=4,
                dash_array="8 6",
                tooltip=f"Distância em linha reta: {fmt_meters(analysis.dc.distance)}",
            ).add_to(fmap)
            mid = ((a.latitude + b.latitude) / 2, (a.longitude + b.longitude) / 2)
            folium.Marker(
                location=mid,
                icon=folium.DivIcon(
                    icon_size=(170, 26),
                    icon_anchor=(85, 34),
                    html=(
                        '<div style="background:#FBBF24;color:#0A1628;font:700 12px Inter,sans-serif;'
                        'padding:4px 8px;border-radius:8px;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,.5)">'
                        f"↔ {fmt_meters(analysis.dc.distance)} (linha reta)</div>"
                    ),
                ),
            ).add_to(fmap)

    if len(bounds) >= 2:
        fmap.fit_bounds(bounds, padding=(30, 30))
    elif bounds:
        fmap.location = bounds[0]
        fmap.options["zoom"] = 15
    return fmap
