"""Testes de geoprocessamento, análise, persistência e modo demonstração."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.config import build_base_url
from src.geo.coordinates import (
    geodesic_distance_m,
    is_in_utm_zone_23,
    latlon_to_utm,
    utm_to_latlon,
    vehicles_to_points,
)
from src.models import PositionsSnapshot, VehiclePosition
from src.services.analysis import analyze_snapshot, proximity_timeline
from src.services.demo_data import SCENARIOS, generate_demo_snapshot
from src.storage.database import SnapshotRepository

NOW = datetime(2026, 11, 1, 15, 0, tzinfo=timezone.utc)


def v(vid, lat, lon, age_s=10):
    return VehiclePosition(vid, lat, lon, NOW - timedelta(seconds=age_s), True)


# ------------------------------------------------------------------- geo
def test_projection_roundtrip():
    lat, lon = -23.5614, -46.6559
    x, y = latlon_to_utm(lat, lon)
    assert 300_000 < x < 360_000 and 7_370_000 < y < 7_420_000  # faixa esperada p/ SP
    lat2, lon2 = utm_to_latlon(x, y)
    assert lat2 == pytest.approx(lat, abs=1e-9) and lon2 == pytest.approx(lon, abs=1e-9)


@pytest.mark.parametrize(
    "a,b",
    [
        ((-23.5614, -46.6559), (-23.5620, -46.6550)),  # ~110 m
        ((-23.5505, -46.6333), (-23.5874, -46.6576)),  # ~4.7 km
        ((-23.4800, -46.8000), (-23.7000, -46.4000)),  # ~47 km
    ],
)
def test_projected_distance_matches_geodesic(a, b):
    xa, ya = latlon_to_utm(*a)
    xb, yb = latlon_to_utm(*b)
    planar = ((xa - xb) ** 2 + (ya - yb) ** 2) ** 0.5
    geo = geodesic_distance_m(*a, *b)
    assert abs(planar - geo) / geo < 5e-4  # erro relativo < 0,05 %


def test_sao_paulo_inside_zone_23():
    assert is_in_utm_zone_23(-46.83) and is_in_utm_zone_23(-46.36)


def test_vehicles_to_points_keeps_ids():
    p = vehicles_to_points([v("A", -23.56, -46.65), v("B", -23.57, -46.66)])
    assert [q.id for q in p] == ["A", "B"]


def test_build_base_url():
    assert build_base_url("https://x.com/v2.1", "v9") == "https://x.com/v2.1"
    assert build_base_url("https://x.com/", "v2.1") == "https://x.com/v2.1"


# --------------------------------------------------------------- análise
def test_analysis_excludes_stale_and_matches_bruteforce():
    snap = PositionsSnapshot(
        1,
        NOW,
        "12:00",
        [
            v("A", -23.5614, -46.6559),
            v("B", -23.5616, -46.6560),  # muito próximo de A
            v("C", -23.5700, -46.6700),
            v("D", -23.5615, -46.6559, age_s=900),  # desatualizado e ainda mais próximo de A
        ],
    )
    an = analyze_snapshot(snap, stale_threshold_s=180, exclude_stale=True)
    assert an.stale_count == 1 and len(an.used) == 3
    assert set(an.dc.pair_ids) == {"A", "B"}
    assert an.results_match
    assert an.geodesic_m == pytest.approx(an.dc.distance, rel=1e-3)

    an2 = analyze_snapshot(snap, stale_threshold_s=180, exclude_stale=False)
    assert set(an2.dc.pair_ids) == {"A", "D"}


def test_analysis_with_insufficient_vehicles():
    an = analyze_snapshot(PositionsSnapshot(1, NOW, None, [v("A", -23.56, -46.65)]))
    assert not an.found and any("Menos de dois" in w for w in an.warnings)


# ----------------------------------------------------------- persistência
def test_repository_deduplicates_and_exports():
    repo = SnapshotRepository(":memory:")
    snap = generate_demo_snapshot("corridor", 0)
    cid, created = repo.save_snapshot(snap, "DEMO-01-10", 1, "x")
    assert created
    cid2, created2 = repo.save_snapshot(snap, "DEMO-01-10", 1, "x")
    assert cid2 == cid and not created2
    repo.save_snapshot(generate_demo_snapshot("corridor", 1), "DEMO-01-10", 1, "x")
    df = repo.export_dataframe(source="demo")
    assert len(df) == 14 and set(df["source"]) == {"demo"}
    assert {"collected_at_utc", "position_time_utc", "vehicle_id"} <= set(df.columns)


def test_repository_keeps_distinct_collection_times_with_same_positions():
    repo = SnapshotRepository(":memory:")
    first = generate_demo_snapshot("cluster", 0)
    second = PositionsSnapshot(
        first.line_code,
        first.collected_at_utc + timedelta(minutes=1),
        first.api_reference_time,
        first.vehicles,
        source="demo",
    )
    id1, _ = repo.save_snapshot(first)
    id2, created = repo.save_snapshot(second)
    assert created and id1 != id2
    assert len(repo.list_collections("demo", first.line_code)) == 2


def test_timeline_detects_consecutive_pairs():
    repo = SnapshotRepository(":memory:")
    for k in range(25):
        repo.save_snapshot(generate_demo_snapshot("cluster", k), "DEMO-03-10", 1, "x")
    tl = proximity_timeline(repo, "demo", SCENARIOS["cluster"].line.code, threshold_m=200)
    assert len(tl) == 25
    assert tl["below_threshold"].all()
    assert tl["consecutive"].max() >= 2


# -------------------------------------------------------- demonstração
def test_demo_is_reproducible_and_marked():
    a = generate_demo_snapshot("random", 5)
    b = generate_demo_snapshot("random", 5)
    assert [(x.vehicle_id, x.latitude, x.longitude) for x in a.vehicles] == [
        (x.vehicle_id, x.latitude, x.longitude) for x in b.vehicles
    ]
    assert a.source == "demo" and all(x.vehicle_id.startswith("SIM-") for x in a.vehicles)
    assert all(s.line.code < 0 for s in SCENARIOS.values())


def test_demo_corridor_buses_approach():
    def dist_45(step):
        an = analyze_snapshot(generate_demo_snapshot("corridor", step))
        pts = {p.id: p for p in vehicles_to_points(an.used)}
        a, b = pts["SIM-04"], pts["SIM-05"]
        return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5

    assert dist_45(0) > 1000 and dist_45(11) < 300


def test_demo_coincident_has_zero_distance_and_stale_vehicle():
    an = analyze_snapshot(generate_demo_snapshot("coincident", 3), stale_threshold_s=180)
    assert an.dc.distance == 0.0 and set(an.dc.pair_ids) == {"SIM-03", "SIM-04"}
    assert an.stale_count == 1
