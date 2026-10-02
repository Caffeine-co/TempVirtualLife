# 07：Physiology / Affect / Health / Goal / Habit / Memory / Relationship

这些模块不是“为了拆文件而拆文件”，而是因为它们的变化原因和时间尺度不同。

## 1. Physiology：分钟～小时连续变化

文件：

```text
physiology.py
```

负责：

```text
Body
Cognition
Drive
```

的连续推进。

环境先通过 Perception 变成：

```text
sensory_target
```

然后 `sensory_load` 平滑靠近目标，而不是瞬间等于环境噪音。

## 2. Sleep pressure

清醒：

```text
向 100 指数渐近
```

睡眠：

```text
向 0 指数下降
```

参数来自 `BiologicalRhythm`。

这样作息可以通过配置控制，不依赖 LLM 常识。

## 3. Affect

文件：

```text
affect.py
```

Core affect：

```text
valence
arousal
stress
```

没有新事件时，按半衰期缓慢回到 baseline。

显著 Emotion：

```text
intensity
half_life_hours
source
```

各自独立衰减。

同名 emotion 再次发生时 `upsert`，不会无限追加重复项。

## 4. Health

文件：

```text
health.py
```

HealthCondition 不是一个瞬时 health 分数，而是持续状态：

```text
severity
started_at
recovery_half_life
pain_effect
fatigue_effect
energy_penalty
```

`advance_health()` 让 severity 衰减。

`health_penalties()` 把多个 condition 汇总成：

```text
health_score
pain
fatigue penalty
energy penalty
```

供 Physiology/Derived 使用。

## 5. Goal

文件：

```text
goals.py
```

Goal 驱动力：

```text
priority × remaining
+ deadline urgency
```

它只给对应 action 增加 bonus，不直接命令角色。

Goal progress：

```python
progress += duration_hours * progress_per_hour
```

且要求 `action_type` 匹配；若 Goal 设置 target，还要求 target 匹配。

## 6. Habit

文件：

```text
habits.py
```

Habit 表示：

> 在某个上下文重复执行某行为后，下次处于相同上下文时更容易继续做它。

上下文：

```text
place
+ weekday/weekend
+ daypart
```

强化：

```text
new_strength
=
effective_strength
+
learning_rate × (1-effective_strength)
```

长期不用则按 half-life 衰减。

## 7. Memory

文件：

```text
memory.py
```

当前 MemoryTrace 是结构化、低成本记忆层。

最重要的行为作用：

```text
action_bias
```

例如：

```python
{"communicate": -20}
```

近期会降低 communicate 倾向，随后随时间衰减。

总 Memory 行为影响限制在 ±40。

超过 `max_records` 后，保留更显著、更新的记录。

## 8. Relationship

文件：

```text
relationships.py
```

每个 target 是独立关系边：

```text
familiarity
closeness
trust
comfort
tension
dependency
last_interaction
```

首次创建时 trust/comfort 是中性 50。

## 9. MeaningEvent 为什么只自动改 familiarity

一次有意义互动可以合理说明：

```text
“更熟悉了一点”
```

但不能自动说明：

```text
trust +10
closeness +20
```

所以复杂关系价值变化必须显式使用 `RelationshipEvent`。

## 10. 最终它们怎样进入行为

```text
Body / Drive
→ base Utility

Affect
→ rest/create 等基础分

Goal
→ directed bonus

Memory
→ directed bonus

Habit
→ habitual branch

Relationship
→ Appraisal relevance

Health
→ Physiology + Derived

World/Perception
→ 候选可行性 + sensory load
```

它们不是“平铺参数”，而是进入不同因果环节。
