"""Testes de correção dos algoritmos de par de pontos mais próximos."""

from __future__ import annotations

import math
import random

import pytest

from src.algorithms import (
    Point,
    closest_pair_brute_force,
    closest_pair_divide_conquer,
    euclidean,
    same_distance,
)
from src.algorithms.closest_pair import BASE_CASE_SIZE
from src.services.benchmark import generate_uniform_points, load_points_csv
from src.config import DATA_DIR

ALGOS = [closest_pair_brute_force, closest_pair_divide_conquer]


def pts(*coords) -> list[Point]:
    return [Point(float(x), float(y), f"P{i}") for i, (x, y) in enumerate(coords)]


def assert_consistent(result, points):
    """O par devolvido existe na entrada e a distância informada é a real."""
    assert result.found
    ids = {p.id for p in points}
    assert result.point_a.id in ids and result.point_b.id in ids
    assert result.point_a.id != result.point_b.id
    assert same_distance(euclidean(result.point_a, result.point_b), result.distance)


# ------------------------------------------------------------ casos de borda
@pytest.mark.parametrize("algo", ALGOS)
def test_zero_points(algo):
    r = algo([])
    assert not r.found and math.isinf(r.distance) and r.evaluations == 0


@pytest.mark.parametrize("algo", ALGOS)
def test_one_point(algo):
    r = algo(pts((3, 4)))
    assert not r.found and math.isinf(r.distance)


@pytest.mark.parametrize("algo", ALGOS)
def test_two_points(algo):
    p = pts((0, 0), (3, 4))
    r = algo(p)
    assert r.distance == pytest.approx(5.0)
    assert set(r.pair_ids) == {"P0", "P1"}
    assert r.evaluations == 1


@pytest.mark.parametrize("algo", ALGOS)
def test_seven_points_sample(algo):
    p = load_points_csv(DATA_DIR / "sample_7_points.csv")
    r = algo(p)
    assert set(r.pair_ids) == {"C", "D"}
    assert r.distance == pytest.approx(math.hypot(1.2, 0.8))


@pytest.mark.parametrize("algo", ALGOS)
def test_coincident_points(algo):
    p = pts((1, 1), (5, 5), (5, 5), (9, 2), (0, 7))
    r = algo(p)
    assert r.distance == 0.0
    assert set(r.pair_ids) == {"P1", "P2"}


@pytest.mark.parametrize("algo", ALGOS)
def test_all_points_identical(algo):
    p = pts(*[(2, 2)] * 10)
    r = algo(p)
    assert r.distance == 0.0
    assert_consistent(r, p)


@pytest.mark.parametrize("algo", ALGOS)
def test_same_x_coordinate(algo):
    # Todos na mesma vertical: a divisão por x fica "degenerada".
    p = pts((5, 0), (5, 10), (5, 3), (5, 21), (5, 3.5), (5, 40), (5, 7))
    r = algo(p)
    assert r.distance == pytest.approx(0.5)
    assert set(r.pair_ids) == {"P2", "P4"}


@pytest.mark.parametrize("algo", ALGOS)
def test_same_y_coordinate(algo):
    p = pts((0, 2), (10, 2), (3, 2), (21, 2), (3.25, 2), (40, 2), (7, 2))
    r = algo(p)
    assert r.distance == pytest.approx(0.25)
    assert set(r.pair_ids) == {"P2", "P4"}


@pytest.mark.parametrize("algo", ALGOS)
def test_collinear_diagonal(algo):
    p = pts(*[(i * 3, i * 3) for i in range(20)], (30.5, 30.5))
    r = algo(p)
    assert r.distance == pytest.approx(math.hypot(0.5, 0.5))


@pytest.mark.parametrize("algo", ALGOS)
def test_pair_crossing_division_line(algo):
    # Metade esquerda e direita bem espaçadas internamente; o par mais
    # próximo está um de cada lado da reta divisória (x ≈ 50).
    left = [(0, 0), (0, 100), (10, 50), (49.9, 50)]
    right = [(50.1, 50.05), (90, 0), (90, 100), (100, 50)]
    p = pts(*left, *right)
    r = algo(p)
    assert set(r.pair_ids) == {"P3", "P4"}
    assert r.distance == pytest.approx(math.hypot(0.2, 0.05))


def test_crossing_pair_found_in_strip():
    """Verifica, pelos eventos, que o par vencedor veio da faixa central."""
    p = load_points_csv(DATA_DIR / "sample_7_points.csv")
    r = closest_pair_divide_conquer(p, trace=True)
    improved = [e for e in r.events if e["type"] == "strip_compare" and e["improved"] and e["depth"] == 0]
    assert improved and {improved[-1]["a"], improved[-1]["b"]} == {"C", "D"}


def test_duplicate_x_with_unbalanced_split():
    # Muitos pontos com o mesmo x: a separação por índice evita perder pontos.
    p = pts(*[(0, i * 10) for i in range(9)], (0, 45.3), (1, 1000), (2, 2000))
    bf = closest_pair_brute_force(p)
    dc = closest_pair_divide_conquer(p)
    assert same_distance(bf.distance, dc.distance)
    assert dc.distance == pytest.approx(4.7)


def test_negative_and_large_coordinates():
    p = pts((-1e6, -1e6), (1e6, 1e6), (333_000.5, 7_390_000.25), (333_001.5, 7_390_000.25), (-5, 3))
    assert closest_pair_divide_conquer(p).distance == pytest.approx(1.0)


# ------------------------------------------------- comparação com força bruta
@pytest.mark.parametrize("seed", range(300))
def test_random_sets_match_brute_force(seed):
    rng = random.Random(seed)
    n = rng.randint(2, 120)
    # Grade inteira pequena força empates e coordenadas repetidas.
    if seed % 3 == 0:
        p = [Point(rng.randint(0, 15), rng.randint(0, 15), f"P{i}") for i in range(n)]
    else:
        p = [Point(rng.uniform(-1e4, 1e4), rng.uniform(-1e4, 1e4), f"P{i}") for i in range(n)]
    bf = closest_pair_brute_force(p)
    dc = closest_pair_divide_conquer(p)
    assert same_distance(bf.distance, dc.distance), (seed, bf.distance, dc.distance)
    assert_consistent(dc, p)


@pytest.mark.parametrize("n", [500, 2000])
def test_medium_sets_match_brute_force(n):
    p = generate_uniform_points(n, seed=n)
    bf = closest_pair_brute_force(p)
    dc = closest_pair_divide_conquer(p)
    assert same_distance(bf.distance, dc.distance)
    # A D&C deve avaliar MUITO menos distâncias que n(n-1)/2.
    assert bf.evaluations == n * (n - 1) // 2
    assert dc.evaluations < bf.evaluations / 10


def test_large_set_runs_and_scales():
    """Conjunto grande (benchmarking): D&C termina e as avaliações crescem ~ n log n."""
    n = 50_000
    p = generate_uniform_points(n, seed=7)
    dc = closest_pair_divide_conquer(p)
    assert_consistent(dc, p)
    assert dc.evaluations < 10 * n * math.log2(n)


def test_input_not_mutated():
    p = pts((5, 1), (1, 5), (3, 3), (9, 9), (0, 0))
    snapshot = list(p)
    closest_pair_divide_conquer(p)
    closest_pair_brute_force(p)
    assert p == snapshot


# ------------------------------------------------------- eventos (didático)
def test_trace_events_structure():
    p = load_points_csv(DATA_DIR / "sample_7_points.csv")
    r = closest_pair_divide_conquer(p, trace=True)
    types = [e["type"] for e in r.events]
    assert types[0] == "start" and types[1] == "sorted" and types[-1] == "result"
    assert "divide" in types and "base_case" in types and "strip" in types
    # Casos-base têm no máximo BASE_CASE_SIZE pontos.
    assert all(len(e["ids"]) <= BASE_CASE_SIZE for e in r.events if e["type"] == "base_case")
    # O evento final reflete o resultado devolvido.
    assert r.events[-1]["best"]["distance"] == pytest.approx(r.distance)
    # Ordenação por y registrada uma única vez (sem reordenar na recursão).
    assert types.count("sorted") == 1


def test_trace_disabled_has_no_events():
    r = closest_pair_divide_conquer(generate_uniform_points(50))
    assert r.events == []
