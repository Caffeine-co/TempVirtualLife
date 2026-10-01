from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

from .models import CharacterRuntimeState, JournalRecord


class SQLiteLifeRepository:
    """最小可用的持久化层：一份快照 + 一条事件日志。

    使用 Python 标准库 sqlite3；异步接口通过 asyncio.to_thread() 包装，
    因此 Life Core 不需要额外依赖 aiosqlite。
    """

    def __init__(self, path: str):
        self.path = path

    async def initialize(self) -> None:
        await asyncio.to_thread(self._initialize_sync)

    def _initialize_sync(self) -> None:
        path = Path(self.path)
        if path.parent != Path("."):
            path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.path) as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS life_snapshot (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    revision INTEGER NOT NULL,
                    as_of TEXT NOT NULL,
                    state_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS life_event (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    revision INTEGER NOT NULL,
                    occurred_at TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    data_json TEXT NOT NULL
                );
                """
            )
            db.commit()

    async def load_state(self) -> CharacterRuntimeState | None:
        return await asyncio.to_thread(self._load_state_sync)

    def _load_state_sync(self) -> CharacterRuntimeState | None:
        with sqlite3.connect(self.path) as db:
            row = db.execute(
                "SELECT state_json FROM life_snapshot WHERE id = 1"
            ).fetchone()
            if row is None:
                return None
            return CharacterRuntimeState.model_validate_json(row[0])

    async def commit(
        self,
        state: CharacterRuntimeState,
        records: list[JournalRecord],
    ) -> None:
        await asyncio.to_thread(self._commit_sync, state, records)

    def _commit_sync(
        self,
        state: CharacterRuntimeState,
        records: list[JournalRecord],
    ) -> None:
        state_json = state.model_dump_json()
        with sqlite3.connect(self.path) as db:
            db.execute("BEGIN")
            db.execute(
                """
                INSERT INTO life_snapshot(id, revision, as_of, state_json)
                VALUES(1, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    revision = excluded.revision,
                    as_of = excluded.as_of,
                    state_json = excluded.state_json
                """,
                (state.revision, state.as_of.isoformat(), state_json),
            )

            for record in records:
                db.execute(
                    """
                    INSERT INTO life_event(revision, occurred_at, kind, data_json)
                    VALUES(?, ?, ?, ?)
                    """,
                    (
                        state.revision,
                        record.occurred_at.isoformat(),
                        record.kind,
                        json.dumps(record.data, ensure_ascii=False, default=str),
                    ),
                )
            db.commit()

    async def recent_events(self, limit: int = 50) -> list[dict]:
        return await asyncio.to_thread(self._recent_events_sync, limit)

    def _recent_events_sync(self, limit: int) -> list[dict]:
        with sqlite3.connect(self.path) as db:
            rows = db.execute(
                """
                SELECT seq, revision, occurred_at, kind, data_json
                FROM life_event
                ORDER BY seq DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        result = []
        for seq, revision, occurred_at, kind, data_json in reversed(rows):
            result.append(
                {
                    "seq": seq,
                    "revision": revision,
                    "occurred_at": occurred_at,
                    "kind": kind,
                    "data": json.loads(data_json),
                }
            )
        return result
