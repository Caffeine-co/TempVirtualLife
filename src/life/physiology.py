from __future__ import annotations

import math

from .actions import ActionDefinition
from .models import CharacterRuntimeState, LifeConfig


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def approach(current: float, target: float, half_life_hours: float, hours: float) -> float:
    """按半衰期平滑靠近 target。"""

    if hours <= 0:
        return current
    decay = math.exp(-math.log(2) * hours / half_life_hours)
    return target + (current - target) * decay


def advance_continuous(
    state: CharacterRuntimeState,
    action: ActionDefinition,
    hours: float,
    config: LifeConfig,
) -> None:
    """让基础状态随时间连续变化。

    第一版故意保持可读：只有少量明确规则，不假装已经是完整人体模型。
    后续可以逐层替换为更严谨的生理/心理模型，而 Runtime API 不需要改变。
    """

    if hours <= 0:
        return

    body = state.body
    affect = state.affect
    drives = state.drives
    effects = action.effects

    if action.name == "sleep":
        # 两过程睡眠模型中的 Process S 在这里先用指数下降近似。
        tau = config.rhythm.sleep_pressure_sleep_tau_hours
        body.sleep_pressure = clamp(body.sleep_pressure * math.exp(-hours / tau))
        body.energy = clamp(body.energy + 7.0 * hours)
        body.physical_fatigue = clamp(body.physical_fatigue - 6.0 * hours)
        body.sleep_debt = clamp(body.sleep_debt - 2.5 * hours)
        body.hunger = clamp(body.hunger + 1.5 * hours)
        body.hydration = clamp(body.hydration - 1.0 * hours)
        body.physiological_arousal = clamp(body.physiological_arousal - 5.0 * hours)
        body.sensory_load = clamp(body.sensory_load - 6.0 * hours)
        drives.social_energy = clamp(drives.social_energy + 3.0 * hours)
    else:
        # 清醒期间 Process S 逐步向 100 靠近。
        tau = config.rhythm.sleep_pressure_awake_tau_hours
        body.sleep_pressure = clamp(
            100 - (100 - body.sleep_pressure) * math.exp(-hours / tau)
        )
        debt_rate = max(0.0, body.sleep_pressure - 65.0) / 35.0
        body.sleep_debt = clamp(body.sleep_debt + debt_rate * 1.2 * hours)

        # 清醒状态的基础变化，再叠加行为自身影响。
        body.energy = clamp(body.energy + (-1.2 + effects.energy) * hours)
        body.physical_fatigue = clamp(
            body.physical_fatigue + (1.0 + effects.fatigue) * hours
        )
        body.hunger = clamp(body.hunger + (3.0 + effects.hunger) * hours)
        body.hydration = clamp(body.hydration + (-2.0 + effects.hydration) * hours)
        body.physiological_arousal = clamp(
            body.physiological_arousal + effects.arousal * hours
        )
        body.sensory_load = clamp(body.sensory_load + effects.sensory_load * hours)

        drives.social_need = clamp(drives.social_need + (0.8 + effects.social_need) * hours)
        drives.social_energy = clamp(
            drives.social_energy + (0.8 + effects.social_energy) * hours
        )
        drives.creative_urge = clamp(
            drives.creative_urge + (0.6 + effects.creative_urge) * hours
        )
        drives.achievement_urge = clamp(
            drives.achievement_urge + (0.6 + effects.achievement_urge) * hours
        )
        drives.novelty_urge = clamp(
            drives.novelty_urge + (0.5 + effects.novelty_urge) * hours
        )

    # 情感没有新事件时缓慢回归基线；行为可叠加额外压力变化。
    baseline = config.affect_baseline
    affect.valence = clamp(
        approach(affect.valence, baseline.valence, baseline.half_life_hours, hours),
        -100,
        100,
    )
    affect.arousal = clamp(
        approach(affect.arousal, baseline.arousal, baseline.half_life_hours, hours)
        + effects.arousal * hours
    )
    affect.stress = clamp(
        approach(affect.stress, baseline.stress, baseline.half_life_hours, hours)
        + effects.stress * hours
    )
