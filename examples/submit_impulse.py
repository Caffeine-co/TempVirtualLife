from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.life import ImpulseEvent, LifeConfig, SimulationClock, build_life_runtime


async def main() -> None:
    db = Path("life_impulse_demo.db")
    db.unlink(missing_ok=True)

    tz = ZoneInfo("Asia/Tokyo")
    clock = SimulationClock(datetime(2026, 10, 1, 20, 0, tzinfo=tz))
    runtime = build_life_runtime(
        LifeConfig(database_path=str(db), random_seed=1),
        clock=clock,
    )
    await runtime.start()

    before = await runtime.get_view()
    print("BEFORE:", before.state.action, before.state.affect)

    # 模拟“上层 Appraisal 已判断：这是一个偏紧急、略有压力的社交刺激”。
    await runtime.submit(
        ImpulseEvent(
            occurred_at=clock.now(),
            name="example_social_signal",
            intensity=0.7,
            urgency=0.8,
            valence=0.0,
            arousal=0.5,
            stress=0.3,
            target_action="socialize",
        )
    )

    after = await runtime.get_view()
    print("AFTER :", after.state.action, after.state.affect)

    await runtime.stop()


if __name__ == "__main__":
    asyncio.run(main())
