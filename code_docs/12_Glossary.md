# 12：术语表

## Canonical State
唯一权威基础状态；当前是持久化的 `LifeState`。

## Derived State
从 Canonical State 重算的指标，例如 sleepiness、attention，不持久化。

## Runtime
承载 Kernel 的工程容器，负责 Lock、Clock、Persistence、Wakeup、Listener。

## Kernel
状态转移核心，负责时间推进顺序、Event 分发、Action 生命周期和重评估时机。

## Domain Service
具体规则模块，例如 MovementService、advance_physiology、goal_bonus。

## ActionDefinition
一种行为的静态规则。

## ActionState
当前一次具体正在执行的行为实例。

## BehaviorDecision
行为真正开始前的决策结果。

## Continuous Dynamics
时间经过就连续变化，例如 hunger、fatigue、emotion decay。

## Discrete Event
明确时刻跳变，例如 Action complete、Goal deadline、MeaningEvent。

## Boundary
Kernel 必须停止连续积分并处理离散规则的时间点。

## Hard Constraint
不进入普通 Utility 排名，直接优先满足的约束。

## Utility
候选 Action 在当前状态下的相对价值分数，不是概率。

## Hysteresis
行为切换需要额外门槛，防止小分差造成频繁抖动。

## Goal-directed
基于需求、Goal、Schedule、Memory 等结果评估的行为控制。

## Habit
由特定上下文中的重复行为形成的倾向。

## Appraisal
把客观刺激转换成“这件事对角色意味着什么”。

## MeaningEvent
Appraisal 完成后的结构化结果。

## WorldState
客观世界运行时事实。

## PerceptionFrame
角色当前可以获得的世界快照。

## Snapshot
数据库当前完整 LifeState。

## Journal
已经发生的状态转移审计记录。

## Pending Event
已确定未来发生、但还没到时间的 LifeEvent。

## Copy-on-write
先复制并修改副本，持久化成功后才发布成新权威状态。

## Single Writer
同一角色状态同一时刻只允许一个写事务；当前由 `asyncio.Lock` 保证。

## Host
承载 Runtime 生命周期的外层；当前可由 NoneBot 担任。
