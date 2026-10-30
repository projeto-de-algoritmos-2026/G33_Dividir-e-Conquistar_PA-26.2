"""Coleta de snapshots (real ou simulada) e gravação no SQLite.

Este módulo NÃO contém laços de repetição: cada chamada faz exatamente uma
consulta. A periodicidade é controlada pela interface.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.api.sptrans_client import SPTransClient
from src.models import BusLine, PositionsSnapshot
from src.services.demo_data import generate_demo_snapshot, scenario_for_line_code
from src.storage.database import SnapshotRepository


@dataclass
class CollectionOutcome:
    snapshot: PositionsSnapshot
    collection_id: int | None
    created: bool


def collect_real(client: SPTransClient, line: BusLine, repo: SnapshotRepository | None, save: bool = True) -> CollectionOutcome:
    snap = client.get_positions(line.code)
    return _persist(snap, line, repo, save)


def collect_demo(line: BusLine, step: int, repo: SnapshotRepository | None, save: bool = True) -> CollectionOutcome:
    scenario = scenario_for_line_code(line.code)
    if scenario is None:
        raise ValueError("Linha não pertence ao modo demonstração.")
    snap = generate_demo_snapshot(scenario.key, step)
    return _persist(snap, line, repo, save)


def _persist(snap: PositionsSnapshot, line: BusLine, repo: SnapshotRepository | None, save: bool) -> CollectionOutcome:
    if not save or repo is None or not snap.vehicles:
        return CollectionOutcome(snap, None, False)
    cid, created = repo.save_snapshot(snap, line.sign, line.direction, line.direction_label)
    return CollectionOutcome(snap, cid, created)
