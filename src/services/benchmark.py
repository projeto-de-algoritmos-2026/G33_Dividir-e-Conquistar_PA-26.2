"""Benchmark experimental: força bruta × divisão e conquista.

Metodologia (todas as medições são reais, feitas na máquina do usuário):
    1. Para cada tamanho n, gera-se UM conjunto de pontos uniformes em um
       quadrado de 10 km × 10 km com semente fixa (seed + n) → reprodutível.
    2. Ambos os algoritmos recebem exatamente os mesmos pontos.
    3. Uma execução de aquecimento (descartada) por algoritmo.
    4. ``repeats`` execuções cronometradas com ``time.perf_counter`` dentro da
       própria função (excluindo geração de dados e cópia da lista).
       O coletor de lixo é desativado durante as medições.
    5. Reporta-se a MEDIANA (robusta a ruído), além de mínimo e desvio-padrão.
    6. A força bruta só é executada até ``bf_max_n`` para não travar a tela.
"""

from __future__ import annotations

import csv
import gc
import math
import random
import statistics
from collections.abc import Callable, Sequence
from pathlib import Path

import pandas as pd

from src.algorithms import (
    ClosestPairResult,
    Point,
    closest_pair_brute_force,
    closest_pair_divide_conquer,
    same_distance,
)

ALGORITHMS: dict[str, Callable[[Sequence[Point]], ClosestPairResult]] = {
    "Força bruta": closest_pair_brute_force,
    "Divisão e conquista": closest_pair_divide_conquer,
}


def generate_uniform_points(n: int, seed: int = 42, side_m: float = 10_000.0) -> list[Point]:
    rng = random.Random(seed)
    return [Point(rng.uniform(0, side_m), rng.uniform(0, side_m), f"P{i}") for i in range(n)]


def load_points_csv(path: Path | str) -> list[Point]:
    """CSV com colunas id,x,y."""
    with open(path, newline="", encoding="utf-8") as fh:
        return [Point(float(r["x"]), float(r["y"]), r["id"].strip()) for r in csv.DictReader(fh)]


def measure(func: Callable[[Sequence[Point]], ClosestPairResult], points: Sequence[Point], repeats: int = 5) -> dict:
    func(points)  # aquecimento
    times: list[float] = []
    result: ClosestPairResult | None = None
    gc_was_enabled = gc.isenabled()
    gc.disable()
    try:
        for _ in range(max(1, repeats)):
            result = func(points)
            times.append(result.elapsed_s)
    finally:
        if gc_was_enabled:
            gc.enable()
    assert result is not None
    return {
        "median_s": statistics.median(times),
        "min_s": min(times),
        "stdev_s": statistics.stdev(times) if len(times) > 1 else 0.0,
        "evaluations": result.evaluations,
        "distance": result.distance,
        "result": result,
        "times": times,
    }


def compare_on(points: Sequence[Point], repeats: int = 5) -> dict:
    """Executa os dois algoritmos sobre os mesmos pontos."""
    bf = measure(closest_pair_brute_force, points, repeats)
    dc = measure(closest_pair_divide_conquer, points, repeats)
    return {
        "bf": bf,
        "dc": dc,
        "match": same_distance(bf["distance"], dc["distance"]),
    }


def run_benchmark(
    sizes: Sequence[int],
    repeats: int = 5,
    seed: int = 42,
    bf_max_n: int = 3000,
    progress: Callable[[float, str], None] | None = None,
) -> pd.DataFrame:
    rows = []
    total = len(sizes)
    for k, n in enumerate(sizes):
        pts = generate_uniform_points(n, seed + n)
        dc = measure(closest_pair_divide_conquer, pts, repeats)
        bf = measure(closest_pair_brute_force, pts, repeats) if n <= bf_max_n else None
        for name, m in (("Divisão e conquista", dc), ("Força bruta", bf)):
            if m is None:
                continue
            rows.append(
                {
                    "n": n,
                    "algoritmo": name,
                    "mediana_ms": m["median_s"] * 1000,
                    "min_ms": m["min_s"] * 1000,
                    "desvio_ms": m["stdev_s"] * 1000,
                    "avaliacoes": m["evaluations"],
                    "distancia": m["distance"],
                    "repeticoes": repeats,
                }
            )
        if bf is not None and not same_distance(bf["distance"], dc["distance"]):
            raise AssertionError(f"Resultados divergentes para n={n}")
        if progress:
            progress((k + 1) / total, f"n = {n} concluído")
    return pd.DataFrame(rows)


def reference_curves(sizes: Sequence[int]) -> pd.DataFrame:
    """Curvas teóricas n(n−1)/2 e n·log2(n) para comparação com as avaliações."""
    return pd.DataFrame(
        {
            "n": list(sizes),
            "n(n-1)/2": [n * (n - 1) / 2 for n in sizes],
            "n log2 n": [n * math.log2(n) if n > 1 else 0 for n in sizes],
        }
    )
