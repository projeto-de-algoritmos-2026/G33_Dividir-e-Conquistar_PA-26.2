"""Algoritmos de Par de Pontos Mais Próximos (implementação própria)."""

from .brute_force import closest_pair_brute_force
from .closest_pair import closest_pair_divide_conquer
from .common import ClosestPairResult, Point, euclidean, same_distance

__all__ = [
    "ClosestPairResult",
    "Point",
    "closest_pair_brute_force",
    "closest_pair_divide_conquer",
    "euclidean",
    "same_distance",
]
