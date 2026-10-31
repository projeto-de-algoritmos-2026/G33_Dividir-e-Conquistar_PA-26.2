"""Integração dos algoritmos com os dados de veículos.

Fluxo de uma análise:
    PositionsSnapshot → filtra posições desatualizadas → projeta para UTM 23S
    → divisão e conquista (resultado oficial) + força bruta (conferência)
    → distância geodésica (validação da projeção).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import pandas as pd

from src.algorithms import (
    ClosestPairResult,
    closest_pair_brute_force,
    closest_pair_divide_conquer,
    same_distance,
)
from src.api.sptrans_client import parse_utc_timestamp
from src.geo.coordinates import geodesic_distance_m, vehicles_to_points
from src.models import PositionsSnapshot, VehiclePosition

# Tolerância para horários de captura "no futuro" (relógios dessincronizados).
FUTURE_TOLERANCE_S = 120

STATUS_CANDIDATE = "Candidato a agrupamento"
STATUS_NORMAL = "Acima do limite"


@dataclass
class VehicleStatus:
    vehicle: VehiclePosition
    age_s: float | None  # idade da posição em relação ao horário da coleta
    stale: bool
    reason: str = ""


@dataclass
class ProximityAnalysis:
    snapshot: PositionsSnapshot
    statuses: list[VehicleStatus]
    used: list[VehiclePosition]
    dc: ClosestPairResult
    bf: ClosestPairResult
    geodesic_m: float | None
    warnings: list[str] = field(default_factory=list)

    @property
    def found(self) -> bool:
        return self.dc.found

    @property
    def results_match(self) -> bool:
        return same_distance(self.dc.distance, self.bf.distance, rel_tol=1e-9, abs_tol=1e-6)

    @property
    def stale_count(self) -> int:
        return sum(1 for s in self.statuses if s.stale)

    def vehicle_by_id(self, vid: str) -> VehiclePosition | None:
        return next((v for v in self.snapshot.vehicles if v.vehicle_id == vid), None)


def classify_vehicle(v: VehiclePosition, collected_at: datetime, stale_threshold_s: int) -> VehicleStatus:
    if v.position_time_utc is None:
        return VehicleStatus(v, None, True, "sem horário de captura")
    age = (collected_at - v.position_time_utc).total_seconds()
    if age < -FUTURE_TOLERANCE_S:
        return VehicleStatus(v, age, True, "horário de captura no futuro")
    if age > stale_threshold_s:
        return VehicleStatus(v, age, True, f"posição com {age / 60:.1f} min")
    return VehicleStatus(v, age, False)


def analyze_snapshot(
    snapshot: PositionsSnapshot, stale_threshold_s: int = 180, exclude_stale: bool = True
) -> ProximityAnalysis:
    statuses = [classify_vehicle(v, snapshot.collected_at_utc, stale_threshold_s) for v in snapshot.vehicles]
    used = [s.vehicle for s in statuses if not (exclude_stale and s.stale)]

    points = vehicles_to_points(used)
    dc = closest_pair_divide_conquer(points)
    bf = closest_pair_brute_force(points)

    warnings: list[str] = []
    stale = [s for s in statuses if s.stale]
    if stale:
        action = "excluídas da análise" if exclude_stale else "incluídas na análise"
        warnings.append(f"{len(stale)} posição(ões) desatualizada(s) ou sem horário — {action}.")
    if snapshot.discarded:
        warnings.append(f"{snapshot.discarded} registro(s) descartado(s) por dados inválidos ou duplicados.")
    if len(used) < 2:
        warnings.append("Menos de dois veículos válidos: não há par para analisar.")

    geodesic = None
    if dc.found:
        a = next(v for v in used if v.vehicle_id == dc.point_a.id)  # type: ignore[union-attr]
        b = next(v for v in used if v.vehicle_id == dc.point_b.id)  # type: ignore[union-attr]
        geodesic = geodesic_distance_m(a.latitude, a.longitude, b.latitude, b.longitude)
        # Posições capturadas em instantes diferentes distorcem a distância real.
        if a.position_time_utc and b.position_time_utc:
            gap = abs((a.position_time_utc - b.position_time_utc).total_seconds())
            if gap > 60:
                warnings.append(
                    f"As posições do par foram capturadas com {gap:.0f} s de diferença; "
                    "a distância pode não representar um mesmo instante."
                )

    return ProximityAnalysis(snapshot, statuses, used, dc, bf, geodesic, warnings)


# ---------------------------------------------------------------- snapshots
def positions_df_to_snapshot(collection: pd.Series, positions: pd.DataFrame) -> PositionsSnapshot:
    """Reconstrói um PositionsSnapshot a partir das tabelas do SQLite."""
    vehicles = [
        VehiclePosition(
            vehicle_id=str(r.vehicle_id),
            latitude=float(r.latitude),
            longitude=float(r.longitude),
            position_time_utc=parse_utc_timestamp(r.position_time_utc),
            accessible=None if pd.isna(r.accessible) else bool(r.accessible),
        )
        for r in positions.itertuples()
    ]
    collected = parse_utc_timestamp(collection["collected_at_utc"]) or datetime.now(timezone.utc)
    return PositionsSnapshot(
        line_code=int(collection["line_code"]),
        collected_at_utc=collected,
        api_reference_time=collection.get("api_reference_time"),
        vehicles=vehicles,
        source=str(collection["source"]),
    )


def proximity_timeline(
    repo,
    source: str,
    line_code: int,
    threshold_m: float,
    stale_threshold_s: int = 180,
    exclude_stale: bool = True,
) -> pd.DataFrame:
    """Executa a divisão e conquista em cada coleta e monta a série temporal.

    ``consecutive`` conta quantas coletas seguidas o MESMO par permaneceu
    abaixo do limite. Isso é um indício, não prova, de agrupamento.
    """
    cols = repo.list_collections(source=source, line_code=line_code)
    rows = []
    prev_pair: tuple[str, str] | None = None
    run = 0
    for _, c in cols.iterrows():
        snap = positions_df_to_snapshot(c, repo.get_positions(int(c["id"])))
        an = analyze_snapshot(snap, stale_threshold_s, exclude_stale)
        pair = tuple(sorted(an.dc.pair_ids)) if an.found else None  # type: ignore[arg-type]
        below = an.found and an.dc.distance < threshold_m
        if below and pair == prev_pair:
            run += 1
        elif below:
            run = 1
        else:
            run = 0
        prev_pair = pair if below else None
        rows.append(
            {
                "collection_id": int(c["id"]),
                "collected_at_utc": snap.collected_at_utc,
                "valid_vehicles": len(an.used),
                "stale_vehicles": an.stale_count,
                "vehicle_a": pair[0] if pair else None,
                "vehicle_b": pair[1] if pair else None,
                "min_distance_m": an.dc.distance if an.found else None,
                "below_threshold": bool(below),
                "consecutive": run,
                "status": STATUS_CANDIDATE if below else (STATUS_NORMAL if an.found else "Sem par"),
            }
        )
    return pd.DataFrame(rows)
