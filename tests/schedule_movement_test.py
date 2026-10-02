from __future__ import annotations

import asyncio
import tempfile
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from src.life import LifeConfig, SimulationClock, build_life_runtime
from src.life.models import PlaceDefinition, ScheduleBlock, TravelLink, WorldConfig


async def run() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db = str(Path(temp_dir) / "life.db")
        tz = ZoneInfo("Asia/Tokyo")
        clock = SimulationClock(datetime(2026, 10, 5, 8, 50, tzinfo=tz))

        config = LifeConfig(
            database_path=db,
            random_seed=1,
            world=WorldConfig(
                places=[
                    PlaceDefinition(
                        place_id="home",
                        links=[TravelLink(to_place_id="school", minutes=20)],
                    ),
                    PlaceDefinition(place_id="school"),
                ]
            ),
            schedule=[
                ScheduleBlock(
                    name="class",
                    weekdays=[0],
                    start=time(9, 0),
                    end=time(10, 0),
                    action_type="work",
                    place_id="school",
                    mode="hard",
                    weight=1.0,
                )
            ],
        )
        config.initial.spatial.place_id = "home"

        runtime = build_life_runtime(config, clock=clock)
        await runtime.start()

        clock.advance(timedelta(minutes=10))
        await runtime.sync()
        at_nine = await runtime.get_state()
        assert at_nine.character.action is not None
        assert at_nine.character.action.type == "travel"
        assert at_nine.character.action.destination_place_id == "school"

        clock.advance(timedelta(minutes=20))
        await runtime.sync()
        arrived = await runtime.get_state()
        assert arrived.character.spatial.place_id == "school"
        assert arrived.character.action is not None
        assert arrived.character.action.type == "work"

        await runtime.stop()


if __name__ == "__main__":
    asyncio.run(run())
    print("schedule_movement_test: PASS")
