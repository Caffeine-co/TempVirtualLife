# 02. State and Ownership：每个状态到底归谁

Formal Core 的核心约束：**每个字段必须有明确 owner。**

## Character

### SpatialState

主要 owner：Movement / World Event。

- `place_id`：语义地点；
- `zone_id`：地点内部区域；
- `anchor_id`：更精细的语义位置；
- `position`：局部 3D 坐标；
- `posture` / `locomotion`：Action / Movement。

### BodyState

主要 owner：Physiology / Health / 少量事件。

LLM 原则上不得直接修改。

### CognitionState

只有 `cognitive_load`、`rumination` 两个持久量。

`attention`、`mental_clarity` 是 Derived State。

### AffectState

`valence/arousal/stress` 连续变化；`emotions` 只保存显著离散情绪。

### DriveState

它们存在的主要目的不是“描述人物”，而是进入 Behavior arbitration。

### ActionState

只有 Kernel / Behavior 能创建、完成和中断。

## World

`WorldState` 保存运行时环境 override、实体位置和 Adapter availability。

静态地图放 `LifeConfig.world`，避免快照每次重复保存地图定义。

## Goal

每一个 Goal 都绑定一个主要 `action_type`。BehaviorEngine 会把优先级、剩余进度、deadline 转成 utility bonus。

## Relationship

关系必须是：

```text
character -> target_id
```

而不是“总体友情 70”。

## Habit

习惯按上下文保存：

```text
place + weekday/weekend + daypart + action
```

完成行为后强化，长时间不用会自然衰减。

## Memory

Formal Core 只保存结构化 MemoryTrace，不负责用自然语言总结长期记忆。

未来 LLM Memory 可以作为更高层服务，但不能成为 Runtime State 的唯一来源。

## Derived

`derived.py` 当前包含：

```text
sleepiness
thirst
health_score
physical_stamina
attention
mental_clarity
available_for_interruption
mood_label
```

它们绝不能被写回数据库作为第二份真相。
