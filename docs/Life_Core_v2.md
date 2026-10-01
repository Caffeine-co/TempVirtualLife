# Life Core v2：第一版可运行设计

这套代码的目标不是一次性模拟完整人类，而是先把 **“生命怎样持续存在”** 的工程骨架建立正确。

第一版只解决四件事：

1. 角色状态可以随真实时间连续推进；
2. 所有状态修改只有一个入口；
3. 行为由状态产生，行为又反过来改变状态；
4. NoneBot 可以和 Life Runtime 同进程运行，但 Life Core 不依赖 NoneBot。

因此它故意没有加入 LLM、RAG、完整关系系统、复杂世界地图和详细心理模型。这些应该作为后续模块挂到稳定的生命核心上，而不是继续把所有功能写进一个 `status_update()`。

---

## 1. 目录结构

```text
src/life/
├─ models.py       数据结构：Runtime State、配置、Event
├─ clock.py        真实时钟 / 模拟时钟
├─ actions.py      通用行为定义与行为影响
├─ schedule.py     日程查询
├─ physiology.py   时间连续推进
├─ derived.py      不持久化的派生状态
├─ behavior.py     下一行为选择
├─ kernel.py       唯一的生命状态转移逻辑
├─ repository.py   SQLite 快照 + Event Journal
├─ runtime.py      asyncio 运行容器、单写者、自动唤醒
├─ factory.py      创建 Runtime
└─ host/
   └─ nonebot.py   NoneBot 生命周期适配
```

最重要的依赖方向是：

```text
NoneBot
   ↓
LifeRuntime
   ↓
LifeKernel
   ↓
State / Action / Physiology / Behavior
```

反方向不允许出现。

例如 `kernel.py` 里不能出现：

```python
from nonebot import get_bot
```

也不能直接操作 SQLite。

---

# 2. 三个最重要的类

## `CharacterRuntimeState`

它是当前角色唯一权威状态。

第一版包含：

```text
spatial     在哪里
body        基础生理
 affect     低维情感状态
 drives     动态行为驱动力
 action     当前正在做什么
```

注意没有把所有可以描述人的指标都保存进去。

例如：

```text
sleepiness
thirst
physical_stamina
attention
mental_clarity
```

都在 `derived.py` 中由基础状态重新计算。

原则：

> 能可靠推导的值，不作为第二份真相持久化。

---

## `LifeKernel`

Kernel 是真正的“生命规则”。

最重要的两个入口：

```python
kernel.advance_to(state, target_time)
```

表示：

> 从上一状态时间连续推演到目标时间。

以及：

```python
kernel.handle_event(state, event)
```

表示：

> 世界在这个时刻发生了一件离散事件，把它作用到角色身上。

Kernel 自己不知道“现在几点”。

这样测试时可以在几秒内模拟几天，而不必真的等待几天。

---

## `LifeRuntime`

Runtime 管工程问题，不管人物心理逻辑。

它负责：

```text
asyncio.Lock
    ↓
保证同一角色只有一个状态写入者

SQLite（标准库 sqlite3）
    ↓
保存 snapshot + event journal

background task
    ↓
睡到行为结束 / 日程边界后再唤醒

start()
    ↓
停机后重新启动时补算到现在
```

外部代码不得这样做：

```python
state.body.energy = 20
```

应该提交 Event：

```python
await runtime.submit(...)
```

---

# 3. Runtime 为什么不是每秒更新一次

假设 13:00：

```text
action = create
fatigue = 30
hunger = 40
```

下一次值得处理的时间是 14:10 的行为结束。

那么 Runtime 可以直接：

```text
13:00 -------------------------- 14:10
              asyncio sleep
```

如果 13:26 突然收到外部事件：

```text
13:00 -------- 13:26
        ↑
     先补算这 26 分钟
        ↓
     应用外部事件
```

所以：

> 状态一直在逻辑上变化，但没有必要一直占 CPU 计算。

---

# 4. 当前的时间推进规则

`physiology.py` 目前故意只做基础版本。

## 清醒状态

基础上会：

```text
energy            缓慢下降
physical_fatigue  缓慢上升
hunger            上升
hydration         下降
sleep_pressure    向 100 逐渐增加
```

然后叠加当前行为的影响。

例如 `work`：

```text
energy 下降更快
fatigue 增加更快
stress 稍微增加
achievement_urge 被逐渐满足
```

## 睡眠

`sleep_pressure` 使用指数下降，作为两过程睡眠模型中 Process S 的第一版近似：

```text
sleep_pressure ↓
energy ↑
fatigue ↓
sleep_debt ↓
```

这还不是最终科学模型。

代码特意把它集中放在：

```text
physiology.py
```

以后替换算法时，不需要动 Runtime、数据库、NoneBot 接口。

---

# 5. 行为选择

第一版采用：

```text
约束 / 日程
   +
Utility
   +
小幅 decision noise
```

例如：

```text
sleep ← sleep_pressure + fatigue + circadian drive
eat   ← hunger
drink ← dehydration
rest  ← fatigue + low energy + stress
socialize ← social_need + social_energy
create ← creative_urge + energy
work   ← achievement_urge + energy
leisure ← novelty_urge + stress
```

`decision_noise` 默认只有 3 分。

它的作用是：

> 两个合理行为非常接近时产生个体波动。

而不是：

> 无视状态随机抽一个行为。

日程最高可以额外获得约 120 分，因此高刚性日程不会轻易被随机噪声破坏。

---

# 6. 行为不是每个 tick 都重新选择

每个 `ActionState` 有：

```text
started_at
expected_end_at
interruptibility
commitment
```

例如角色正在 `work`：

```text
interruptibility = 0.30
commitment       = 0.80
```

普通时间经过不会重新抽行为。

只在这些时刻重新判断：

```text
行为自然结束
日程边界
足够强的外部事件
手工强制事件
```

这就是行为惯性。

---

# 7. Event 的作用

第一版提供三个 Event。

## `ImpulseEvent`

它不是原始 QQ 消息。

它表示：

> 上层已经理解了某件事情对角色意味着什么。

例如：

```python
ImpulseEvent(
    occurred_at=now,
    name="important_social_signal",
    intensity=0.7,
    urgency=0.8,
    arousal=0.5,
    stress=0.3,
    target_action="socialize",
)
```

以后完整链路应该是：

```text
QQ Message
   ↓
Perception
   ↓
LLM / Rule Appraisal
   ↓
ImpulseEvent
   ↓
LifeKernel
```

因此 Kernel 不需要知道自然语言，也不依赖某个 LLM 厂商。

## `LocationChangedEvent`

用于世界系统确认角色位置发生变化。

## `ForceActionEvent`

主要用于：

```text
调试
管理员命令
测试
未来高层规划器
```

正常自主生命运行不应该大量依赖它。

---

# 8. SQLite 为什么保存两份东西

数据库里有：

```text
life_snapshot
```

保存当前完整状态。

还有：

```text
life_event
```

记录：

```text
action_started
action_completed
action_interrupted
schedule_boundary
impulse_applied
location_changed
...
```

因此以后遇到：

> “为什么角色现在突然在休息？”

可以直接查 Event Journal，而不是只看到一个无法解释来源的 `status.json`。

---

# 9. 如何挂载到 NoneBot

建议新增一个很薄的初始化文件，例如：

```python
# src/plugins/living/life_host.py

from src.life import build_life_runtime, load_life_config
from src.life.host import mount_to_nonebot


life_runtime = build_life_runtime(
    load_life_config("life.json")
)

mount_to_nonebot(life_runtime)
```

然后其他 matcher 只 import：

```python
from .life_host import life_runtime
```

禁止 matcher import：

```python
LifeKernel
SQLiteLifeRepository
```

更禁止自己修改 State。

这样 NoneBot 只是 Host。

---

# 10. 与现有 25:01 共存时怎么做

不要立刻删除旧 `living`。

建议阶段如下。

## 阶段 A：Dry Run

```text
旧 living
→ 继续负责真实聊天

Life v2
→ 同时运行
→ 只写自己的 life.db
→ 不发送消息
```

运行几天后观察：

```text
行动持续时间
睡眠时间
行为切换数量
状态曲线
Event Journal
```

## 阶段 B：输入接入

把 OneBot 消息同时作为 Life v2 的外部输入，但仍不让 v2 发送消息。

## 阶段 C：行为接管

逐步废弃：

```text
active_probability
status_update
pre_chat.new_status
chatting.new_status
```

让 Life v2 决定是否进入通信行为。

## 阶段 D：聊天成为 Action Executor

Life Core 决定：

```text
communicate
```

LLM 只决定：

```text
怎么理解
怎么说
```

到这里才真正完成核心替换。

---

# 11. 为什么现在没有 Relationship / Goal / World 复杂模型

不是因为不需要，而是因为顺序问题。

第一阶段最先验证：

```text
时间
→ 状态
→ 行为
→ 状态
```

这一闭环是否稳定。

确认稳定后再按下面顺序加：

```text
Schedule
↓
Goal / Task
↓
Relationship
↓
Perception
↓
Appraisal
↓
LLM
↓
复杂 World / 3D
```

不要第一版就把所有模块同时写出来，否则出了错很难判断究竟是哪一层导致的。

---

# 12. 目前代码中哪些算法明确只是占位版

需要特别说明，以下规则是**可运行的第一版模型**，不是最终人类行为学结论：

```text
circadian_sleep_drive()
Utility 权重
各种 ActionEffects 数值
情感 half-life
ImpulseEvent 的数值映射
Drive 的自然增长速度
```

它们存在的意义是先确定：

```text
所有权
因果方向
时间尺度
更新入口
```

以后应该通过：

```text
理论依据
+ 长期模拟结果
+ 参数校准
```

逐步替换这些数字。

架构本身不需要因此推倒重来。

---

# 13. 第一版最值得你读懂的调用链

建议按这个顺序阅读源码：

```text
examples/simulate_day.py
        ↓
factory.py
        ↓
runtime.py
        ↓
kernel.py
        ↓
behavior.py
physiology.py
        ↓
models.py
```

不要一上来从 `models.py` 七八个类逐行读。

先看一次完整调用是怎么跑起来的，再回头看数据结构会容易很多。

---

# 14. 一句话理解每个模块

```text
models.py
“系统里有什么数据？”

clock.py
“现在几点？”

actions.py
“有哪些行为，它们会造成什么影响？”

schedule.py
“现在有没有固定日程？”

physiology.py
“时间过去以后身体怎么变？”

behavior.py
“下一步更倾向做什么？”

kernel.py
“发生时间/事件以后，世界状态怎么转移？”

repository.py
“怎么把生命保存下来？”

runtime.py
“怎么让 Kernel 在程序里持续运行？”

host/nonebot.py
“NoneBot 怎么负责启动和关闭它？”
```

这就是第一版 Life Core 的完整边界。
