from __future__ import annotations

from .models import EnvironmentState, LifeConfig, LifeState, PlaceDefinition, WorldEntity


class WorldService:
    """静态地图定义 + 运行时世界状态的查询服务。"""

    def __init__(self, config: LifeConfig):
        # 用字典缓存 place_id -> PlaceDefinition，后续查询是 O(1)。
        self.places: dict[str, PlaceDefinition] = {
            place.place_id: place for place in config.world.places
        }

    def has_place(self, place_id: str) -> bool:
        return place_id in self.places

    def environment_at(self, state: LifeState, place_id: str) -> EnvironmentState:
        # 运行时 override 的优先级最高。
        if place_id in state.world.environment_overrides:
            return state.world.environment_overrides[place_id].model_copy(deep=True)

        # 如果配置里定义了这个地点，则使用它的默认环境。
        place = self.places.get(place_id)
        if place is not None:
            return place.default_environment.model_copy(deep=True)

        # 未定义地点也必须能运行，因此退化为中性默认环境。
        return EnvironmentState()

    def nearby_entities(self, state: LifeState) -> list[WorldEntity]:
        spatial = state.character.spatial
        result: list[WorldEntity] = []

        for entity in state.world.entities.values():
            if not entity.active:
                continue
            if entity.place_id != spatial.place_id:
                continue
            # zone_id 只有双方都明确时才要求相等；未知 zone 不做过度过滤。
            if spatial.zone_id and entity.zone_id and spatial.zone_id != entity.zone_id:
                continue
            result.append(entity.model_copy(deep=True))

        return result
