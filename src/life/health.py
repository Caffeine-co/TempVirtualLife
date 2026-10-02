from __future__ import annotations

import math

from .models import HealthCondition, LifeState


def advance_health(state: LifeState, hours: float) -> None:
    """健康问题按自己的恢复半衰期缓慢减轻。"""

    if hours <= 0:
        return

    expired: list[str] = []
    for name, condition in state.health.conditions.items():
        condition.severity *= math.exp(
            -math.log(2) * hours / condition.recovery_half_life_hours
        )
        if condition.severity < 1:
            expired.append(name)

    for name in expired:
        state.health.conditions.pop(name, None)


def health_penalties(state: LifeState) -> tuple[float, float, float, float]:
    """返回 health_score、pain、fatigue_penalty、energy_penalty。"""

    health_score = 100.0
    pain = state.character.body.pain
    fatigue_penalty = 0.0
    energy_penalty = 0.0

    for condition in state.health.conditions.values():
        scale = condition.severity / 100.0
        health_score -= condition.severity * 0.6
        pain += condition.pain_effect * scale
        fatigue_penalty += condition.fatigue_effect * scale
        energy_penalty += condition.energy_penalty * scale

    return (
        max(0.0, min(100.0, health_score)),
        max(0.0, min(100.0, pain)),
        fatigue_penalty,
        energy_penalty,
    )


def apply_health_impact(
    state: LifeState,
    condition: HealthCondition,
) -> None:
    """同名健康状态取更严重的一次，并刷新恢复参数。"""

    old = state.health.conditions.get(condition.name)
    if old is None:
        state.health.conditions[condition.name] = condition
        return

    old.severity = max(old.severity, condition.severity)
    old.started_at = condition.started_at
    old.recovery_half_life_hours = condition.recovery_half_life_hours
    old.pain_effect = max(old.pain_effect, condition.pain_effect)
    old.fatigue_effect = max(old.fatigue_effect, condition.fatigue_effect)
    old.energy_penalty = max(old.energy_penalty, condition.energy_penalty)
