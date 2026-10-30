"""Persistência de snapshots em SQLite.

Esquema:
    collections — uma linha por consulta (coleta) feita pelo TwoBus.
        collected_at_utc  → horário em que o TwoBus consultou a API (UTC)
        api_reference_time→ campo ``hr`` da resposta
        content_hash      → impressão digital das posições; junto ao horário
                            de coleta, impede duplicar exatamente a mesma coleta.
    positions — uma linha por veículo em uma coleta.
        position_time_utc → campo ``ta`` (horário de CAPTURA da posição)
        UNIQUE(collection_id, vehicle_id) impede veículo duplicado na coleta.
"""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.models import PositionsSnapshot

SCHEMA = """
CREATE TABLE IF NOT EXISTS collections (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    collected_at_utc   TEXT    NOT NULL,
    source             TEXT    NOT NULL CHECK (source IN ('real', 'demo')),
    line_code          INTEGER NOT NULL,
    line_sign          TEXT,
    direction          INTEGER,
    direction_label    TEXT,
    api_reference_time TEXT,
    vehicle_count      INTEGER NOT NULL,
    content_hash       TEXT    NOT NULL,
    UNIQUE (source, line_code, collected_at_utc, content_hash)
);
CREATE TABLE IF NOT EXISTS positions (
    collection_id     INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    vehicle_id        TEXT    NOT NULL,
    latitude          REAL    NOT NULL,
    longitude         REAL    NOT NULL,
    position_time_utc TEXT,
    accessible        INTEGER,
    PRIMARY KEY (collection_id, vehicle_id)
);
CREATE INDEX IF NOT EXISTS idx_collections_line ON collections(source, line_code, collected_at_utc);
"""


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def snapshot_hash(snapshot: PositionsSnapshot) -> str:
    """Hash determinístico das posições (veículo, horário de captura, lat, lon)."""
    items = sorted(
        (v.vehicle_id, _iso(v.position_time_utc) or "", f"{v.latitude:.6f}", f"{v.longitude:.6f}")
        for v in snapshot.vehicles
    )
    return hashlib.sha256(repr(items).encode()).hexdigest()


class SnapshotRepository:
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        if str(db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._memory_conn = sqlite3.connect(":memory:") if str(db_path) == ":memory:" else None
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _conn(self):
        conn = self._memory_conn or sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            if self._memory_conn is None:
                conn.close()

    # --------------------------------------------------------------- escrita
    def save_snapshot(
        self,
        snapshot: PositionsSnapshot,
        line_sign: str = "",
        direction: int | None = None,
        direction_label: str = "",
    ) -> tuple[int, bool]:
        """Grava a coleta. Retorna (id, criado). Se já existir idêntica, criado=False."""
        h = snapshot_hash(snapshot)
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id FROM collections WHERE source=? AND line_code=? AND collected_at_utc=? AND content_hash=?",
                (snapshot.source, snapshot.line_code, _iso(snapshot.collected_at_utc), h),
            ).fetchone()
            if row:
                return int(row[0]), False
            cur = conn.execute(
                """INSERT INTO collections (collected_at_utc, source, line_code, line_sign, direction,
                       direction_label, api_reference_time, vehicle_count, content_hash)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    _iso(snapshot.collected_at_utc),
                    snapshot.source,
                    snapshot.line_code,
                    line_sign,
                    direction,
                    direction_label,
                    snapshot.api_reference_time,
                    len(snapshot.vehicles),
                    h,
                ),
            )
            cid = int(cur.lastrowid)
            conn.executemany(
                """INSERT OR IGNORE INTO positions
                   (collection_id, vehicle_id, latitude, longitude, position_time_utc, accessible)
                   VALUES (?,?,?,?,?,?)""",
                [
                    (
                        cid,
                        v.vehicle_id,
                        v.latitude,
                        v.longitude,
                        _iso(v.position_time_utc),
                        None if v.accessible is None else int(v.accessible),
                    )
                    for v in snapshot.vehicles
                ],
            )
            return cid, True

    def delete_source(self, source: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM positions WHERE collection_id IN (SELECT id FROM collections WHERE source=?)",
                (source,),
            )
            conn.execute("DELETE FROM collections WHERE source=?", (source,))

    # ---------------------------------------------------------------- leitura
    def list_lines(self) -> pd.DataFrame:
        with self._conn() as conn:
            return pd.read_sql_query(
                """SELECT source, line_code, line_sign, direction, direction_label,
                          COUNT(*) AS collections, MIN(collected_at_utc) AS first_utc,
                          MAX(collected_at_utc) AS last_utc
                   FROM collections GROUP BY source, line_code ORDER BY last_utc DESC""",
                conn,
            )

    def list_collections(self, source: str | None = None, line_code: int | None = None) -> pd.DataFrame:
        sql = "SELECT * FROM collections WHERE 1=1"
        params: list = []
        if source:
            sql += " AND source=?"
            params.append(source)
        if line_code is not None:
            sql += " AND line_code=?"
            params.append(int(line_code))
        sql += " ORDER BY collected_at_utc"
        with self._conn() as conn:
            return pd.read_sql_query(sql, conn, params=params)

    def get_positions(self, collection_id: int) -> pd.DataFrame:
        with self._conn() as conn:
            return pd.read_sql_query(
                "SELECT * FROM positions WHERE collection_id=? ORDER BY vehicle_id",
                conn,
                params=(int(collection_id),),
            )

    def export_dataframe(self, source: str | None = None, line_code: int | None = None) -> pd.DataFrame:
        """Junção coletas × posições, pronta para exportar em CSV."""
        sql = """SELECT c.id AS collection_id, c.collected_at_utc, c.source, c.line_code, c.line_sign,
                        c.direction, c.direction_label, c.api_reference_time,
                        p.vehicle_id, p.latitude, p.longitude, p.position_time_utc, p.accessible
                 FROM collections c JOIN positions p ON p.collection_id = c.id WHERE 1=1"""
        params: list = []
        if source:
            sql += " AND c.source=?"
            params.append(source)
        if line_code is not None:
            sql += " AND c.line_code=?"
            params.append(int(line_code))
        sql += " ORDER BY c.collected_at_utc, p.vehicle_id"
        with self._conn() as conn:
            return pd.read_sql_query(sql, conn, params=params)
