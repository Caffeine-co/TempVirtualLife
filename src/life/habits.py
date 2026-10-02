from __future__ import annotations

import math
from datetime import datetime

from .models import HabitState, LifeConfig, LifeState


def context_key(state: LifeState, now: datetime) -> str:
    """第一版习惯上下文：地点 + 工作日/周末 + 四段日内时间。"""

    hour = now.hour
    if 5 <= hour < 11:
        daypart = "morning"
    elif 11 <= hour < 17:
        daypart = "afternoon"
    elif 17 <= hour < 23:
        daypart = "evening"
    else:
        daypart = "night"

    weekday_kind = "weekday" if now.weekday() < 5 else "weekend"
    return f"{state.character.spatial.place_id}|{weekday_kind}|{daypart}"


def _habit_id(context: str, action_type: str) -> str:
    return f"{context}::{action_type}"


def effective_habit_strength(
    state: LifeState,
    config: LifeConfig,
    action_type: str,
    now: datetime,
) -> float:
    """读取带时间衰减后的习惯强度。"""

    context = context_key(state, now)
    habit = state.habits.get(_habit_id(context, action_type))
    if habit is None:
        return 0.0
    if habit.last_performed_at is None:
        return habit.strength

    age_days = max(0.0, (now - habit.last_performed_at).total_seconds() / 86400.0)
    decay = math.exp(-math.log(2) * age_days / config.habit.half_life_days)
    return habit.strength * decay


def reinforce_habit(
    state: LifeState,
    config: LifeConfig,
    action_type: str,
    now: datetime,
    *,
    original_context: str | None = None,
) -> HabitState:
    """行为完成后对当前上下文的同类习惯做渐近强化。"""

    context = original_context or context_key(state, now)
    key = _habit_id(context, action_type)
    habit = state.habits.get(key)

    if habit is None:
        habit = HabitState(context_key=context, action_type=action_type)
        state.habits[key] = habit

    if habit.last_performed_at is None:
        effective = habit.strength
    else:
        age_days = max(0.0, (now - habit.last_performed_at).total_seconds() / 86400.0)
        decay = math.exp(-math.log(2) * age_days / config.habit.half_life_days)
        effective = habit.strength * decay
    habit.strength = min(
        1.0,
        effective + config.habit.learning_rate * (1.0 - effective),
    )
    habit.repetitions += 1
    habit.last_performed_at = now
    return habit
