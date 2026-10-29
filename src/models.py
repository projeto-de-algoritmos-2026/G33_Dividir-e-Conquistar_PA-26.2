"""Modelos de domínio internos (independentes do formato JSON da API)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class BusLine:
    """Linha retornada por /Linha/Buscar.

    Atenção: ``code`` (campo ``cl``) é o identificador INTERNO da API, diferente
    para cada sentido. O número visto pelo passageiro é ``sign`` (``lt``-``tl``),
    ex.: "8000-10".
    """

    code: int  # cl — identificador interno usado em /Posicao/Linha
    circular: bool  # lc
    sign_prefix: str  # lt — primeira parte do letreiro
    sign_suffix: int  # tl — segunda parte do letreiro (10, 21, 23, 32, 41)
    direction: int  # sl — 1: principal→secundário | 2: secundário→principal
    main_terminal: str  # tp
    secondary_terminal: str  # ts
    source: str = "real"

    @property
    def sign(self) -> str:
        return f"{self.sign_prefix}-{self.sign_suffix}"

    @property
    def origin(self) -> str:
        return self.main_terminal if self.direction == 1 else self.secondary_terminal

    @property
    def destination(self) -> str:
        return self.secondary_terminal if self.direction == 1 else self.main_terminal

    @property
    def direction_label(self) -> str:
        return f"Sentido {self.direction}: {self.origin} → {self.destination}"

    @property
    def display_name(self) -> str:
        return f"{self.sign} — {self.main_terminal} / {self.secondary_terminal}"


@dataclass(frozen=True, slots=True)
class VehiclePosition:
    """Posição de um veículo (campos p, a, ta, py, px de /Posicao/Linha)."""

    vehicle_id: str  # p — prefixo
    latitude: float  # py
    longitude: float  # px
    position_time_utc: datetime | None  # ta — horário de captura da posição (UTC)
    accessible: bool | None  # a


@dataclass(slots=True)
class PositionsSnapshot:
    """Uma consulta de posições de uma linha."""

    line_code: int
    collected_at_utc: datetime  # quando o TwoBus fez a consulta
    api_reference_time: str | None  # hr — horário de referência (HH:MM, horário local)
    vehicles: list[VehiclePosition] = field(default_factory=list)
    discarded: int = 0  # registros descartados por dados inválidos
    source: str = "real"  # "real" ou "demo"
