from __future__ import annotations

import math

from .models import AffectBaseline, LifeState, SalientEmotion


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def approach(current: float, target: float, half_life_hours: float, hours: float) -> float:
    """按半衰期让 current 平滑靠近 target。"""

    if hours <= 0:
        return current
    decay = math.exp(-math.log(2) * hours / half_life_hours)
    return target + (current - target) * decay


def advance_affect(
    state: LifeState,
    baseline: AffectBaseline,
    hours: float,
    *,
    action_stress_per_hour: float = 0.0,
    action_arousal_per_hour: float = 0.0,
) -> None:
    """推进核心情感并让显著情绪自然衰减。"""

    if hours <= 0:
        return

    affect = state.character.affect

    # 没有新事件时，核心情感缓慢回到人物长期基线。
    affect.valence = clamp(
        approach(affect.valence, baseline.valence, baseline.half_life_hours, hours),
        -100,
        100,
    )
    affect.arousal = clamp(
        approach(affect.arousal, baseline.arousal, baseline.half_life_hours, hours)
        + action_arousal_per_hour * hours
    )
    affect.stress = clamp(
        approach(affect.stress, baseline.stress, baseline.half_life_hours, hours)
        + action_stress_per_hour * hours
    )

    # 每个显著情绪拥有自己的半衰期，因此“尴尬”和“长期焦虑”不必同速消失。
    surviving: list[SalientEmotion] = []
    for emotion in affect.emotions:
        decayed = emotion.intensity * math.exp(
            -math.log(2) * hours / emotion.half_life_hours
        )
        # 低于 1 分后视为已经不再是当前显著情绪。
        if decayed >= 1:
            copied = emotion.model_copy(deep=True)
            copied.intensity = decayed
            surviving.append(copied)
    affect.emotions = surviving


def upsert_emotion(
    state: LifeState,
    *,
    name: str,
    intensity: float,
    started_at,
    half_life_hours: float,
    source: str | None,
) -> None:
    """同名显著情绪合并，而不是无限追加重复记录。"""

    for emotion in state.character.affect.emotions:
        if emotion.name == name:
            emotion.intensity = clamp(max(emotion.intensity, intensity))
            emotion.started_at = started_at
            emotion.half_life_hours = half_life_hours
            emotion.source = source
            return

    state.character.affect.emotions.append(
        SalientEmotion(
            name=name,
            intensity=clamp(intensity),
            started_at=started_at,
            half_life_hours=half_life_hours,
            source=source,
        )
    )
