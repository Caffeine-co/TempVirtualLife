from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


class RealClock:
    """生产环境使用的真实时钟。"""

    def __init__(self, timezone: str):
        self._tz = ZoneInfo(timezone)

    def now(self) -> datetime:
        return datetime.now(self._tz)


class SimulationClock:
    """测试/高速模拟使用的可手动推进时钟。"""

    def __init__(self, current: datetime):
        if current.tzinfo is None:
            raise ValueError("SimulationClock 需要带时区的 datetime")
        self._current = current

    def now(self) -> datetime:
        return self._current

    def advance(self, delta: timedelta) -> datetime:
        if delta.total_seconds() < 0:
            raise ValueError("不能把模拟时钟向后推进")
        self._current += delta
        return self._current
