from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from src.life import LifeConfig, SimulationClock, build_life_runtime
from src.life.config import load_life_config


def summary(view) -> str:
    state = view.state
    action = state.character.action.type if state.character.action else "none"
    return (
        f"{state.as_of:%m-%d %H:%M} | {action:11} | "
        f"place={state.character.spatial.place_id:10} "
        f"energy={state.character.body.energy:5.1f} "
        f"fatigue={state.character.body.physical_fatigue:5.1f} "
        f"sleepy={view.derived.sleepiness:5.1f} "
        f"stress={state.character.affect.stress:5.1f}"
    )


async def main() -> None:
    config = load_life_config("life.example.json")
    demo_db = Path("life_week_demo.db")
    demo_db.unlink(missing_ok=True)
    config = config.model_copy(update={"database_path": str(demo_db)})

    tz = ZoneInfo(config.timezone)
    clock = SimulationClock(datetime(2026, 10, 5, 7, 0, tzinfo=tz))
    runtime = build_life_runtime(config, clock=clock)
    await runtime.start()

    print(summary(await runtime.get_view()))
    for _ in range(7 * 8):
        clock.advance(timedelta(hours=3))
        await runtime.sync()
        print(summary(await runtime.get_view()))

    print("\n最近 20 条生命日志：")
    for event in await runtime.repository.recent_events(20):
        print(event)

    await runtime.stop()


if __name__ == "__main__":
    asyncio.run(main())
