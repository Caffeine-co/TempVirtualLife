from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from src.life import (
    AdapterAvailabilityEvent,
    GoalState,
    GoalUpsertEvent,
    MeaningEvent,
    SimulationClock,
    build_life_runtime,
)
from src.life.config import load_life_config


async def main() -> None:
    config = load_life_config("life.example.json")
    db = Path("life_event_demo.db")
    db.unlink(missing_ok=True)
    config = config.model_copy(update={"database_path": str(db)})

    tz = ZoneInfo(config.timezone)
    clock = SimulationClock(datetime(2026, 10, 5, 18, 0, tzinfo=tz))
    runtime = build_life_runtime(config, clock=clock)
    await runtime.start()

    # OneBot 可用只是世界事实；LifeKernel 不需要 import NoneBot。
    await runtime.submit(
        AdapterAvailabilityEvent(
            occurred_at=clock.now(),
            adapter="onebot",
            available=True,
        )
    )

    # 新建一个结构化目标。BehaviorEngine 会把它转成 work 的额外效用。
    await runtime.submit(
        GoalUpsertEvent(
            occurred_at=clock.now(),
            goal=GoalState(
                goal_id="demo_task",
                title="Finish a task",
                action_type="work",
                priority=0.9,
                progress_per_hour=0.25,
                deadline=clock.now() + timedelta(hours=8),
            ),
        )
    )

    # MeaningEvent 模拟未来 Appraisal 层的输出，而不是原始自然语言消息。
    await runtime.submit(
        MeaningEvent(
            occurred_at=clock.now(),
            name="important_social_signal",
            intensity=0.7,
            urgency=0.8,
            arousal=0.5,
            stress=0.25,
            emotion="concern",
            target_action="communicate",
            memory_salience=0.6,
        )
    )

    print((await runtime.get_view()).model_dump_json(indent=2))
    await runtime.stop()


if __name__ == "__main__":
    asyncio.run(main())
