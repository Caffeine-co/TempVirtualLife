from __future__ import annotations

from .clock import RealClock
from .kernel import LifeKernel
from .models import LifeConfig
from .repository import SQLiteLifeRepository
from .runtime import LifeRuntime


def build_life_runtime(config: LifeConfig, clock=None) -> LifeRuntime:
    """集中创建 Runtime，避免业务代码到处 new 各种组件。"""

    if clock is None:
        clock = RealClock(config.timezone)

    kernel = LifeKernel(config)
    repository = SQLiteLifeRepository(config.database_path)
    return LifeRuntime(kernel, repository, clock)
