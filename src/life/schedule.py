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
    # end <= start 代表跨午夜，例如 23:00~02:00。
    if end <= start:
        end += timedelta(days=1)
    return start, end


class ScheduleService:
    """只回答日程事实；BehaviorEngine 决定如何响应这些事实。"""

    def __init__(self, blocks: list[ScheduleBlock], timezone: str):
        self.blocks = blocks
        self.tz = ZoneInfo(timezone)

    def active_blocks(self, now: datetime) -> list[ScheduleBlock]:
        local = now.astimezone(self.tz)
        result: list[ScheduleBlock] = []

        # 昨天也要检查，因为有日程可能跨过午夜。
        for offset in (0, -1):
            day = local.date() + timedelta(days=offset)
            weekday = day.weekday()
            for block in self.blocks:
                if weekday not in block.weekdays:
                    continue
                start, end = _interval_for_date(block, day, self.tz)
                if start <= local < end:
                    result.append(block)

        # hard 优先；同类中 weight 越高优先级越高。
        result.sort(key=lambda b: (b.mode != "hard", -b.weight, b.name))
        return result

    def primary_hard_block(self, now: datetime) -> ScheduleBlock | None:
        for block in self.active_blocks(now):
            if block.mode == "hard":
                return block
        return None


    def next_hard_start_after(self, now: datetime) -> tuple[datetime, ScheduleBlock] | None:
        """返回严格晚于 now 的最近一个 hard schedule 开始时刻。"""

        local = now.astimezone(self.tz)
        candidates: list[tuple[datetime, ScheduleBlock]] = []

        for offset in range(0, 8):
            day = local.date() + timedelta(days=offset)
            weekday = day.weekday()
            for block in self.blocks:
                if block.mode != "hard" or weekday not in block.weekdays:
                    continue
                start, _ = _interval_for_date(block, day, self.tz)
                if start > local:
                    candidates.append((start, block))

        return min(candidates, key=lambda item: item[0]) if candidates else None

    def next_boundary_after(self, now: datetime) -> datetime | None:
        local = now.astimezone(self.tz)
        candidates: list[datetime] = []

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
