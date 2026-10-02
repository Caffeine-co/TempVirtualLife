from __future__ import annotations

import math
from datetime import datetime
from uuid import uuid4

from .models import LifeConfig, LifeState, MemoryTrace


def add_memory(state: LifeState, config: LifeConfig, memory: MemoryTrace) -> None:
    """追加结构化记忆，并限制总量，避免无限增长。"""

    state.memories.append(memory)
    if len(state.memories) > config.memory.max_records:
        # 保留 salience 更高、更新的记忆。这里使用简单排序，后续可换成数据库分层归档。
        state.memories.sort(key=lambda m: (m.salience, m.occurred_at), reverse=True)
        del state.memories[config.memory.max_records :]


def memory_action_bonus(
    state: LifeState,
    config: LifeConfig,
    action_type: str,
    now: datetime,
) -> float:
    """让近期高显著度记忆短期影响行为，但随时间衰减。"""

    total = 0.0
    for memory in state.memories:
        raw = memory.action_bias.get(action_type)
        if raw is None:
            continue

        age_days = max(0.0, (now - memory.occurred_at).total_seconds() / 86400.0)
        decay = math.exp(-math.log(2) * age_days / config.memory.half_life_days)
        total += raw * memory.salience * decay
    return max(-40.0, min(40.0, total))


def make_memory(
    *,
    occurred_at: datetime,
    kind: str,
    salience: float,
    valence: float = 0.0,
    related_entity: str | None = None,
    tags: list[str] | None = None,
    action_bias: dict[str, float] | None = None,
    note: str | None = None,
) -> MemoryTrace:
    return MemoryTrace(
        memory_id=uuid4().hex,
        occurred_at=occurred_at,
        kind=kind,
        salience=salience,
        valence=valence,
        related_entity=related_entity,
        tags=tags or [],
        action_bias=action_bias or {},
        note=note,
    )
