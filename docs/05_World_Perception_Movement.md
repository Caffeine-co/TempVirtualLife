# 05. World / Perception / Movement

## WorldConfig vs WorldState

### WorldConfig

静态：

```text
有哪些地点
默认环境
地点之间旅行时间
```

### WorldState

动态：

```text
临时环境变化
当前实体
通信 Adapter 是否在线
```

## Environment

当前支持：

```text
noise
crowding
privacy
comfort
temperature
light
```

Physiology 会把环境转换为 `sensory_load` 目标值。

## Entity

同一 place/zone 的 active entity 会进入 `PerceptionFrame.nearby_entities`。

线下 `socialize` 只有附近存在 `kind="person"` 时才进入候选。

## Adapter

通信渠道也是世界能力：

```text
onebot=True
web=False
```

没有任何在线 Adapter 时，`communicate` 不进入 Behavior 候选。

## Movement

地图边使用：

```json
{"to_place_id":"school","minutes":20,"bidirectional":true}
```

`MovementService` 用 Dijkstra 算最短旅行时间。

目前移动粒度是“地点之间旅行”，不是逐帧 3D NavMesh。

未来接 Unity/Godot 时，`position: Vec3` 和 `travel` Action 可以继续作为高层语义，低层导航由 3D 客户端执行。

## Home Base

`LifeConfig.home_place_id` 是生活基地，不是硬日程。角色离开 home 后，在睡眠时相或疲劳升高时，`travel(home)` 会作为普通 Utility 候选出现，因此可以自然回家。
