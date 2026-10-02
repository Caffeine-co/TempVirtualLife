from __future__ import annotations

from datetime import datetime

from .models import GoalState, LifeState


def _goal_value(goal: GoalState, now: datetime) -> float:
    """单个目标在当前时刻的驱动力。"""

    remaining = 1.0 - goal.progress
    value = goal.priority * 70.0 * remaining
    if goal.deadline is not None:
        hours_left = (goal.deadline - now).total_seconds() / 3600.0
        if hours_left <= 0:
            value += 50.0
        elif hours_left < 24:
            value += (24.0 - hours_left) / 24.0 * 40.0
    return value


def goal_bonus(state: LifeState, action_type: str, now: datetime) -> float:
    """把所有 active goal 对某个 action 的推动力转成 Utility bonus。"""

    bonus = 0.0
    for goal in state.goals.values():
        if goal.status != "active" or goal.action_type != action_type:
            continue

        bonus += _goal_value(goal, now)
    # 防止大量同类目标把其他生理需求永久淹没。
    return max(-150.0, min(150.0, bonus))


def dominant_goal(state: LifeState, action_type: str, now: datetime) -> GoalState | None:
    """返回当前最能推动该行为的 active goal。"""

    candidates = [
        goal
        for goal in state.goals.values()
        if goal.status == "active" and goal.action_type == action_type
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda goal: _goal_value(goal, now))


def apply_action_progress(
    state: LifeState,
    *,
    action_type: str,
    target: str | None,
    duration_hours: float,
) -> list[str]:
    """行为完成后推进匹配的目标，返回本次完成的 goal_id。"""

    completed: list[str] = []
    for goal in state.goals.values():
        if goal.status != "active" or goal.action_type != action_type:
            continue
        if goal.target is not None and goal.target != target:
            continue

        goal.progress = min(1.0, goal.progress + duration_hours * goal.progress_per_hour)
        if goal.progress >= 1.0:
            goal.status = "completed"
            completed.append(goal.goal_id)
    return completed


def fail_expired_goals(state: LifeState, now: datetime) -> list[str]:
    """deadline 已过且仍未完成的目标标记为 failed。"""

    failed: list[str] = []
    for goal in state.goals.values():
        if (
            goal.status == "active"
            and goal.deadline is not None
            and goal.deadline <= now
            and goal.progress < 1.0
        ):
            goal.status = "failed"
            failed.append(goal.goal_id)
    return failed


def next_goal_deadline(state: LifeState, now: datetime) -> datetime | None:
    candidates = [
        goal.deadline
        for goal in state.goals.values()
        if goal.status == "active" and goal.deadline is not None and goal.deadline > now
    ]
    return min(candidates) if candidates else None
