# 06：World、Perception、Movement、Schedule 如何连起来

## 1. World 分静态和动态

静态地图：`LifeConfig.world`

```text
PlaceDefinition
├─ place_id
├─ default_environment
└─ links
```

动态世界：`LifeState.world`

```text
environment_overrides
entities
adapters
```

例如 OneBot 是否在线、某个人现在在哪、今天某地点是否特别吵，都属于动态世界。

## 2. `WorldService`

### `environment_at()`

优先级：

```text
runtime override
→ place default environment
→ 中性默认 EnvironmentState
```

### `nearby_entities()`

返回：

```text
active
且 place_id 相同
且明确 zone 冲突时排除
```

当前不是 3D 遮挡/视锥，只是语义地点级过滤。

## 3. Perception 为什么独立

```text
WorldState + 当前 Spatial
→ PerceptionFrame
```

输出：

```text
environment
nearby_entities
available_adapters
```

Behavior 应该消费“角色能获得什么”，而不是直接消费所有客观世界事实。

未来才能加入：

```text
遮挡
听觉距离
注意过滤
设备静音
```

而不改 Behavior 接口。

## 4. Perception 已如何影响行为

没有 nearby person：

```text
socialize 不进入候选
```

没有 online adapter：

```text
communicate 不进入候选
```

环境：

```text
noise/crowding/privacy...
→ sensory_target
→ sensory_load
→ attention/mental_clarity
```

## 5. Movement

`MovementService` 把 `Place.links` 建成图，用 Dijkstra 求最短旅行时间。

例如：

```text
home --10--> station --20--> school
home --50-----------------> school
```

返回 30min。

## 6. travel 是 Action

不是：

```python
state.place_id = school
```

而是：

```text
BehaviorDecision(travel)
→ ActionState(travel)
→ 时间推进
→ travel completed
→ place_id = destination
```

所以移动也会消耗 energy、增加 fatigue。

## 7. Schedule 只回答事实

`ScheduleService`：

```text
active_blocks
primary_hard_block
next_hard_start_after
next_boundary_after
```

不直接修改角色。

## 8. 跨午夜日程

例如：

```text
23:00~02:00
```

`end <= start` 时自动把 end 加一天。

查询当前 active block 时还会检查昨天，确保 01:00 仍能识别前一晚日程。

## 9. hard vs soft

hard：

```text
直接优先 BehaviorDecision
```

soft：

```text
给对应 action 增加 bonus
```

## 10. 09:00 上班完整链

配置：

```text
home → work_area = 25min
hard schedule:
09:00~12:00 work @ work_area
```

08:00：

```text
next_required_departure_time()
→ 08:35
```

08:35：

```text
Kernel departure boundary
→ reconsider
→ upcoming hard travel
→ travel(work_area, 25min)
```

09:00：

```text
travel complete
→ place=work_area
→ hard schedule active
→ work
```

这条链说明：

```text
日程事实
→ 推导出通勤行为
→ 到达后执行日程行为
```
