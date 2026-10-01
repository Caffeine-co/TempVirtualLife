from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .models import ScheduleBlock


def _interval_for_date(
    block: ScheduleBlock,
    day: date,
    tz: ZoneInfo,
) -> tuple[datetime, datetime]:
    start = datetime.combine(day, block.start, tzinfo=tz)
    end = datetime.combine(day, block.end, tzinfo=tz)
    if end <= start:
        end += timedelta(days=1)
    return start, end


class ScheduleService:
    """只负责回答“现在有什么日程”和“下一个边界是什么时候”。"""

    def __init__(self, blocks: list[ScheduleBlock], timezone: str):
        self.blocks = blocks
        self.tz = ZoneInfo(timezone)

    def active_block(self, now: datetime) -> ScheduleBlock | None:
        local = now.astimezone(self.tz)

        # 检查今天和昨天，昨天用于覆盖跨午夜日程。
        for offset in (0, -1):
            day = local.date() + timedelta(days=offset)
            weekday = day.weekday()
            for block in self.blocks:
                if weekday not in block.weekdays:
                    continue
                start, end = _interval_for_date(block, day, self.tz)
                if start <= local < end:
                    return block
        return None

    def next_boundary_after(self, now: datetime) -> datetime | None:
        """返回严格晚于 now 的最近一个日程开始/结束时间。"""

        local = now.astimezone(self.tz)
        candidates: list[datetime] = []

        # 查未来 8 天足以覆盖完整一周循环。
        for offset in range(-1, 8):
            day = local.date() + timedelta(days=offset)
            weekday = day.weekday()
            for block in self.blocks:
                if weekday not in block.weekdays:
                    continue
                start, end = _interval_for_date(block, day, self.tz)
                if start > local:
                    candidates.append(start)
                if end > local:
                    candidates.append(end)

        return min(candidates) if candidates else None
