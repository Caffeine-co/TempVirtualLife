from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, time
from pathlib import Path
from zoneinfo import ZoneInfo

from src.life import LifeConfig, SimulationClock, build_life_runtime
from src.life.models import ScheduleBlock


def line(view) -> str:
    state = view.state
    action = state.action.type if state.action else "none"
    return (
        f"{state.as_of:%m-%d %H:%M} | {action:10} | "
        f"energy={state.body.energy:5.1f} "
        f"fatigue={state.body.physical_fatigue:5.1f} "
        f"sleepy={view.derived.sleepiness:5.1f} "
        f"hunger={state.body.hunger:5.1f} "
        f"stress={state.affect.stress:5.1f}"
    )


async def main() -> None:
    demo_db = Path("life_demo.db")
    demo_db.unlink(missing_ok=True)

    tz = ZoneInfo("Asia/Tokyo")
    clock = SimulationClock(datetime(2026, 10, 1, 7, 0, tzinfo=tz))

    # 这里只是展示 Schedule 如何工作，不代表任何具体角色。
    config = LifeConfig(
        database_path=str(demo_db),
        random_seed=2501,
        schedule=[
            ScheduleBlock(
                name="morning_work",
                weekdays=[0, 1, 2, 3, 4, 5, 6],
                start=time(9, 0),
                end=time(12, 0),
                action_type="work",
                place_id="work_area",
                rigidity=0.9,
            ),
            ScheduleBlock(
                name="afternoon_create",
                weekdays=[0, 1, 2, 3, 4, 5, 6],
                start=time(14, 0),
                end=time(16, 0),
                action_type="create",
                place_id="creative_area",
                rigidity=0.75,
            ),
        ],
    )

    runtime = build_life_runtime(config, clock=clock)
    await runtime.start()

    print(line(await runtime.get_view()))
    for _ in range(12):
        clock.advance(timedelta(hours=2))
        await runtime.sync()
        print(line(await runtime.get_view()))

    print("\n最近事件：")
    for event in await runtime.repository.recent_events(20):
        print(event)

    await runtime.stop()


if __name__ == "__main__":
    asyncio.run(main())
