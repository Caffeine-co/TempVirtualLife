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
        clock = SimulationClock(datetime(2026, 10, 5, 22, 0, tzinfo=tz))
        config = LifeConfig(database_path=db, random_seed=42)

        runtime1 = build_life_runtime(config, clock=clock)
        await runtime1.start()
        before = await runtime1.get_state()
        await runtime1.stop()

        clock.advance(timedelta(hours=8))

        runtime2 = build_life_runtime(config, clock=clock)
        await runtime2.start()
        recovered = await runtime2.get_state()

        assert recovered.as_of == clock.now()
        assert recovered.revision > before.revision
        assert recovered.character.action is not None
        await runtime2.stop()


if __name__ == "__main__":
    asyncio.run(run())
    print("recovery_test: PASS")
