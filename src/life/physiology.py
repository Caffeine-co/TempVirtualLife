from __future__ import annotations

import math

from .actions import ActionDefinition
from .health import health_penalties
from .models import LifeConfig, LifeState, PerceptionFrame


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def advance_physiology(
    state: LifeState,
    action: ActionDefinition,
    perception: PerceptionFrame,
    hours: float,
    config: LifeConfig,
) -> None:
    """推进身体、认知和驱动力。

    这里使用可解释的低维模型，而不是伪装成医学级人体仿真。
    关键是所有参数都有明确的因果方向，后续可单独替换公式。
    """

    if hours <= 0:
        return

    body = state.character.body
    cognition = state.character.cognition
    drives = state.character.drives
    effects = action.effects
    _, health_pain, health_fatigue, health_energy_penalty = health_penalties(state)

    # 环境刺激目标值：噪声和拥挤越高、隐私越低，感官负担越高。
    env = perception.environment
    sensory_target = clamp(
        env.noise * 0.38
        + env.crowding * 0.25
        + (100 - env.privacy) * 0.12
        + (100 - env.comfort) * 0.12
        + abs(env.temperature_c - 22.0) * 2.0
        + abs(env.light - 60.0) * 0.05
    )

    if action.name == "sleep":
        # Process S 的简化指数下降。
        tau = config.rhythm.sleep_pressure_sleep_tau_hours
        body.sleep_pressure = clamp(body.sleep_pressure * math.exp(-hours / tau))
        body.energy = clamp(body.energy + 7.0 * hours - health_energy_penalty * 0.02 * hours)
        body.physical_fatigue = clamp(
            body.physical_fatigue - 6.0 * hours + health_fatigue * 0.02 * hours
        )
        body.sleep_debt = clamp(body.sleep_debt - 2.5 * hours)
        body.hunger = clamp(body.hunger + 1.5 * hours)
        body.hydration = clamp(body.hydration - 1.0 * hours)
        body.physiological_arousal = clamp(body.physiological_arousal - 5.0 * hours)
        body.sensory_load = clamp(body.sensory_load - 7.0 * hours)
        cognition.cognitive_load = clamp(cognition.cognitive_load - 8.0 * hours)
        cognition.rumination = clamp(cognition.rumination - 3.0 * hours)
        drives.social_energy = clamp(drives.social_energy + 3.0 * hours)
    else:
        # 清醒时 Process S 向 100 渐近。
        tau = config.rhythm.sleep_pressure_awake_tau_hours
        body.sleep_pressure = clamp(
            100 - (100 - body.sleep_pressure) * math.exp(-hours / tau)
        )
        debt_rate = max(0.0, body.sleep_pressure - 65.0) / 35.0
        body.sleep_debt = clamp(body.sleep_debt + debt_rate * 1.2 * hours)

        # 基础清醒消耗 + 行为影响 + 健康惩罚。
        body.energy = clamp(
            body.energy + (-1.2 + effects.energy - health_energy_penalty * 0.03) * hours
        )
        body.physical_fatigue = clamp(
            body.physical_fatigue
            + (1.0 + effects.fatigue + health_fatigue * 0.03) * hours
        )
        body.hunger = clamp(body.hunger + (3.0 + effects.hunger) * hours)
        body.hydration = clamp(body.hydration + (-2.0 + effects.hydration) * hours)
        # 生理唤醒会缓慢回到中性 40，再叠加当前行为刺激。
        arousal_return = 1 - math.exp(-hours / 2.0)
        body.physiological_arousal = clamp(
            body.physiological_arousal
            + (40.0 - body.physiological_arousal) * arousal_return
            + effects.arousal * hours
        )

        # sensory_load 不直接线性累加环境值，而是缓慢靠近环境目标，再叠加行为负担。
        approach_factor = 1 - math.exp(-hours / 0.75)
        body.sensory_load = clamp(
            body.sensory_load
            + (sensory_target - body.sensory_load) * approach_factor
            + effects.sensory_load * hours
        )

        cognition.cognitive_load = clamp(
            cognition.cognitive_load + (-1.0 + effects.cognitive_load) * hours
        )
        cognition.rumination = clamp(
            cognition.rumination + (-0.3 + effects.rumination) * hours
        )

        drives.social_need = clamp(
            drives.social_need + (0.8 + effects.social_need) * hours
        )
        drives.social_energy = clamp(
            drives.social_energy + (0.6 + effects.social_energy) * hours
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

    # 痛觉有一部分来自健康状态，但突发痛觉仍可由事件直接写 BodyState.pain。
    body.pain = clamp(max(body.pain * math.exp(-hours / 8.0), health_pain))
