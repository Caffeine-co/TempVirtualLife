# 08：Event、Appraisal 和“外界如何进入生命”

## 1. Event 是唯一正常外部写入口

外部系统只表达：

```text
发生了什么
```

例如：

```python
AdapterAvailabilityEvent(
    adapter="onebot",
    available=True,
)
```

而不直接：

```python
state.world.adapters["onebot"] = True
```

这样才能统一时间顺序、Journal、事务与 Behavior reconsider。

## 2. 当前 Event

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

## 3. `occurred_at`

Runtime 根据它保证：

```text
先 advance 到事件时刻
→ handle_event
→ 再 advance 到现在
```

## 4. `AppraisalInput` 还不是 Event

它描述一个结构化刺激：

```text
relevance
goal_congruence
controllability
novelty
social_evaluation
threat
urgency
related_entity
target_action
memory_salience
```

还没有作用到状态。

## 5. `RuleBasedAppraisal`

调用：

```python
meaning = appraisal.appraise(state, stimulus)
```

输出：

```text
MeaningEvent
```

它本身不修改 `LifeState`。

## 6. Relationship 如何影响 Appraisal

若有 `related_entity`：

```text
closeness
dependency
```

会提高 relation factor。

所以同一句评价来自陌生人和来自亲近对象，可以有不同 relevance。

## 7. Appraisal 计算什么

粗略：

```text
valence
← goal congruence + social evaluation

arousal
← novelty + threat + urgency

stress
← threat + low controllability + negative congruence
```

然后少量规则选择显著 emotion：

```text
embarrassment
anxiety
joy
frustration
```

## 8. MeaningEvent 进入 Kernel 后

顺序：

```text
① 修改 core affect
② upsert salient emotion
③ related entity → familiarity 小幅增加
④ memory_salience > 0 → MemoryTrace
⑤ target_action 存在时检查是否允许打断
```

## 9. 为什么紧急刺激不直接打断

```python
interrupt_score =
    urgency *
    current_action.interruptibility
```

例如：

```text
urgency=0.8
work interruptibility=0.30
→ 0.24
```

默认阈值 0.35，所以继续 work。

leisure interruptibility=0.85：

```text
0.68
```

才进入重新决策。

## 10. 通过中断阈值后也不是强制

只是：

```python
external_bonus = {
    target_action: urgency * 80
}
```

然后重新走 BehaviorEngine。

所以外界刺激仍然要与：

```text
Schedule
Goal
Habit
Memory
当前行为惯性
```

一起竞争。

## 11. 未来 LLM 正确插入点

```text
自然语言/图片/聊天上下文
→ LLM 语义理解
→ AppraisalInput 或 MeaningEvent
→ runtime.submit()
```

不应该：

```text
LLM → 完整 LifeState
```

## 12. 一个完整社交刺激

```python
AppraisalInput(
    relevance=0.8,
    goal_congruence=-0.4,
    controllability=0.3,
    novelty=0.6,
    social_evaluation=-0.8,
    threat=0.4,
    urgency=0.5,
    related_entity="person_A",
    target_action="communicate",
    memory_salience=0.7,
)
```

链路：

```text
Appraisal
→ MeaningEvent
→ Affect
→ Emotion
→ Familiarity
→ Memory
→ interrupt check
→ Behavior reconsider
```

这就是当前完整的“外界→心理→行为”入口。
