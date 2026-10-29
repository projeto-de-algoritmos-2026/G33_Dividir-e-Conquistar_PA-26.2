"""Conversão de coordenadas geográficas para um plano métrico.

A API devolve latitude/longitude (graus, WGS84). Distâncias em graus NÃO são
distâncias em metros (1° de longitude encolhe com a latitude). Por isso
projetamos para SIRGAS 2000 / UTM zona 23S (EPSG:31983):

- A zona 23 cobre as longitudes de 48°W a 42°W (meridiano central 45°W).
  O município de São Paulo está entre ~46,83°W e ~46,36°W → dentro da zona.
- Distorção de escala UTM nessa região: fator k ≈ 0,9996–0,9998 (erro < 0,05 %),
  desprezível para distâncias entre ônibus (dezenas a milhares de metros).
- SIRGAS 2000 e WGS84 coincidem no nível de centímetros, então tratamos as
  coordenadas da API como compatíveis com o datum SIRGAS 2000.

A distância euclidiana no plano UTM aproxima a distância geodésica (linha reta
sobre o elipsoide). Ela NÃO é a distância rodoviária nem a distância ao longo
do itinerário da linha — estas seriam maiores ou iguais.
"""

from __future__ import annotations

from collections.abc import Iterable
from functools import lru_cache

from pyproj import Geod, Transformer

from src.algorithms.common import Point
from src.models import VehiclePosition

WGS84 = "EPSG:4326"
SIRGAS2000_UTM23S = "EPSG:31983"

# Caixa aproximada da Região Metropolitana de São Paulo (validação de dados).
SP_BOUNDS = {"lat_min": -24.10, "lat_max": -23.15, "lon_min": -47.25, "lon_max": -46.00}
# Faixa de validade da zona UTM 23S.
ZONE_23_LON_MIN, ZONE_23_LON_MAX = -48.0, -42.0

_GEOD = Geod(ellps="GRS80")


@lru_cache(maxsize=1)
def _to_utm() -> Transformer:
    # always_xy=True → ordem (lon, lat) / (x, y), evitando inversões de eixo.
    return Transformer.from_crs(WGS84, SIRGAS2000_UTM23S, always_xy=True)


@lru_cache(maxsize=1)
def _to_geo() -> Transformer:
    return Transformer.from_crs(SIRGAS2000_UTM23S, WGS84, always_xy=True)


def is_valid_lat_lon(lat: float | None, lon: float | None) -> bool:
    """Valida coordenada genérica (faixa geográfica e não nula)."""
    if lat is None or lon is None:
        return False
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return False
    if lat != lat or lon != lon:  # NaN
        return False
    if lat == 0.0 and lon == 0.0:  # "Null Island": GPS sem sinal
        return False
    return -90 <= lat <= 90 and -180 <= lon <= 180


def is_in_sao_paulo_region(lat: float, lon: float) -> bool:
    b = SP_BOUNDS
    return b["lat_min"] <= lat <= b["lat_max"] and b["lon_min"] <= lon <= b["lon_max"]


def is_in_utm_zone_23(lon: float) -> bool:
    return ZONE_23_LON_MIN <= lon <= ZONE_23_LON_MAX


def latlon_to_utm(lat: float, lon: float) -> tuple[float, float]:
    """(lat, lon) em graus → (x, y) em metros (EPSG:31983)."""
    x, y = _to_utm().transform(lon, lat)
    return float(x), float(y)


def utm_to_latlon(x: float, y: float) -> tuple[float, float]:
    """(x, y) em metros (EPSG:31983) → (lat, lon) em graus."""
    lon, lat = _to_geo().transform(x, y)
    return float(lat), float(lon)


def geodesic_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distância geodésica no elipsoide GRS80 (usada só para conferência)."""
    _, _, dist = _GEOD.inv(lon1, lat1, lon2, lat2)
    return float(dist)


def vehicles_to_points(vehicles: Iterable[VehiclePosition]) -> list[Point]:
    """Projeta posições de veículos para pontos cartesianos do algoritmo."""
    vehicles = list(vehicles)
    if not vehicles:
        return []
    lons = [v.longitude for v in vehicles]
    lats = [v.latitude for v in vehicles]
    xs, ys = _to_utm().transform(lons, lats)  # transformação vetorizada
    return [Point(float(x), float(y), v.vehicle_id) for v, x, y in zip(vehicles, xs, ys)]
