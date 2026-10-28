"""Algoritmo B — Par de Pontos Mais Próximos por Divisão e Conquista.

Visão geral (algoritmo clássico de Shamos & Hoey, 1975; CLRS §33.4):

1. PRÉ-PROCESSAMENTO (uma única vez, O(n log n))
   - ``px``: pontos ordenados por x.
   - ``py``: os mesmos pontos ordenados por y (guardamos índices de ``px``).

2. DIVISÃO
   - Divide ``px[lo:hi]`` ao meio: esquerda = ``[lo, mid)``, direita = ``[mid, hi)``.
   - A reta vertical ``x = mid_x`` separa as metades.
   - ``py`` é particionado em ``py_esq`` e ``py_dir`` em O(n), PRESERVANDO a
     ordem por y. Assim nunca reordenamos por y dentro da recursão.

3. CONQUISTA
   - Resolve recursivamente cada metade → δ_esq e δ_dir.
   - Caso-base: com até 3 pontos, compara todos os pares (força bruta local).

4. COMBINAÇÃO
   - δ = min(δ_esq, δ_dir).
   - Um par que cruza a divisão só pode ser melhor que δ se ambos os pontos
     estiverem na FAIXA CENTRAL ``|x − mid_x| < δ``.
   - Percorre a faixa em ordem de y; cada ponto só precisa ser comparado com
     os seguintes enquanto ``Δy < δ`` (no máximo 7 vizinhos, pelo argumento de
     empacotamento em um retângulo δ × 2δ).

Recorrência: T(n) = 2·T(n/2) + O(n)  ⇒  T(n) = O(n log n) (Teorema Mestre, caso 2).

Por que usar ÍNDICES de ``px`` em ``py``?
    Separar ``py`` em esquerda/direita comparando apenas ``x < mid_x`` falha
    quando há vários pontos com o mesmo x (duplicatas). Como a esquerda é
    exatamente o intervalo de índices ``[lo, mid)`` de ``px``, testar
    ``indice < mid`` é exato e continua O(1) por ponto.
"""

from __future__ import annotations

import math
import time
from collections.abc import Sequence
from typing import Any

from .common import ClosestPairResult, Point, euclidean

# Melhor par parcial: (índice_a, índice_b, distância), índices referentes a px.
_Best = tuple[int, int, float]

BASE_CASE_SIZE = 3


class _DivideAndConquerSolver:
    """Encapsula o estado da execução (ordenações, contador e eventos)."""

    def __init__(self, points: Sequence[Point], events: list[dict[str, Any]] | None):
        self.events = events
        self.evaluations = 0
        n = len(points)

        # Passo 1 — ordenação inicial por x (desempate por y para determinismo).
        self.px: list[Point] = sorted(points, key=lambda p: (p.x, p.y))
        # Passo 1' — ordenação por y feita UMA vez; guarda índices de px.
        self.py: list[int] = sorted(range(n), key=lambda i: (self.px[i].y, self.px[i].x))

        self._emit(
            "sorted",
            order_x=[p.id for p in self.px],
            order_y=[self.px[i].id for i in self.py],
        )

    # ------------------------------------------------------------------ utils
    def _emit(self, kind: str, **data: Any) -> None:
        """Registra um evento da execução real (usado pelo modo didático)."""
        if self.events is not None:
            data["type"] = kind
            self.events.append(data)

    def _ids(self, indices) -> list[str]:
        return [self.px[i].id for i in indices]

    def _dist(self, i: int, j: int) -> float:
        self.evaluations += 1
        return euclidean(self.px[i], self.px[j])

    def _pair_info(self, best: _Best) -> dict[str, Any]:
        i, j, d = best
        return {"a": self.px[i].id, "b": self.px[j].id, "distance": d}

    # -------------------------------------------------------------- algoritmo
    def solve(self) -> _Best:
        return self._solve(0, len(self.px), self.py, depth=0)

    def _base_case(self, lo: int, hi: int, depth: int) -> _Best:
        """Até 3 pontos: compara todos os pares (no máximo 3 comparações)."""
        best: _Best = (-1, -1, math.inf)
        compared = []
        for i in range(lo, hi - 1):
            for j in range(i + 1, hi):
                d = self._dist(i, j)
                compared.append({"a": self.px[i].id, "b": self.px[j].id, "distance": d})
                if d < best[2]:
                    best = (i, j, d)
        self._emit(
            "base_case",
            depth=depth,
            ids=self._ids(range(lo, hi)),
            compared=compared,
            best=self._pair_info(best),
        )
        return best

    def _solve(self, lo: int, hi: int, py: list[int], depth: int) -> _Best:
        n = hi - lo
        if n <= BASE_CASE_SIZE:
            return self._base_case(lo, hi, depth)

        # ---- DIVISÃO -------------------------------------------------------
        mid = (lo + hi) // 2
        # Reta divisória entre o último ponto da esquerda e o primeiro da direita.
        mid_x = (self.px[mid - 1].x + self.px[mid].x) / 2.0

        # Particiona py em O(n) mantendo a ordem por y (sem nova ordenação!).
        py_left = [i for i in py if i < mid]
        py_right = [i for i in py if i >= mid]

        self._emit(
            "divide",
            depth=depth,
            ids=self._ids(range(lo, hi)),
            left=self._ids(range(lo, mid)),
            right=self._ids(range(mid, hi)),
            mid_x=mid_x,
        )

        # ---- CONQUISTA -----------------------------------------------------
        best_left = self._solve(lo, mid, py_left, depth + 1)
        best_right = self._solve(mid, hi, py_right, depth + 1)

        # ---- COMBINAÇÃO ----------------------------------------------------
        best = best_left if best_left[2] <= best_right[2] else best_right
        delta = best[2]
        self._emit(
            "combine",
            depth=depth,
            ids=self._ids(range(lo, hi)),
            left_best=self._pair_info(best_left),
            right_best=self._pair_info(best_right),
            delta=delta,
            mid_x=mid_x,
        )

        # Faixa central: pontos a menos de δ da reta divisória, já em ordem de y.
        strip = [i for i in py if abs(self.px[i].x - mid_x) < delta]
        self._emit(
            "strip",
            depth=depth,
            ids=self._ids(range(lo, hi)),
            strip=self._ids(strip),
            mid_x=mid_x,
            delta=delta,
        )

        # Para cada ponto da faixa, compara apenas com os próximos em y
        # enquanto a diferença vertical for menor que a melhor distância atual.
        m = len(strip)
        for k in range(m):
            i = strip[k]
            yi = self.px[i].y
            t = k + 1
            while t < m and self.px[strip[t]].y - yi < best[2]:
                j = strip[t]
                d = self._dist(i, j)
                improved = d < best[2]
                if improved:
                    best = (i, j, d)
                self._emit(
                    "strip_compare",
                    depth=depth,
                    a=self.px[i].id,
                    b=self.px[j].id,
                    distance=d,
                    improved=improved,
                    best=self._pair_info(best),
                    mid_x=mid_x,
                    delta=delta,
                )
                t += 1

        self._emit(
            "return",
            depth=depth,
            ids=self._ids(range(lo, hi)),
            best=self._pair_info(best),
        )
        return best


def closest_pair_divide_conquer(points: Sequence[Point], trace: bool = False) -> ClosestPairResult:
    """Encontra o par mais próximo em O(n log n).

    Args:
        points: pontos no plano (coordenadas métricas).
        trace: se ``True``, registra eventos de cada etapa em ``result.events``
            (usado pela página didática). Com ``trace=True`` o tempo medido
            inclui o custo dos registros e NÃO deve ser usado em benchmarks.
    """
    pts = list(points)
    n = len(pts)
    events: list[dict[str, Any]] | None = [] if trace else None

    if events is not None:
        events.append({"type": "start", "ids": [p.id for p in pts]})

    start = time.perf_counter()
    if n < 2:
        elapsed = time.perf_counter() - start
        if events is not None:
            events.append({"type": "result", "best": None})
        return ClosestPairResult("Divisão e conquista", None, None, math.inf, 0, elapsed, n, events or [])

    solver = _DivideAndConquerSolver(pts, events)
    i, j, d = solver.solve()
    elapsed = time.perf_counter() - start

    a, b = solver.px[i], solver.px[j]
    if events is not None:
        events.append({"type": "result", "best": {"a": a.id, "b": b.id, "distance": d}})

    return ClosestPairResult(
        algorithm="Divisão e conquista",
        point_a=a,
        point_b=b,
        distance=d,
        evaluations=solver.evaluations,
        elapsed_s=elapsed,
        n=n,
        events=events or [],
    )
