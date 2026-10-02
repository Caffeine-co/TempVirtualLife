# 11：四个完整场景串起全部代码

## 场景一：第一次启动

```text
07:00
life.db 不存在
initial.place=home
```

调用：

```python
runtime = build_life_runtime(config, clock)
await runtime.start()
```

真实调用栈：

```text
factory.build_life_runtime
├─ Clock
├─ LifeKernel
│  ├─ WorldService
│  ├─ PerceptionService
│  ├─ MovementService
│  ├─ ScheduleService
│  └─ BehaviorEngine
├─ SQLiteLifeRepository
└─ LifeRuntime

LifeRuntime.start
├─ repository.initialize
├─ repository.load_state → None
├─ kernel.create_initial_state
├─ kernel.initialize
│  ├─ perception.frame
│  ├─ behavior.decide
│  └─ kernel._apply_decision
├─ repository.commit revision=1
├─ runtime.sync
└─ background task
```

---

## 场景二：09:00 hard schedule，地点 25 分钟远

```text
08:00 人在 home
09:00 work @ work_area
home→work_area = 25min
```

08:00：

```text
next_required_departure_time()
→ 08:35
```

08:35：

```text
runtime.sync
→ kernel.advance_to(08:35)
→ departure boundary
→ reconsider
→ behavior.decide
→ travel(work_area,25min)
```

09:00：

```text
travel complete
→ place=work_area
→ schedule boundary
→ hard schedule active
→ work
```

---

## 场景三：work 中收到紧急社交刺激

当前：

```text
action=work
interruptibility=0.30
```

Meaning：

```text
urgency=0.8
target_action=communicate
```

计算：

```text
interrupt_score
= 0.8 × 0.30
= 0.24
```

默认 threshold=0.35：

```text
不打断
继续 work
```

如果当前 leisure：

```text
0.8 × 0.85 = 0.68
```

通过阈值后：

```text
communicate +64 external bonus
→ BehaviorEngine 完整重评估
```

仍可能因为 hard schedule、Goal、hysteresis 不切换。

---

## 场景四：停机 8 小时，中间有 Future Event

最后 Snapshot：

```text
01:00
action=sleep
```

Pending：

```text
03:00 MeaningEvent(stress)
```

09:00 重启：

```text
load 01:00
→ sync
→ due event 03:00
→ advance 01:00→03:00
→ handle MeaningEvent
→ advance 03:00→09:00
→ commit
→ 删除 pending event
```

---

## 场景五：Goal 要求去特定地点

Goal：

```text
action_type=work
required_place_id=library
priority=0.9
```

当前：

```text
place=home
```

Behavior：

```text
work base
+ goal bonus
→ work 成为 best
```

但 required place 不满足：

```text
→ travel(library)
```

到达后下一轮：

```text
Goal 继续推动 work
→ 地点满足
→ work(target=goal.target)
```

work 完成：

```text
apply_action_progress
→ progress += duration × progress_per_hour
```

这条链把：

```text
目标 → 空间 → 行为 → 进度
```

完整串起来。
