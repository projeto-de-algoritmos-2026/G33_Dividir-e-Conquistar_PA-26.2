"""Algoritmo A — Força Bruta para o Par de Pontos Mais Próximos.

Compara todos os pares distintos {i, j}, com i < j.

    Número de comparações: C(n, 2) = n(n-1)/2  →  Θ(n²) no tempo
    Memória extra: O(1)

É a referência de correção usada nos testes e no benchmark.
"""

from __future__ import annotations

import math
import time
from collections.abc import Sequence

from .common import ClosestPairResult, Point, euclidean


def brute_force_core(points: Sequence[Point]) -> tuple[Point | None, Point | None, float, int]:
    """Núcleo sem medição de tempo: devolve (a, b, distância, avaliações).

    Em caso de empate, mantém o primeiro par encontrado (comparação estrita ``<``).
    """
    best_a: Point | None = None
    best_b: Point | None = None
    best_d = math.inf
    evaluations = 0
    n = len(points)
    for i in range(n - 1):
        pi = points[i]
        for j in range(i + 1, n):
            d = euclidean(pi, points[j])
            evaluations += 1
            if d < best_d:
                best_d, best_a, best_b = d, pi, points[j]
    return best_a, best_b, best_d, evaluations


def closest_pair_brute_force(points: Sequence[Point]) -> ClosestPairResult:
    """Executa a força bruta e mede o tempo de execução."""
    pts = list(points)
    start = time.perf_counter()
    a, b, d, evals = brute_force_core(pts)
    elapsed = time.perf_counter() - start
    return ClosestPairResult(
        algorithm="Força bruta",
        point_a=a,
        point_b=b,
        distance=d,
        evaluations=evals,
        elapsed_s=elapsed,
        n=len(pts),
    )
