from __future__ import annotations

import asyncio
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from src.life import (
    GoalProgressEvent,
    GoalState,
    GoalUpsertEvent,
    HealthImpactEvent,
    LifeConfig,
    RelationshipEvent,
    SimulationClock,
    build_life_runtime,
)


async def run() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db = str(Path(temp_dir) / "life.db")
        tz = ZoneInfo("Asia/Tokyo")
        clock = SimulationClock(datetime(2026, 10, 5, 12, 0, tzinfo=tz))
        runtime = build_life_runtime(LifeConfig(database_path=db, random_seed=3), clock=clock)
        await runtime.start()

        await runtime.submit(
            GoalUpsertEvent(
                occurred_at=clock.now(),
                goal=GoalState(
                    goal_id="g1",
                    title="demo",
                    action_type="work",
                    priority=0.9,
                    deadline=clock.now() + timedelta(hours=4),
                ),
            )
        )
        await runtime.submit(
            GoalProgressEvent(
                occurred_at=clock.now(),
                goal_id="g1",
                delta=0.4,
            )
        )
        await runtime.submit(
            RelationshipEvent(
                occurred_at=clock.now(),
                target_id="person_a",
                familiarity_delta=20,
                trust_delta=5,
            )
        )
        await runtime.submit(
            HealthImpactEvent(
                occurred_at=clock.now(),
                name="cold",
                severity=40,
                fatigue_effect=30,
                energy_penalty=20,
                recovery_half_life_hours=24,
            )
        )

        state = await runtime.get_state()
        assert state.goals["g1"].progress == 0.4
        assert state.relationships["person_a"].familiarity == 20
        assert "cold" in state.health.conditions
        await runtime.stop()


if __name__ == "__main__":
    asyncio.run(run())
    print("domain_modules_test: PASS")
