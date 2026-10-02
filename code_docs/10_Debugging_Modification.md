# 10：怎么调试、怎么新增功能而不破坏体系

## 1. 先从 Journal 查原因

SQL：

```sql
SELECT
    seq,
    revision,
    occurred_at,
    kind,
    data_json
FROM life_event
ORDER BY seq DESC
LIMIT 100;
```

如果问：

```text
“为什么突然 work？”
```

先看：

```text
action_completed
schedule_boundary
goal_upserted
meaning_applied
action_started.reason
```

`action_started` 已记录：

```text
reason
score
source
target
destination
expected_end_at
```

## 2. 调 Behavior 时检查顺序

打印：

```text
时间
place
当前 action
Body / Affect / Drives
Perception
active schedule
active goals
habit context
memory bonus
final scores
```

不要只打印 `best=work`。

## 3. 各测试保护什么

`smoke_test`：

```text
Event 提交
时间推进
Action 完成
下一 Action 续接
Journal
```

`schedule_movement_test`：

```text
hard schedule
→ travel
→ 到达
→ schedule action
```

`future_event_test`：

```text
未来 Event 不提前生效
到时间才生效
```

`appraisal_listener_test`：

```text
Appraisal → MeaningEvent → Affect
Listener 不在写锁内
```

`recovery_test`：停机恢复。

`long_simulation_test`：长时间不死循环、不越界、不掉 Action。

## 4. 增加 Action

例如 `exercise`：

### A. `actions.py`

新增 `ActionDefinition`。

### B. `behavior.py::_base_scores()`

若要自主选择，必须加入：

```python
scores["exercise"] = ...
```

只加 ActionDefinition 不够。

### C. 离散完成效果

如需要，改：

```text
kernel._complete_current_action()
```

只有连续 effects 则不用。

### D. 测试

验证：

```text
可被选
可推进
可完成
状态范围正确
```

## 5. 增加状态字段

先回答：

```text
谁拥有？
为什么变？
时间尺度？
Canonical 还是 Derived？
```

如果能推导，放 `derived.py`。

必须保留历史连续性才进 State。

## 6. 增加 Event

步骤：

```text
models.py 新 Event
→ 加入 LifeEvent union
→ kernel.handle_event 分发
→ handler/domain function
→ Journal
→ 测试当前事件 + future event
```

## 7. 增加 Derived 指标

只改：

```text
DerivedState
derived.py
```

不需要数据库 migration，也不需要更新循环。

## 8. 增加地点

通常只改 `life.json` 的 WorldConfig。

如果规则通用，不改 Kernel。

## 9. 更复杂 Goal

当前 Goal 是“原子目标”。

若未来：

```text
买材料
→ 去工作室
→ 创作
→ 提交
```

不要把几十个阶段字段继续塞 `GoalState`。

应该新增 TaskGraph / Planner。

## 10. 接 LLM 的禁区

不要：

```text
LLM → energy/stress/current_action 完整重写
```

推荐：

```text
LLM → 语义/Appraisal
→ MeaningEvent
→ Kernel
```

## 11. 常见误区

### “每个文件是独立系统”

不是；它们共享一个 `LifeState`。

### “Kernel 应该包含所有公式”

不是；Kernel 编排顺序，公式放 Domain。

### “Behavior 不停重选”

不是；只在 Action complete / boundary / relevant event 时重评估。

### “Journal 是状态恢复来源”

目前不是；Snapshot 是恢复来源，Journal 主要审计。

### “Perception 就是 World”

不是；World 是客观事实，Perception 是角色当前可获得的事实。

## 12. 推荐断点

启动：

```text
factory.build_life_runtime
runtime.start
kernel.initialize
behavior.decide
kernel._apply_decision
runtime._commit_working
```

推进：

```text
runtime.sync
kernel.advance_to
physiology.advance_physiology
kernel._complete_current_action
behavior.decide
```

事件：

```text
runtime.submit
kernel.handle_event
对应 handler
kernel._reconsider
behavior.decide
```
