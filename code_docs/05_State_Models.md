# 05：`models.py` 按“数据寿命”理解

`models.py` 很长，不要逐类背。

## 1. Canonical Runtime State

真正进 Snapshot：

```text
LifeState
├─ revision
├─ as_of
├─ character
├─ world
├─ health
├─ goals
├─ relationships
├─ habits
└─ memories
```

### `CharacterState`

只放角色自身当前状态：

```text
spatial
body
cognition
affect
drives
action
```

World、Goal、Relationship 不再塞进 CharacterState。

## 2. `SpatialState`

层级：

```text
place_id    语义地点
zone_id     地点内部区域
anchor_id   床/座位/桌子等语义锚点
position    局部 3D 坐标
posture     姿态
locomotion  移动状态
```

当前主逻辑主要使用 `place_id`。

## 3. `BodyState`

保存基础自由变量：

```text
energy
physical_fatigue
sleep_pressure
sleep_debt
hunger
hydration
pain
physiological_arousal
sensory_load
```

没有：

```text
sleepiness
thirst
physical_stamina
```

因为这些是 Derived。

## 4. `CognitionState`

只保存需要历史连续性的：

```text
cognitive_load
rumination
```

而：

```text
attention
mental_clarity
```

从多项基础状态派生。

## 5. `AffectState`

```text
valence
arousal
stress
emotions[]
```

前三个是连续 core affect。

`emotions[]` 只保存当前显著离散情绪：

```python
SalientEmotion(
    name="anxiety",
    intensity=70,
    half_life_hours=4,
    source="..."
)
```

## 6. `DriveState`

不是人格，是 BehaviorEngine 当前消费的动态驱动力：

```text
social_need
social_energy
creative_urge
achievement_urge
novelty_urge
```

长期倾向在 `LifeConfig.profile`。

## 7. `ActionState`

字段：

```text
type                  做什么
started_at            开始时间
expected_end_at       预计结束
progress              当前进度
interruptibility      容易被打断吗
commitment            倾向持续吗
source                 为什么开始
target                 对谁/什么执行
destination_place_id  travel 去哪里
habit_context_key     行为开始时习惯上下文
```

## 8. 独立长期/社会域

### HealthState

`conditions[name] -> HealthCondition`

一个健康问题有自己的 severity、恢复半衰期、pain/fatigue/energy 影响。

### GoalState

描述：

```text
action_type
priority
progress
deadline
target
required_place_id
status
```

### RelationshipState

每个 `target_id` 一条具体关系边。

### HabitState

记录某上下文某行为的 strength/repetitions。

### MemoryTrace

结构化记忆：

```text
occurred_at
salience
valence
related_entity
tags
action_bias
note
```

## 9. World Runtime

`WorldState`：

```text
environment_overrides
entities
adapters
```

静态地图在：

```text
LifeConfig.world
```

动态世界在：

```text
LifeState.world
```

## 10. Config

`LifeConfig` 是规则/长期先验：

```text
timezone
database_path
home_place_id
initial
rhythm
profile
affect_baseline
habit tuning
memory tuning
runtime tuning
static world
weekly schedule
```

普通运行时不把这些当动态状态。

## 11. Event

所有正常外部写入都通过 `LifeEvent`：

```text
MeaningEvent
LocationChangedEvent
ForceActionEvent
WorldEnvironmentEvent
EntityPresenceEvent
AdapterAvailabilityEvent
GoalUpsertEvent
GoalProgressEvent
RelationshipEvent
HealthImpactEvent
MemoryEvent
```

`type` 是 discriminator，Pydantic 根据它恢复具体 Event 类型。

## 12. Derived / View

不进 Snapshot：

```text
PerceptionFrame
DerivedState
RuntimeView
```

`get_view()` 返回：

```text
Canonical LifeState
+ 当前 Perception
+ 当前 Derived 指标
```

## 13. `SchemaModel`

```python
extra="forbid"
validate_assignment=True
```

意义：

- 拼错字段立刻报错；
- 运行时赋值也继续检查范围；
- 不让旧配置/错误字段悄悄混进状态。
