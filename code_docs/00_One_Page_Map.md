# 00：一页建立完整心智模型

## 1. 中心事实只有一个：`LifeState`

数据库真正保存的是：

```python
LifeState(
    revision=...,
    as_of=...,
    character=...,
    world=...,
    health=...,
    goals=...,
    relationships=...,
    habits=...,
    memories=...,
)
```

它表示：

> 在 `as_of` 这个时刻，模拟世界承认的全部生命事实。

其他模块不各自拥有状态；它们都围绕同一个 `LifeState` 工作。

## 2. 四层结构

```text
Host
NoneBot / standalone / future 3D
“谁负责启动、接外部世界？”
        ↓
LifeRuntime
Lock / Clock / Repository / Wakeup
“怎么安全持续运行？”
        ↓
LifeKernel
时间推进 + Event + Action 生命周期
“状态按什么顺序变化？”
        ↓
Domain Services
Behavior / Physiology / Affect / World ...
“具体规则是什么？”
```

依赖只能向下：

```text
NoneBot → Runtime → Kernel → Domain
```

不能反向。

## 3. 一次 `sync()` 的真实链路

假设：

```text
08:00
place=home
action=leisure
action ends=08:35
```

09:10 调用：

```python
await runtime.sync()
```

实际：

```text
LifeRuntime.sync()
├─ clock.now() = 09:10
├─ 查询到期 future events
├─ deep copy 当前 LifeState → working
└─ kernel.advance_to(working, 09:10)
   ├─ 找最近 boundary
   ├─ health/physiology/affect 连续推进
   ├─ Action 到期则完成
   ├─ Goal/Habit 更新
   ├─ Behavior 决定下一 Action
   └─ 重复直到 09:10
```

最后：

```text
working.revision += 1
→ SQLite 原子 commit
→ self._state = working
→ 释放 Lock
→ Listener
```

## 4. 两种变化

连续变化：

```text
energy / fatigue / sleep_pressure / hunger /
hydration / sensory_load / cognitive_load /
emotion decay / health recovery
```

离散变化：

```text
Action complete
Schedule boundary
Goal deadline
MeaningEvent
RelationshipEvent
Travel arrival
Adapter 上线/下线
```

## 5. 为什么不需要固定 tick

如果 08:00→09:00 一直是同一 Action：

```python
advance_physiology(..., hours=1.0)
```

一次结算即可。

所以：

```text
逻辑上连续变化
≠
CPU 持续计算
```

## 6. 外部正常写入口只有一个

不要：

```python
state.character.body.energy -= 20
```

应该：

```python
await runtime.submit(event)
```

这样变化才有统一时间顺序、Journal 和事务。

## 7. 五个对象最重要

```text
LifeState
现在世界事实是什么？

LifeRuntime
怎么安全持续运行？

LifeKernel
时间/Event 来了以后怎么转移状态？

BehaviorEngine
需要重新决策时下一步做什么？

ActionState
角色此刻正在执行的具体行为是什么？
```
