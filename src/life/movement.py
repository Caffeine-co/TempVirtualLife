from __future__ import annotations

import heapq
import math

from .models import LifeConfig


class MovementService:
    """最小三维世界移动层：目前先解决语义地点之间的最短旅行时间。"""

    def __init__(self, config: LifeConfig):
        self._graph: dict[str, list[tuple[str, float]]] = {}

        # 把 WorldConfig 中的 links 建成邻接表。
        for place in config.world.places:
            self._graph.setdefault(place.place_id, [])
            for link in place.links:
                self._graph[place.place_id].append((link.to_place_id, link.minutes))
                if link.bidirectional:
                    self._graph.setdefault(link.to_place_id, []).append(
                        (place.place_id, link.minutes)
                    )

    def travel_minutes(self, start: str, destination: str) -> float | None:
        """Dijkstra 求最短旅行时间。不可达时返回 None。"""

        if start == destination:
            return 0.0
        if start not in self._graph:
            return None

        queue: list[tuple[float, str]] = [(0.0, start)]
        best: dict[str, float] = {start: 0.0}

        while queue:
            cost, node = heapq.heappop(queue)
            if node == destination:
                return cost
            if cost > best.get(node, math.inf):
                continue
            for neighbor, minutes in self._graph.get(node, []):
                new_cost = cost + minutes
                if new_cost < best.get(neighbor, math.inf):
                    best[neighbor] = new_cost
                    heapq.heappush(queue, (new_cost, neighbor))

        return None
