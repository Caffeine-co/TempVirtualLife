from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActionEffects:
    """行为每小时对基础状态产生的附加变化。

    注意：这些值会叠加在清醒时的基础代谢/疲劳变化之上。
    sleep 是特殊行为，在 physiology.py 里单独处理。
    """

    energy: float = 0.0
    fatigue: float = 0.0
    hunger: float = 0.0
    hydration: float = 0.0
    arousal: float = 0.0
    stress: float = 0.0
    sensory_load: float = 0.0
    social_need: float = 0.0
    social_energy: float = 0.0
    creative_urge: float = 0.0
    achievement_urge: float = 0.0
    novelty_urge: float = 0.0


@dataclass(frozen=True)
class ActionDefinition:
    name: str
    min_duration_minutes: float
    max_duration_minutes: float
    interruptibility: float
    commitment: float
    effects: ActionEffects = ActionEffects()


def default_actions() -> dict[str, ActionDefinition]:
    """不依赖具体角色的通用行为集合。"""

    items = [
        ActionDefinition(
            name="idle",
            min_duration_minutes=10,
            max_duration_minutes=30,
            interruptibility=0.95,
            commitment=0.10,
            effects=ActionEffects(energy=0.5, fatigue=-0.5, stress=-0.5),
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
            effects=ActionEffects(energy=1.0, fatigue=-0.5),
        ),
        ActionDefinition(
            name="drink",
            min_duration_minutes=5,
            max_duration_minutes=10,
            interruptibility=0.80,
            commitment=0.25,
        ),
        ActionDefinition(
            name="rest",
            min_duration_minutes=20,
            max_duration_minutes=60,
            interruptibility=0.80,
            commitment=0.30,
            effects=ActionEffects(energy=4.0, fatigue=-4.0, stress=-3.0),
        ),
        ActionDefinition(
            name="socialize",
            min_duration_minutes=10,
            max_duration_minutes=60,
            interruptibility=0.75,
            commitment=0.35,
            effects=ActionEffects(
                energy=-1.0,
                fatigue=0.5,
                arousal=1.0,
                social_need=-16.0,
                social_energy=-8.0,
            ),
        ),
        ActionDefinition(
            name="create",
            min_duration_minutes=30,
            max_duration_minutes=120,
            interruptibility=0.45,
            commitment=0.70,
            effects=ActionEffects(
                energy=-1.5,
                fatigue=1.0,
                stress=0.5,
                creative_urge=-12.0,
                achievement_urge=-2.0,
            ),
        ),
        ActionDefinition(
            name="work",
            min_duration_minutes=30,
            max_duration_minutes=120,
            interruptibility=0.30,
            commitment=0.80,
            effects=ActionEffects(
                energy=-2.0,
                fatigue=1.5,
                stress=1.5,
                achievement_urge=-10.0,
            ),
        ),
        ActionDefinition(
            name="leisure",
            min_duration_minutes=20,
            max_duration_minutes=90,
            interruptibility=0.85,
            commitment=0.25,
            effects=ActionEffects(
                stress=-3.0,
                novelty_urge=-12.0,
                social_energy=1.0,
            ),
        ),
    ]
    return {item.name: item for item in items}
