from __future__ import annotations

from .models import AppraisalInput, LifeState, MeaningEvent


class RuleBasedAppraisal:
    """不依赖 LLM 的可解释 Appraisal。

    它不是在声称“精确模拟人类情绪”，而是给系统一条稳定的因果链：
    刺激维度 -> 对角色的意义 -> MeaningEvent。
    """

    def appraise(self, state: LifeState, stimulus: AppraisalInput) -> MeaningEvent:
        # 关系越亲近，社会评价越容易产生更强影响。
        relation_factor = 1.0
        if stimulus.related_entity:
            relation = state.relationships.get(stimulus.related_entity)
            if relation is not None:
                relation_factor += relation.closeness / 250.0
                relation_factor += relation.dependency / 400.0

        relevance = stimulus.relevance * relation_factor
        relevance = max(0.0, min(1.0, relevance))

        # goal_congruence 决定正负性；social_evaluation 作为社会评价修正。
        valence = (
            stimulus.goal_congruence * 0.75
            + stimulus.social_evaluation * 0.25
        ) * relevance

        # 新奇、威胁、紧迫性共同提高 arousal。
        arousal = (
            stimulus.novelty * 0.30
            + stimulus.threat * 0.45
            + stimulus.urgency * 0.25
        ) * relevance

        # 威胁高、控制感低时 stress 更强。
        stress = (
            stimulus.threat * 0.60
            + (1.0 - stimulus.controllability) * 0.30
            + max(0.0, -stimulus.goal_congruence) * 0.10
        ) * relevance

        # 用少量规则挑一个当前显著情绪标签。
        emotion = None
        if stimulus.social_evaluation < -0.45 and relevance > 0.45:
            emotion = "embarrassment"
        elif stimulus.threat > 0.6 and stimulus.controllability < 0.4:
            emotion = "anxiety"
        elif stimulus.goal_congruence > 0.55:
            emotion = "joy"
        elif stimulus.goal_congruence < -0.55 and stimulus.controllability > 0.6:
            emotion = "frustration"

        intensity = max(
            relevance,
            abs(valence),
            arousal,
            stress,
        )

        return MeaningEvent(
            occurred_at=stimulus.occurred_at,
            name=stimulus.name,
            intensity=max(0.0, min(1.0, intensity)),
            urgency=stimulus.urgency,
            valence=max(-1.0, min(1.0, valence)),
            arousal=max(-1.0, min(1.0, arousal)),
            stress=max(-1.0, min(1.0, stress)),
            emotion=emotion,
            emotion_half_life_hours=2.0,
            target_action=stimulus.target_action,
            related_entity=stimulus.related_entity,
            memory_salience=stimulus.memory_salience,
        )
