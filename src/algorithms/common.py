"""Tipos compartilhados pelos algoritmos de Par de Pontos Mais Próximos.

Os algoritmos trabalham exclusivamente sobre pontos em um PLANO CARTESIANO
(coordenadas x, y em metros, já projetadas). Eles não sabem nada sobre
latitude/longitude, API ou ônibus — isso mantém o núcleo algorítmico puro,
testável e fácil de explicar.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Point:
    """Ponto no plano. ``id`` identifica o objeto (ex.: prefixo do ônibus)."""

    x: float
    y: float
    id: str


@dataclass(slots=True)
class ClosestPairResult:
    """Resultado de uma execução de algoritmo de par mais próximo.

    Para entradas com menos de dois pontos, ``point_a``/``point_b`` são ``None``
    e ``distance`` é ``math.inf``.
    """

    algorithm: str
    point_a: Point | None
    point_b: Point | None
    distance: float
    evaluations: int  # quantidade de cálculos de distância realizados
    elapsed_s: float  # tempo de execução medido com time.perf_counter
    n: int
    events: list[dict[str, Any]] = field(default_factory=list)

    @property
    def found(self) -> bool:
        return self.point_a is not None and self.point_b is not None

    @property
    def pair_ids(self) -> tuple[str, str] | None:
        if not self.found:
            return None
        return (self.point_a.id, self.point_b.id)  # type: ignore[union-attr]


def euclidean(a: Point, b: Point) -> float:
    """Distância euclidiana no plano projetado."""
    return math.hypot(a.x - b.x, a.y - b.y)


def same_distance(d1: float, d2: float, rel_tol: float = 1e-9, abs_tol: float = 1e-9) -> bool:
    """Compara distâncias com tolerância numérica (inclui o caso inf == inf)."""
    if math.isinf(d1) or math.isinf(d2):
        return d1 == d2
    return math.isclose(d1, d2, rel_tol=rel_tol, abs_tol=abs_tol)
