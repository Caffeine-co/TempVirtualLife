from __future__ import annotations

from .models import LifeState, PerceptionFrame
from .world import WorldService


class PerceptionService:
    """把客观 WorldState 转换成“角色此刻实际可获得的环境快照”。"""

    def __init__(self, world: WorldService):
        self.world = world

    def frame(self, state: LifeState) -> PerceptionFrame:
        place_id = state.character.spatial.place_id
        environment = self.world.environment_at(state, place_id)
        nearby_entities = self.world.nearby_entities(state)
        available_adapters = [
            name for name, available in state.world.adapters.items() if available
        ]
        return PerceptionFrame(
            environment=environment,
            nearby_entities=nearby_entities,
            available_adapters=available_adapters,
        )
