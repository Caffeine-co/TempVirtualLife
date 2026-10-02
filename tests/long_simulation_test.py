from __future__ import annotations

import asyncio
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from src.life import LifeConfig, SimulationClock, build_life_runtime


async def run() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db = str(Path(temp_dir) / "life.db")
        tz = ZoneInfo("Asia/Tokyo")
        clock = SimulationClock(datetime(2026, 10, 5, 0, 0, tzinfo=tz))
        runtime = build_life_runtime(
            LifeConfig(database_path=db, random_seed=2501),
            clock=clock,
        )
        await runtime.start()

        # 30 天，每 6 小时观察一次。主要检查死循环、越界和行为断链。
        for _ in range(30 * 4):
            clock.advance(timedelta(hours=6))
            await runtime.sync()
            state = await runtime.get_state()
            assert state.as_of == clock.now()
            assert state.character.action is not None

        await runtime.stop()


if __name__ == "__main__":
    asyncio.run(run())
    print("long_simulation_test: PASS")
