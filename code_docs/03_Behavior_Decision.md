# 03：BehaviorEngine 到底如何决定“下一步做什么”

对应源码：

```text
src/life/behavior.py
src/life/goals.py
src/life/habits.py
src/life/memory.py
src/life/schedule.py
src/life/movement.py
```

## 1. 不是“算一个概率然后抽签”

正式版顺序：

```text
Hard Constraint
→ 是否必须提前出发
→ 基础 Utility
→ Goal / Soft Schedule / Memory / External bonus
→ Habit
→ Goal-directed 与 Habit 加权
→ 小幅 noise
→ best action
→ Hysteresis 判断是否值得打断当前行为
```

## 2. `_base_scores()`

基础分来自当前身体、情绪、驱动力和环境。

例如：

```python
eat = hunger * 0.95
drink = (100 - hydration) * 1.10
```

`create`：

```text
creative_urge
× creative_reward
+ energy
- stress
```

`work`：

```text
achievement_urge
× achievement_reward
+ energy
- fatigue
```

这里只是“基础倾向”，还没有 Goal/Habit/Memory。

## 3. Perception 会裁掉不可能行为

附近没有 person：

```python
scores.pop("socialize")
```

没有任何可用 Adapter：

```python
scores.pop("communicate")
```

所以行为不是只看内心，还受当前世界条件约束。

## 4. 白天为什么压低 sleep

如果：

```text
circadian < 25
sleep_pressure < 70
fatigue < 75
```

则：

```text
sleep -35
```

目的：防止普通白天疲劳频繁触发 6~9 小时长睡。

## 5. 回家为什么也是普通行为

不在 `home_place_id` 时：

```text
travel score
=
8
+ circadian × 0.30
+ fatigue × 0.18
```

所以越晚、越累，越倾向回家。

它不是 hard schedule。

## 6. Hard Schedule 不参加排名

`decide()` 先：

```python
hard = self._hard_schedule_decision(...)
if hard is not None:
    return hard
```

意味着：

```text
hard schedule
```

不是“额外加 100 分”，而是直接优先返回。

## 7. 为什么会提前出发

09:00 hard schedule @ school，路程 25 分钟：

```text
departure = 09:00 - 25min = 08:35
```

08:35 到达 Kernel boundary 后：

```text
_reconsider()
→ upcoming_hard_travel_decision()
→ travel(school)
```

所以不会 09:00 才发现还在家。

## 8. Goal-directed 与 Habit 如何混合

先算：

```python
goal_weight
habit_weight
```

注意力更高：

```text
goal_weight 略升
```

cognitive_load 更高：

```text
goal_weight 略降
```

然后：

```text
combined
=
directed * goal_weight
+
habit * habit_weight
```

`directed` 包含：

```text
base score
+ soft schedule
+ goal bonus
+ memory bonus
+ external bonus
```

Habit 是另一条分支。

## 9. Goal bonus

单个 Goal：

```text
priority × 70 × remaining_progress
+ deadline urgency
```

越重要、越没完成、越临近 deadline，推动力越大。

总 bonus 截断：

```text
[-150, +150]
```

防止大量同类 Goal 永久压制吃饭/睡觉。

## 10. Goal 的 required place

如果：

```text
Goal.action_type = work
Goal.required_place_id = library
```

Behavior 先发现 `work` 高分，然后检查地点：

```text
不在 library
→ 先返回 travel(library)
```

到达后下一轮才真正 `work`。

## 11. Habit 上下文

当前 context：

```text
place_id
+ weekday/weekend
+ morning/afternoon/evening/night
```

例如：

```text
home|weekday|night
```

完整 habit key：

```text
home|weekday|night::leisure
```

所以习惯不是“全局爱做某事”，而是“在某个上下文更习惯做某事”。

## 12. 为什么 Action 保存 `habit_context_key`

例如：

```text
08:35 在 home 开始 travel
09:00 在 school 完成
```

如果完成时才取 context，会错误记录：

```text
school|morning|travel
```

所以开始时就保存原 context。

## 13. Memory bonus

每条 MemoryTrace 可以：

```python
action_bias = {"communicate": 20}
```

实际影响：

```text
raw bias
× salience
× 时间衰减
```

总影响限制在：

```text
[-40, +40]
```

## 14. External bonus

MeaningEvent：

```text
target_action=communicate
urgency=0.8
```

通过中断阈值后：

```text
communicate + 0.8 × 80
```

再进入普通 Behavior 仲裁。

它不是强制命令。

## 15. Decision noise

```python
rng.gauss(0, noise)
```

只用于相近候选产生个体波动。

Hard constraint 在之前已返回，不受它影响。

## 16. Hysteresis

普通 reconsider：

```python
if best_score <= current_score + threshold:
    continue
```

threshold 还受：

```text
current.commitment
profile.persistence
```

影响。

所以新行为只好一点时不会频繁切换。

## 17. `BehaviorDecision` 不是 `ActionState`

`BehaviorDecision`：

```text
“我决定接下来做什么”
```

`ActionState`：

```text
“这件事已经开始，成为现实事实”
```

只有 `start_action()` 后才进入 `LifeState.character.action`。
