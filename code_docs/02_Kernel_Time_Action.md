# 02：`LifeKernel`、时间推进与 Action 生命周期

## 1. Kernel 本质只有两个问题

```python
advance_to(state, target_time)
```

时间过去会发生什么？

```python
handle_event(state, event)
```

离散事件发生会怎样？

Kernel 不读真实时间，不碰 SQLite，不知道 NoneBot。

## 2. `initialize()`

如果：

```python
state.character.action is None
```

则：

```text
Perception
→ Behavior.decide()
→ _apply_decision()
```

保证生命始终有当前行为。

## 3. `next_wakeup_time()`

内部重要边界：

```text
Action expected_end_at
Schedule start/end
Goal deadline
Hard schedule 最晚出发时间
```

Runtime 可直接睡到最近一个。

## 4. `advance_to()` 核心循环

```python
while state.as_of < target_time:
    boundary = min(
        target_time,
        action_end,
        schedule_boundary,
        goal_deadline,
        departure_boundary,
    )

    hours = boundary - state.as_of

    advance_health(...)
    advance_physiology(...)
    advance_affect(...)

    state.as_of = boundary
    update_action_progress()

    处理 boundary 上的离散变化
```

为什么必须找最近边界？

假设：

```text
10:00 work
10:40 work 结束
11:00 schedule
12:00 target
```

不能直接把 `work` 的 effects 算到 12:00。

## 5. 连续推进顺序

当前：

```text
advance_health
→ advance_physiology
→ advance_affect
```

Health 先恢复，再由 Physiology 查询最新健康惩罚。

## 6. `ActionDefinition` vs `ActionState`

`ActionDefinition`：

```text
一种行为的静态规则
持续范围
interruptibility
commitment
effects
```

`ActionState`：

```text
这一次具体行为实例
started_at
expected_end_at
progress
target
destination
```

## 7. 连续 effects 与完成 effects

连续：

```text
ActionEffects × hours
```

例如 work 每小时增加 fatigue/cognitive load。

完成：

```text
eat 完成 → hunger -40
drink 完成 → hydration +30
travel 完成 → place_id 改变
```

两者语义不同。

## 8. `_complete_current_action()`

顺序：

```text
action_completed Journal
→ 离散完成效果
→ travel arrival（若有）
→ Goal progress
→ Habit reinforce
→ action=None
```

然后 `advance_to()` 再选下一 Action。

## 9. 为什么 Goal/Habit 完成后才更新

如果行为一开始就奖励：

```text
work 开始 1 秒后被打断
```

也会得到完整 Goal/Habit 奖励。

所以当前坚持：

> 真正做完才形成完成型学习与进度。

## 10. `_reconsider()` 与 Action complete

Action complete：

```text
旧行为已结束
allow_continue=False
必须重新选
```

Reconsider：

```text
旧行为仍存在
allow_continue=True
可以继续当前行为
```

触发 reconsider：

```text
Schedule boundary
Departure boundary
Adapter availability
Goal changed
足够强的 MeaningEvent
```

## 11. `_apply_decision()` 为什么可能什么都不做

如果决策仍是当前 Action：

```text
type 相同
travel destination 也相同
```

直接 return，不重建 ActionState。

否则 started_at/progress 会被重置。

## 12. travel 的空间语义

开始：

```text
locomotion=walking
posture=moving
place_id 暂时仍是出发地
```

完成：

```text
place_id=destination
locomotion=idle
```

当前是语义地点级模拟，不是逐帧坐标物理。

## 13. `maximum_kernel_steps`

防止未来新增规则制造：

```text
boundary == current time
→ while 永不前进
```

超过阈值直接报错，是逻辑安全阀。
