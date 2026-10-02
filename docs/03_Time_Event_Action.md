# 03. Time / Event / Action

## 1. 时间不是 tick 驱动

假设 13:00 正在 `create`，下一事件 14:10 才发生。

程序不需要：

```text
13:01 update
13:02 update
...
```

而是：

```text
13:00 ---------------- 14:10
       一次连续积分
```

如果 13:26 来了事件：

```text
13:00 → 13:26
apply event
13:26 → later
```

## 2. advance_to()

`kernel.advance_to(state, target)` 每次寻找最近 boundary：

```text
target_time
action end
schedule boundary
goal deadline
```

只推进到最近一个，然后处理离散变化，再继续。

这是一种 Hybrid Discrete Event Simulation。

## 3. Action 生命周期

```text
select
→ started
→ continuous effects
→ completed / interrupted
→ discrete completion effects
→ goal progress
→ habit reinforcement
→ next action
```

## 4. Hard Schedule

`mode="hard"` 不再进入普通 Utility 排名。

如果 09:00 的 hard schedule 要求 `work_area`，从 `home` 需要 25 分钟：

```text
08:35 schedule_departure_boundary
→ travel
→ 09:00 arrival
→ required action
```

因此不是等到日程开始才发现“该走了”。

地图不可达时不会凭空计算路线；当前实现会直接执行日程行为并保留地点不一致，这种情况应通过测试或配置审计发现。

## 5. Future Event

`runtime.submit(event)`：

- `occurred_at <= now`：立即作用；
- `occurred_at > now`：存入 `life_pending_event`。

重启以后 future event 仍然存在。

## 6. Late Event

正式版仍然不做历史回滚。

迟到事件会在当前状态应用，并写：

```text
late_event_applied
```

完整历史回滚会显著增加复杂度，除非未来有强需求，否则不建议引入。
