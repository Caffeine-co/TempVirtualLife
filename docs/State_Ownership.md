# 状态字段所有权与更新来源

这张表是 Life Core 后续扩展时最重要的约束之一。

原则：

> 每个状态都必须明确“谁可以修改它”。

如果以后新增字段时无法回答这个问题，就先不要把它加入 Runtime State。

## 1. Runtime 中真正持久化的状态

### SpatialState

| 字段 | 主要修改者 | 说明 |
|---|---|---|
| `place_id` | World / Schedule / Location Event | 语义地点 |
| `zone_id` | World / Location Event | 地点内部区域 |
| `anchor_id` | World / Location Event | 更精细的语义锚点 |
| `posture` | Action System | 第一版尚未自动变化 |

第一版 Schedule 为了简化，会在高刚性日程行为开始时直接修改 `place_id`。

这相当于暂时省略：

```text
当前位置
→ travel
→ 到达目标地点
```

后续加入 Movement/World 后应替换，而不是继续“瞬移”。

---

### BodyState

| 字段 | 更新时间尺度 | 主要修改者 |
|---|---|---|
| `energy` | 分钟~小时 | Time + Action |
| `physical_fatigue` | 分钟~小时 | Time + Action |
| `sleep_pressure` | 小时 | Sleep/Wake physiology |
| `sleep_debt` | 小时~天 | Sleep/Wake physiology |
| `hunger` | 分钟~小时 | Time + Eat Action |
| `hydration` | 分钟~小时 | Time + Drink Action |
| `pain` | 事件型 | 未来 Health/Event System |
| `physiological_arousal` | 分钟 | Time + Action + Event |
| `sensory_load` | 分钟 | Action，未来由 Perception 驱动 |
| `health` | 天~更久/事件型 | 未来 Health System |

LLM 原则上不直接修改这一层数值。

---

### AffectState

| 字段 | 更新时间尺度 | 主要修改者 |
|---|---|---|
| `valence` | 秒~小时 | Appraisal Event + 自然回归 |
| `arousal` | 秒~小时 | Event + Action + 自然回归 |
| `stress` | 分钟~天 | Event + Action + 自然回归 |

未来 LLM 可以参与 **Appraisal**：

```text
原始事件
→ LLM 判断意义
→ 结构化 ImpulseEvent
→ Kernel 改 Affect
```

但不推荐：

```text
LLM → new valence = 37
```

---

### DriveState

| 字段 | 更新时间尺度 | 主要修改者 |
|---|---|---|
| `social_need` | 小时 | Time + Social Action |
| `social_energy` | 分钟~小时 | Time + Social Action + Sleep |
| `creative_urge` | 小时 | Time + Create Action |
| `achievement_urge` | 小时 | Time + Work Action |
| `novelty_urge` | 小时 | Time + Leisure Action |

这些值的目的不是“完整描述心理”，而是给 BehaviorEngine 一个足够小的行为驱动空间。

---

### ActionState

| 字段 | 主要修改者 |
|---|---|
| `type` | Behavior / Schedule / External Impulse |
| `started_at` | Kernel |
| `expected_end_at` | Kernel / Behavior |
| `progress` | Time advance |
| `interruptibility` | Action Definition |
| `commitment` | Action Definition |
| `source` | Kernel |
| `target` | Planner / Event |

其他模块不能直接把：

```python
state.action.type = "xxx"
```

作为正常业务逻辑。

---

# 2. 不持久化的派生状态

`derived.py` 当前提供：

```text
sleepiness
thirst
physical_stamina
attention
mental_clarity
available_for_interruption
mood_label
```

它们没有自己的更新逻辑。

每次需要时：

```python
derive_state(state)
```

重新计算。

因此永远不会出现：

```text
hydration 已经改变
但 thirst 忘记更新
```

这种“双真相”问题。

---

# 3. Runtime 以外的长期参数

这些参数不会在每次状态推进中被重写。

## BiologicalRhythm

```text
preferred_sleep_hour
preferred_wake_hour
sleep_pressure_awake_tau_hours
sleep_pressure_sleep_tau_hours
```

归属：长期生理/生活规律。

## BehavioralProfile

```text
social_reward
creative_reward
achievement_reward
novelty_reward
persistence
impulsivity
```

归属：稳定行为先验。

当前代码中：

```text
reward 参数
→ 改变不同活动的 Utility

persistence
→ 提高从当前行为切走的门槛

impulsivity
→ 提高相近选择之间的决策噪声
```

它们都实际参与运算，不是仅用于“描述人物”的装饰字段。

---

# 4. 当前尚未实现，但未来应该独立的数据域

不要直接塞回 `CharacterRuntimeState`：

```text
RelationshipState
GoalTaskState
MemoryState
WorldState
PerceptionFrame
HealthHistory
HabitState
```

它们可以影响 Runtime，却应该各自拥有自己的更新规则与时间尺度。

例如：

```text
RelationshipState
     ↓
Appraisal
     ↓
ImpulseEvent
     ↓
Affect / Behavior
```

而不是把几十个“友情平均值”重新塞进角色实时状态。
