# 04：关键函数逐段注解版

## 1. `LifeRuntime.sync()`

下面是等价的解释版：

```python
async def sync(self):

    # 最终通知 Listener 的数据。
    # 真正回调不能在写锁里执行。
    notification = None

    # 从这里进入“单写者事务”。
    async with self._lock:

        # 当前内存权威状态，只读。
        current = self._require_state()

        # Runtime 从注入 Clock 获取现在。
        now = self.clock.now()

        # 时间倒退说明 Clock 或数据有错误。
        if now < current.as_of:
            raise ValueError(...)

        # 找已经到时间的 future events。
        due = await self.repository.due_events(now)

        # 时间没变化、也没有到期事件，就无需事务。
        if now == current.as_of and not due:
            return current.model_copy(deep=True)

        # Copy-on-write：Kernel 只修改 working。
        working = current.model_copy(deep=True)

        records = []
        consumed = []

        # future event 按 occurred_at 顺序处理。
        for pending_id, event in due:

            # 先把生命推进到事件时刻。
            if event.occurred_at >= working.as_of:
                records += self.kernel.advance_to(
                    working,
                    event.occurred_at,
                )

            # 再在那个时刻作用事件。
            records += self.kernel.handle_event(
                working,
                event,
            )

            # 提交成功后才真正从 DB 删除。
            consumed.append(pending_id)

        # 最后推进到真实 now。
        if working.as_of < now:
            records += self.kernel.advance_to(working, now)

        # 原子提交成功后才替换 self._state。
        notification = await self._commit_working(
            working,
            records,
            consumed,
        )

        result = self._require_state().model_copy(deep=True)

    # 已释放写锁。
    await self._notify(notification)

    return result
```

一句话：

> `sync()` = “把旧 Snapshot + 所有到期事件一次性结算到现在”。

---

## 2. `LifeKernel.advance_to()`

```python
def advance_to(state, target_time):

    # 不允许生命时间倒退。
    if target_time < state.as_of:
        raise ValueError(...)

    # 没有 Action 就先补一个。
    initialize(state)

    while state.as_of < target_time:

        # A. 找下一离散边界。
        action_end = ...
        schedule_boundary = ...
        goal_deadline = ...
        departure_boundary = ...

        boundary = min(
            target_time,
            action_end,
            schedule_boundary,
            goal_deadline,
            departure_boundary,
        )

        # B. 这一整段里 Action 不变，所以可一次性积分。
        hours = boundary - state.as_of

        action_def = actions[current_action.type]
        perception = perception.frame(state)

        advance_health(state, hours)
        advance_physiology(state, action_def, perception, hours)
        advance_affect(state, ..., hours)

        # C. 把生命时间正式推进到边界。
        state.as_of = boundary
        update_action_progress(state)

        # D. 在边界处理离散事情。
        if boundary == goal_deadline:
            fail_expired_goals(...)

        if action 到期:
            complete_current_action(...)

        if boundary == schedule_boundary:
            reconsider(...)

        if boundary == departure_boundary:
            reconsider(...)

        # E. 若旧行为刚完成，马上产生下一行为。
        if state.character.action is None:
            decision = behavior.decide(...)
            apply_decision(...)

        # F. 防止零时间死循环。
        if state.as_of == old_as_of:
            raise RuntimeError(...)
```

---

## 3. `BehaviorEngine.decide()`

```python
def decide(...):

    # ① 真正硬约束。
    hard = hard_schedule_decision(...)
    if hard:
        return hard

    # ② 到了 hard schedule 最晚出发时间。
    departure = upcoming_hard_travel_decision(...)
    if departure:
        return departure

    # ③ 根据 Body/Affect/Drive/Perception 算基础分。
    scores = base_scores(...)

    # ④ 计算 goal-directed 与 habit 的权重。
    goal_weight = ...
    habit_weight = ...

    for action in scores:

        # 显式目标导向部分。
        directed = base_score
        directed += soft_schedule_bonus
        directed += goal_bonus
        directed += memory_bonus
        directed += external_bonus

        # 当前上下文习惯。
        habit = effective_habit_strength(...) * 100

        # 两条控制系统融合。
        combined = (
            directed * goal_weight
            + habit * habit_weight
        )

        # 小幅噪声。
        combined += random_noise

    best = argmax(final_scores)

    # ⑤ 普通重评估时加 hysteresis。
    if allow_continue:
        if best_score <= current_score + threshold:
            return current_action

    # ⑥ 若 Goal 要求特定地点，先 travel。
    if dominant_goal.requires_other_place:
        return travel_to_goal_place

    return BehaviorDecision(...)
```

---

## 4. `advance_physiology()`

```python
def advance_physiology(state, action, perception, hours, config):

    body = state.character.body
    cognition = state.character.cognition
    drives = state.character.drives

    # 当前行为每小时额外影响。
    effects = action.effects

    # Health condition 的身体惩罚。
    _, health_pain, health_fatigue, health_energy_penalty = \
        health_penalties(state)

    # 客观环境通过 Perception 变成感官负荷目标。
    sensory_target = f(
        noise,
        crowding,
        privacy,
        comfort,
        temperature,
        light,
    )

    if action.name == "sleep":

        # Process S 简化下降。
        sleep_pressure *= exp(-hours/tau)

        # 恢复。
        energy += ...
        fatigue -= ...
        cognitive_load -= ...
        rumination -= ...

    else:

        # 清醒时 sleep pressure 向 100 渐近。
        sleep_pressure = ...

        # 基础清醒消耗 + Action effects + Health effects。
        energy += (...)
        fatigue += (...)
        hunger += (...)
        hydration += (...)

        # 生理唤醒缓慢回到中性 40。
        physiological_arousal += ...

        # 感官负荷平滑靠近环境目标。
        sensory_load += (
            sensory_target - sensory_load
        ) * approach_factor

        # Cognition / Drives 连续更新。
        cognitive_load += ...
        rumination += ...
        social_need += ...
        creative_urge += ...
        ...

    # 普通 pain 会自然衰减，
    # Health condition 可形成最低疼痛水平。
    pain = max(old_pain_decay, health_pain)
```

---

## 5. `_complete_current_action()`

```python
action = current_action

# 先记录“确实做完了”。
record(action_completed)

# 离散完成效果。
if eat:
    hunger -= 40
elif drink:
    hydration += 30
elif travel:
    place_id = destination
    record(travel_arrived)
...

# 行为真正完成后才推进 Goal。
apply_action_progress(...)

# 行为真正完成后才强化 Habit。
reinforce_habit(
    original_context=action.habit_context_key
)

# 最后清空 Action。
state.character.action = None
```

---

## 6. `_handle_meaning()`

```python
# ① Core Affect。
valence += event.valence * ...
arousal += event.arousal * ...
stress += event.stress * ...

# ② 当前显著 Emotion。
if event.emotion:
    upsert_emotion(...)

# ③ 相关人物：只小幅增加 familiarity。
if related_entity:
    relationship.familiarity += ...

# ④ 高 salience：形成 MemoryTrace。
if memory_salience > 0:
    add_memory(...)

# ⑤ 没有 target_action，心理影响到此结束。
if not target_action:
    return

# ⑥ 是否足够重要到允许打断？
interrupt_score =
    urgency * current_action.interruptibility

if interrupt_score < threshold:
    return

# ⑦ 仍然不是强制切换。
# 给目标行为一个 external bonus，再走 Behavior 仲裁。
decision = behavior.decide(
    external_bonus={target_action: urgency * 80}
)

apply_decision(...)
```

所以：

```text
紧急刺激
≠
必然行动
```

还取决于当前行为、Schedule、Goal、Habit 和 hysteresis。
