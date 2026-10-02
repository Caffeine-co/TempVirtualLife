from __future__ import annotations

import asyncio

from .appraisal_listener_test import run as appraisal_listener
from .domain_modules_test import run as domain_modules
from .future_event_test import run as future_event
from .long_simulation_test import run as long_simulation
from .recovery_test import run as recovery
from .schedule_movement_test import run as schedule_movement
from .smoke_test import run as smoke


async def main() -> None:
    tests = [
        ("smoke", smoke),
        ("recovery", recovery),
        ("schedule_movement", schedule_movement),
        ("future_event", future_event),
        ("domain_modules", domain_modules),
        ("appraisal_listener", appraisal_listener),
        ("long_simulation", long_simulation),
    ]

    for name, func in tests:
        await func()
        print(f"{name}: PASS")


if __name__ == "__main__":
    asyncio.run(main())
