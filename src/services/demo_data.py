"""Modo Demonstração: dados SINTÉTICOS e reproduzíveis (sem acesso à API).

Todos os veículos têm prefixo ``SIM-`` e as linhas têm código negativo e
letreiro ``DEMO-xx``, para nunca se confundirem com dados reais da SPTrans.
As posições dependem apenas do passo de simulação ``k`` (k × 60 s), então a
mesma configuração sempre gera os mesmos snapshots.

Os trajetos são polilinhas aproximadas entre pontos conhecidos da cidade; não
representam o itinerário oficial de nenhuma linha.
"""

from __future__ import annotations

import math
import random
from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from src.geo.coordinates import latlon_to_utm, utm_to_latlon
from src.models import BusLine, PositionsSnapshot, VehiclePosition

STEP_SECONDS = 60
# Instante-base fixo (08:00 em São Paulo = 11:00 UTC) para reprodutibilidade.
BASE_TIME_UTC = datetime(2026, 3, 2, 11, 0, 0, tzinfo=timezone.utc)

# Trajeto aproximado Paraíso → Av. Paulista → Consolação → Rebouças → Pinheiros.
ROUTE_WAYPOINTS = [
    (-23.5760, -46.6402),
    (-23.5712, -46.6448),
    (-23.5660, -46.6505),
    (-23.5614, -46.6559),
    (-23.5560, -46.6620),
    (-23.5588, -46.6690),
    (-23.5625, -46.6772),
    (-23.5668, -46.6862),
    (-23.5690, -46.6935),
    (-23.5732, -46.7010),
]
CENTER = (-23.5614, -46.6559)


class _Route:
    """Polilinha em coordenadas UTM com interpolação por comprimento de arco."""

    def __init__(self, waypoints):
        self.xy = [latlon_to_utm(lat, lon) for lat, lon in waypoints]
        self.cum = [0.0]
        for (x1, y1), (x2, y2) in zip(self.xy, self.xy[1:]):
            self.cum.append(self.cum[-1] + math.hypot(x2 - x1, y2 - y1))
        self.length = self.cum[-1]

    def at(self, s: float) -> tuple[float, float]:
        """Posição (lat, lon) a ``s`` metros do início.

        Sentido único: ao chegar ao fim do trajeto, o veículo inicia uma nova
        viagem a partir da origem (s mod comprimento).
        """
        s = s % self.length
        i = min(bisect_right(self.cum, s) - 1, len(self.xy) - 2)
        seg = self.cum[i + 1] - self.cum[i]
        t = 0 if seg == 0 else (s - self.cum[i]) / seg
        x = self.xy[i][0] + t * (self.xy[i + 1][0] - self.xy[i][0])
        y = self.xy[i][1] + t * (self.xy[i + 1][1] - self.xy[i][1])
        return utm_to_latlon(x, y)


_ROUTE: _Route | None = None


def _route() -> _Route:
    global _ROUTE
    if _ROUTE is None:
        _ROUTE = _Route(ROUTE_WAYPOINTS)
    return _ROUTE


@dataclass(frozen=True)
class DemoScenario:
    key: str
    line: BusLine
    description: str


def _demo_line(code: int, n: int, name: str) -> BusLine:
    return BusLine(
        code=code,
        circular=False,
        sign_prefix=f"DEMO-{n:02d}",
        sign_suffix=10,
        direction=1,
        main_terminal="Paraíso (simulado)",
        secondary_terminal=name,
        source="demo",
    )


SCENARIOS: dict[str, DemoScenario] = {
    s.key: s
    for s in [
        DemoScenario(
            "corridor",
            _demo_line(-101, 1, "Pinheiros (simulado)"),
            "7 ônibus no mesmo corredor; SIM-04 é mais rápido e alcança SIM-05 ao longo dos passos.",
        ),
        DemoScenario(
            "random",
            _demo_line(-102, 2, "Dispersão aleatória"),
            "7 ônibus em caminhada aleatória (semente fixa) ao redor da Av. Paulista.",
        ),
        DemoScenario(
            "cluster",
            _demo_line(-103, 3, "Agrupamento de três"),
            "Três ônibus seguem juntos no corredor; os demais estão espaçados.",
        ),
        DemoScenario(
            "coincident",
            _demo_line(-104, 4, "Coordenadas coincidentes"),
            "Dois ônibus parados exatamente no mesmo ponto (distância 0 m) e um com posição desatualizada.",
        ),
    ]
}


def _vehicle(vid: str, lat: float, lon: float, ts: datetime, accessible: bool = True) -> VehiclePosition:
    return VehiclePosition(vid, round(lat, 6), round(lon, 6), ts, accessible)


def generate_demo_snapshot(key: str, step: int) -> PositionsSnapshot:
    """Gera o snapshot simulado do cenário ``key`` no passo ``step``."""
    scenario = SCENARIOS[key]
    t = step * STEP_SECONDS
    collected = BASE_TIME_UTC + timedelta(seconds=t)
    route = _route()
    vehicles: list[VehiclePosition] = []
    # Pequeno atraso (0–40 s) entre a captura da posição e a coleta.
    lag = [5, 12, 20, 8, 30, 15, 40]

    if key == "corridor":
        starts = [i * 1050 for i in range(7)]
        speeds = [5.2, 5.2, 5.2, 6.4, 4.8, 5.2, 5.2]  # m/s — SIM-04 alcança SIM-05
        for i in range(7):
            lat, lon = route.at(starts[i] + speeds[i] * t)
            vehicles.append(_vehicle(f"SIM-{i + 1:02d}", lat, lon, collected - timedelta(seconds=lag[i]), i % 2 == 0))
    elif key == "cluster":
        starts = [0, 2600, 2690, 2790, 4300, 5500, 6600]
        speeds = [5.3] * 7
        for i in range(7):
            lat, lon = route.at(starts[i] + speeds[i] * t)
            vehicles.append(_vehicle(f"SIM-{i + 1:02d}", lat, lon, collected - timedelta(seconds=lag[i])))
    elif key == "random":
        rng = random.Random(2026)
        cx, cy = latlon_to_utm(*CENTER)
        pos = [(cx + rng.uniform(-3000, 3000), cy + rng.uniform(-3000, 3000)) for _ in range(7)]
        for _ in range(step):  # caminhada aleatória determinística
            pos = [(x + rng.gauss(0, 250), y + rng.gauss(0, 250)) for x, y in pos]
        for i, (x, y) in enumerate(pos):
            lat, lon = utm_to_latlon(x, y)
            vehicles.append(_vehicle(f"SIM-{i + 1:02d}", lat, lon, collected - timedelta(seconds=lag[i])))
    elif key == "coincident":
        starts = [0, 1500, 3600, 3600, 4700, 5900, 7000]
        speeds = [5.3, 5.3, 0.0, 0.0, 5.3, 5.3, 5.3]  # SIM-03 e SIM-04 parados no mesmo ponto
        for i in range(7):
            lat, lon = route.at(starts[i] + speeds[i] * t)
            # SIM-07 com posição 10 min atrasada → deve ser marcada como desatualizada.
            ts = collected - timedelta(seconds=600 if i == 6 else lag[i])
            vehicles.append(_vehicle(f"SIM-{i + 1:02d}", lat, lon, ts))
    else:  # pragma: no cover
        raise KeyError(key)

    local = collected - timedelta(hours=3)
    return PositionsSnapshot(
        line_code=scenario.line.code,
        collected_at_utc=collected,
        api_reference_time=local.strftime("%H:%M"),
        vehicles=vehicles,
        source="demo",
    )


def scenario_for_line_code(code: int) -> DemoScenario | None:
    return next((s for s in SCENARIOS.values() if s.line.code == code), None)
