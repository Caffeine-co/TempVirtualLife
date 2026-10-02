from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

from pydantic import TypeAdapter

from .models import JournalRecord, LifeEvent, LifeState


_EVENT_ADAPTER = TypeAdapter(LifeEvent)


class SQLiteLifeRepository:
    """正式版最小持久化层。

    三类数据：
    1. life_snapshot：当前权威状态；
    2. life_event：已经发生的审计日志；
    3. life_pending_event：未来事件队列，重启后仍然存在。
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

                CREATE TABLE IF NOT EXISTS life_pending_event (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    occurred_at TEXT NOT NULL,
                    event_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_life_pending_time
                ON life_pending_event(occurred_at);
                """
            )
            db.commit()

    async def load_state(self) -> LifeState | None:
        return await asyncio.to_thread(self._load_state_sync)

    def _load_state_sync(self) -> LifeState | None:
        with sqlite3.connect(self.path) as db:
            row = db.execute(
                "SELECT state_json FROM life_snapshot WHERE id = 1"
            ).fetchone()
            if row is None:
                return None
            return LifeState.model_validate_json(row[0])

    async def commit(
        self,
        state: LifeState,
        records: list[JournalRecord],
        *,
        consumed_pending_ids: list[int] | None = None,
    ) -> None:
        """原子提交 snapshot + journal + 已消费的 future events。"""

        await asyncio.to_thread(
            self._commit_sync,
            state,
            records,
            consumed_pending_ids or [],
        )

    def _commit_sync(
        self,
        state: LifeState,
        records: list[JournalRecord],
        consumed_pending_ids: list[int],
    ) -> None:
        state_json = state.model_dump_json()

        with sqlite3.connect(self.path) as db:
            # 显式事务保证三类修改要么全部成功，要么全部回滚。
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

            if consumed_pending_ids:
                placeholders = ",".join("?" for _ in consumed_pending_ids)
                db.execute(
                    f"DELETE FROM life_pending_event WHERE id IN ({placeholders})",
                    consumed_pending_ids,
                )

            db.commit()

    async def schedule_event(self, event: LifeEvent) -> int:
        return await asyncio.to_thread(self._schedule_event_sync, event)

    def _schedule_event_sync(self, event: LifeEvent) -> int:
        event_json = _EVENT_ADAPTER.dump_json(event).decode("utf-8")
        with sqlite3.connect(self.path) as db:
            cursor = db.execute(
                """
                INSERT INTO life_pending_event(occurred_at, event_json)
                VALUES(?, ?)
                """,
                (event.occurred_at.isoformat(), event_json),
            )
            db.commit()
            return int(cursor.lastrowid)

    async def due_events(self, until) -> list[tuple[int, LifeEvent]]:
        return await asyncio.to_thread(self._due_events_sync, until)

    def _due_events_sync(self, until) -> list[tuple[int, LifeEvent]]:
        with sqlite3.connect(self.path) as db:
            rows = db.execute(
                """
                SELECT id, event_json
                FROM life_pending_event
                WHERE occurred_at <= ?
                ORDER BY occurred_at ASC, id ASC
                """,
                (until.isoformat(),),
            ).fetchall()

        return [
            (int(event_id), _EVENT_ADAPTER.validate_json(event_json))
            for event_id, event_json in rows
        ]

    async def next_pending_time(self):
        return await asyncio.to_thread(self._next_pending_time_sync)

    def _next_pending_time_sync(self):
        from datetime import datetime

        with sqlite3.connect(self.path) as db:
            row = db.execute(
                "SELECT occurred_at FROM life_pending_event ORDER BY occurred_at ASC, id ASC LIMIT 1"
            ).fetchone()
        return datetime.fromisoformat(row[0]) if row else None

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
