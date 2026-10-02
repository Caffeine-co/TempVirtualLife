from __future__ import annotations

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.life import (
    AppraisalInput,
    LifeConfig,
    RuleBasedAppraisal,
    SimulationClock,
    build_life_runtime,
)


async def run() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db = str(Path(temp_dir) / "life.db")
        tz = ZoneInfo("Asia/Tokyo")
        clock = SimulationClock(datetime(2026, 10, 5, 18, 0, tzinfo=tz))
        runtime = build_life_runtime(LifeConfig(database_path=db, random_seed=4), clock=clock)
        await runtime.start()

        callback_count = 0

        async def listener(view, records):
            nonlocal callback_count
            callback_count += 1
            # 这一行会重新进入 Runtime 的读锁；若 Listener 仍在写锁中执行就会死锁。
            await runtime.get_state()

        runtime.add_listener(listener)

        appraisal = RuleBasedAppraisal()
        state = await runtime.get_state()
        meaning = appraisal.appraise(
            state,
            AppraisalInput(
                occurred_at=clock.now(),
                name="negative_social_evaluation",
                relevance=0.8,
                goal_congruence=-0.4,
                controllability=0.3,
                novelty=0.6,
                social_evaluation=-0.8,
                threat=0.4,
                urgency=0.5,
            ),
        )
        await runtime.submit(meaning)

        after = await runtime.get_state()
        assert callback_count >= 1
        assert after.character.affect.valence < 0
        assert after.character.affect.emotions
        await runtime.stop()


if __name__ == "__main__":
    asyncio.run(run())
    print("appraisal_listener_test: PASS")
