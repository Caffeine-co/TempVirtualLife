from __future__ import annotations

from .models import LifeState, RelationshipState
from .physiology import clamp


def apply_relationship_delta(
    state: LifeState,
    *,
    target_id: str,
    familiarity_delta: float = 0,
    closeness_delta: float = 0,
    trust_delta: float = 0,
    comfort_delta: float = 0,
    tension_delta: float = 0,
    dependency_delta: float = 0,
    occurred_at=None,
) -> RelationshipState:
    """更新具体关系边。不存在时创建一条中性关系。"""

    relation = state.relationships.get(target_id)
    if relation is None:
        relation = RelationshipState(target_id=target_id)
        state.relationships[target_id] = relation

    relation.familiarity = clamp(relation.familiarity + familiarity_delta)
    relation.closeness = clamp(relation.closeness + closeness_delta)
    relation.trust = clamp(relation.trust + trust_delta)
    relation.comfort = clamp(relation.comfort + comfort_delta)
    relation.tension = clamp(relation.tension + tension_delta)
    relation.dependency = clamp(relation.dependency + dependency_delta)
    if occurred_at is not None:
        relation.last_interaction_at = occurred_at
    return relation
