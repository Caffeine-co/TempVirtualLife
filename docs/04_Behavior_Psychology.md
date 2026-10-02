# 04. Behavior / Psychology Model

## 1. Behavior 不是 random choice

Formal Core 使用：

```text
Hard Constraint
+
Goal-directed Utility
+
Habit
+
Memory influence
+
bounded decision noise
+
Hysteresis
```

## 2. Goal-directed Utility

例如：

```text
sleep <- sleep pressure + fatigue + circadian drive
eat <- hunger
drink <- dehydration
rest <- fatigue + low energy + stress
create <- creative urge + energy - stress
work <- achievement urge + energy - fatigue
```

同时叠加：

```text
soft schedule
goal urgency
memory action bias
external impulse
```

## 3. Habit

Habit 不是直接覆盖理性系统。

当前仲裁：

```text
final score
=
goal_weight * goal_directed_score
+
habit_weight * habit_score
+
small noise
```

低注意力、高认知负荷会降低 goal-directed weight。

## 4. Hysteresis

普通重新决策时：

```text
new_score <= current_score + switch_threshold
→ continue current action
```

threshold 还会受：

```text
current action commitment
profile.persistence
```

影响。

所以角色不会因为新行为只高 1 分就立刻切换。

## 5. Affect

连续底座：

```text
valence
arousal
stress
```

显著情绪：

```text
SalientEmotion(name, intensity, half_life)
```

无新事件时逐渐回归 baseline。

## 6. Appraisal

`RuleBasedAppraisal` 接收已经结构化的刺激：

```text
relevance
goal_congruence
controllability
novelty
social_evaluation
threat
urgency
```

输出 `MeaningEvent`。

未来 LLM 只需要补“自然语言 -> 这些 appraisal 维度”的能力，不必重新设计 Kernel。

## 7. Sleep

`physiology.py` 当前对 Process S 使用指数形式：

```text
awake -> sleep_pressure 向 100 渐近
sleep -> sleep_pressure 向 0 衰减
```

`behavior.py` 的 circadian sleep drive 是 Process C 的工程近似。

以后可以提高生理模型精度，但接口不变。
