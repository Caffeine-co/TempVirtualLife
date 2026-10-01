from __future__ import annotations

from .models import CharacterRuntimeState, DerivedState
from .physiology import clamp


def derive_state(state: CharacterRuntimeState) -> DerivedState:
    """计算不需要持久化的派生指标。"""

    body = state.body
    affect = state.affect
    action = state.action

    sleepiness = clamp(
        body.sleep_pressure * 0.55
        + body.physical_fatigue * 0.25
        + (100 - body.energy) * 0.20
    )
    thirst = clamp(100 - body.hydration)
    physical_stamina = clamp(
        body.energy * 0.45
        + (100 - body.physical_fatigue) * 0.30
        + body.health * 0.20
        + (100 - body.pain) * 0.05
    )
    attention = clamp(
        body.energy * 0.30
        + (100 - body.physical_fatigue) * 0.20
        + (100 - sleepiness) * 0.25
        + (100 - affect.stress) * 0.20
        + (100 - body.pain) * 0.05
    )
    mental_clarity = clamp(
        attention * 0.55
        + (100 - body.sensory_load) * 0.20
        + (100 - affect.arousal) * 0.10
        + body.health * 0.15
    )

    interruptibility = action.interruptibility if action else 1.0
    available_for_interruption = clamp(interruptibility * attention)

    if affect.valence >= 35 and affect.arousal >= 55:
        mood_label = "positive_active"
    elif affect.valence >= 35:
        mood_label = "positive_calm"
    elif affect.valence <= -35 and affect.arousal >= 55:
        mood_label = "negative_active"
    elif affect.valence <= -35:
        mood_label = "negative_low"
    else:
        mood_label = "neutral"

    return DerivedState(
        sleepiness=sleepiness,
        thirst=thirst,
        physical_stamina=physical_stamina,
        attention=attention,
        mental_clarity=mental_clarity,
        available_for_interruption=available_for_interruption,
        mood_label=mood_label,
    )
