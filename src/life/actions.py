from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActionEffects:
    """行为执行期间，每小时叠加到基础动态上的影响。"""

    energy: float = 0.0
    fatigue: float = 0.0
    hunger: float = 0.0
    hydration: float = 0.0
    arousal: float = 0.0
    stress: float = 0.0
    sensory_load: float = 0.0
    cognitive_load: float = 0.0
    rumination: float = 0.0
    social_need: float = 0.0
    social_energy: float = 0.0
    creative_urge: float = 0.0
    achievement_urge: float = 0.0
    novelty_urge: float = 0.0


@dataclass(frozen=True)
class ActionDefinition:
    """一种行为的静态规则。真正正在执行的实例保存在 ActionState。"""

    name: str
    min_duration_minutes: float
    max_duration_minutes: float
    interruptibility: float
    commitment: float
    effects: ActionEffects = ActionEffects()


# 第一版正式行为集合仍保持通用，不放任何特定角色设定。
# 更具体的“上课、画插画、做饭”等应当以后通过 Goal/World/Action 扩展层映射，
# 而不是直接把角色设定写死进 Kernel。
def default_actions() -> dict[str, ActionDefinition]:
    items = [
        ActionDefinition(
            name="idle",
            min_duration_minutes=10,
            max_duration_minutes=30,
            interruptibility=0.95,
            commitment=0.10,
            effects=ActionEffects(energy=0.4, fatigue=-0.5, stress=-0.4, cognitive_load=-2.0),
        ),
        ActionDefinition(
            name="sleep",
            min_duration_minutes=360,
            max_duration_minutes=540,
            interruptibility=0.05,
            commitment=0.95,
        ),
        ActionDefinition(
            name="eat",
            min_duration_minutes=20,
            max_duration_minutes=40,
            interruptibility=0.45,
            commitment=0.55,
            effects=ActionEffects(energy=0.8, fatigue=-0.4, cognitive_load=-0.5),
        ),
        ActionDefinition(
            name="drink",
            min_duration_minutes=3,
            max_duration_minutes=10,
            interruptibility=0.85,
            commitment=0.20,
        ),
        ActionDefinition(
            name="rest",
            min_duration_minutes=20,
            max_duration_minutes=60,
            interruptibility=0.80,
            commitment=0.30,
            effects=ActionEffects(energy=4.0, fatigue=-4.0, stress=-3.0, cognitive_load=-5.0),
        ),
        ActionDefinition(
            name="socialize",
            min_duration_minutes=10,
            max_duration_minutes=90,
            interruptibility=0.70,
            commitment=0.40,
            effects=ActionEffects(
                energy=-1.0,
                fatigue=0.4,
                arousal=1.0,
                social_need=-15.0,
                social_energy=-7.0,
                novelty_urge=-1.0,
            ),
        ),
        ActionDefinition(
            name="communicate",
            min_duration_minutes=5,
            max_duration_minutes=45,
            interruptibility=0.80,
            commitment=0.30,
            effects=ActionEffects(
                energy=-0.5,
                arousal=0.5,
                cognitive_load=1.0,
                social_need=-10.0,
                social_energy=-5.0,
            ),
        ),
        ActionDefinition(
            name="create",
            min_duration_minutes=30,
            max_duration_minutes=150,
            interruptibility=0.45,
            commitment=0.70,
            effects=ActionEffects(
                energy=-1.5,
                fatigue=1.0,
                stress=0.3,
                cognitive_load=4.0,
                creative_urge=-12.0,
                achievement_urge=-1.5,
            ),
        ),
        ActionDefinition(
            name="work",
            min_duration_minutes=30,
            max_duration_minutes=180,
            interruptibility=0.30,
            commitment=0.80,
            effects=ActionEffects(
                energy=-2.0,
                fatigue=1.5,
                stress=1.2,
                cognitive_load=5.0,
                achievement_urge=-10.0,
            ),
        ),
        ActionDefinition(
            name="leisure",
            min_duration_minutes=20,
            max_duration_minutes=120,
            interruptibility=0.85,
            commitment=0.25,
            effects=ActionEffects(
                stress=-3.0,
                cognitive_load=-2.0,
                novelty_urge=-12.0,
                social_energy=0.5,
            ),
        ),
        ActionDefinition(
            name="travel",
            min_duration_minutes=5,
            max_duration_minutes=120,
            interruptibility=0.20,
            commitment=0.85,
            effects=ActionEffects(
                energy=-1.5,
                fatigue=1.5,
                hunger=0.5,
                hydration=-0.5,
                sensory_load=1.0,
            ),
        ),
    ]
    return {item.name: item for item in items}
