from __future__ import annotations

from .health import health_penalties
from .models import DerivedState, LifeState
from .physiology import clamp


def derive_state(state: LifeState) -> DerivedState:
    """计算全部不持久化的指标。"""

    body = state.character.body
    cognition = state.character.cognition
    affect = state.character.affect
    action = state.character.action
    health_score, health_pain, _, _ = health_penalties(state)

    sleepiness = clamp(
        body.sleep_pressure * 0.55
        + body.physical_fatigue * 0.25
        + (100 - body.energy) * 0.20
    )
    thirst = clamp(100 - body.hydration)
    physical_stamina = clamp(
        body.energy * 0.45
        + (100 - body.physical_fatigue) * 0.30
        + health_score * 0.20
        + (100 - max(body.pain, health_pain)) * 0.05
    )
    attention = clamp(
        body.energy * 0.27
        + (100 - body.physical_fatigue) * 0.18
        + (100 - sleepiness) * 0.20
        + (100 - affect.stress) * 0.15
        + (100 - cognition.cognitive_load) * 0.12
        + (100 - cognition.rumination) * 0.08
    )
    mental_clarity = clamp(
        attention * 0.50
        + (100 - body.sensory_load) * 0.20
        + (100 - cognition.rumination) * 0.15
        + health_score * 0.15
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
        health_score=health_score,
        physical_stamina=physical_stamina,
        attention=attention,
        mental_clarity=mental_clarity,
        available_for_interruption=available_for_interruption,
        mood_label=mood_label,
    )
