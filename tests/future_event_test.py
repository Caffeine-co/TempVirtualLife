from __future__ import annotations

import asyncio
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from src.life import LifeConfig, MeaningEvent, SimulationClock, build_life_runtime


async def run() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db = str(Path(temp_dir) / "life.db")
        tz = ZoneInfo("Asia/Tokyo")
        clock = SimulationClock(datetime(2026, 10, 5, 12, 0, tzinfo=tz))
        runtime = build_life_runtime(
            LifeConfig(database_path=db, random_seed=2),
            clock=clock,
        )
        await runtime.start()

        before = await runtime.get_state()
        future = MeaningEvent(
            occurred_at=clock.now() + timedelta(hours=1),
            name="future_stressor",
            intensity=1.0,
            stress=1.0,
            emotion="worry",
        )
        await runtime.submit(future)

        # 未来事件尚未发生，因此当前 stress 不应立刻改变。
        scheduled = await runtime.get_state()
        assert scheduled.character.affect.stress == before.character.affect.stress

        clock.advance(timedelta(hours=1))
        await runtime.sync()
        after = await runtime.get_state()
        assert after.character.affect.stress > before.character.affect.stress
        assert any(e.name == "worry" for e in after.character.affect.emotions)

        await runtime.stop()


if __name__ == "__main__":
    asyncio.run(run())
    print("future_event_test: PASS")
