from __future__ import annotations

import asyncio
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from src.life import ForceActionEvent, LifeConfig, SimulationClock, build_life_runtime


async def run() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db = str(Path(temp_dir) / "life.db")
        tz = ZoneInfo("Asia/Tokyo")
        clock = SimulationClock(datetime(2026, 10, 5, 8, 0, tzinfo=tz))
        runtime = build_life_runtime(
            LifeConfig(database_path=db, random_seed=1),
            clock=clock,
        )
        await runtime.start()

        await runtime.submit(
            ForceActionEvent(
                occurred_at=clock.now(),
                action_type="work",
                duration_minutes=60,
            )
        )
        before = await runtime.get_state()

        clock.advance(timedelta(minutes=30))
        await runtime.sync()
        middle = await runtime.get_state()

        assert middle.as_of == clock.now()
        assert middle.character.body.hunger > before.character.body.hunger
        assert middle.revision > before.revision

        clock.advance(timedelta(minutes=40))
        await runtime.sync()
        after = await runtime.get_state()
        assert after.character.action is not None
        assert after.as_of == clock.now()

        events = await runtime.repository.recent_events(100)
        assert any(e["kind"] == "action_completed" for e in events)
        await runtime.stop()


if __name__ == "__main__":
    asyncio.run(run())
    print("smoke_test: PASS")
