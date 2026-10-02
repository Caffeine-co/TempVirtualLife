# TempVirtualLife Formal Core

这是 TempVirtualLife 的正式版 Life Core：目标不是“做一个更复杂的 Bot”，而是建立一个**可持续存在、可被时间推进、可在世界中行动、并能由行为反过来改变自身状态的虚拟生命运行核心**。

这一版已经把 prototype 中明确属于占位性质的部分重新实现，并补齐了除 LLM 之外的主要模块：

- Embedded Runtime：可与 NoneBot 同进程运行；
- Single Writer + copy-on-write transaction；
- 连续时间推进 + 离散事件；
- Snapshot + Journal + 持久化 Future Event Queue；
- Hard / Soft Schedule；
- World / Environment / Entity；
- Perception；
- Movement / Travel；
- Physiology / Sleep / Health；
- Core Affect + Salient Emotion；
- Cognition；
- Drive；
- Goal / Task；
- Relationship；
- Structured Memory + memory influence；
- Habit learning / decay；
- Goal-directed + Habit arbitration；
- Rule-based Appraisal；
- NoneBot Host；
- RealClock / SimulationClock；
- 30 日高速模拟测试。

LLM **没有**集成进 Kernel。未来 LLM 最适合放在：

```text
原始自然语言 / 复杂社会事件
        ↓
Perception / Semantic Parser
        ↓
Appraisal
        ↓
MeaningEvent
        ↓
LifeRuntime.submit()
```

Kernel 本身不允许 LLM 直接写 `energy=...`、`stress=...`、`action=...`。

---

## 1. 最重要的总体结构

```text
Host / Adapter
    │
    │ submit LifeEvent / listen committed records
    ▼
LifeRuntime
    │
    │ single writer / persistence / wakeup / recovery
    ▼
LifeKernel
    │
    ├─ World + Perception + Movement
    ├─ Physiology + Health
    ├─ Affect + Cognition + Drives
    ├─ Schedule + Goal + Habit + Memory
    └─ Behavior Arbitration + Action Lifecycle
```

依赖方向只能从上向下。`LifeKernel` 不 import NoneBot、不访问 SQLite、不读取真实系统时间。

---

## 2. 快速运行

安装核心依赖：

```bash
pip install -r requirements-life.txt
```

运行全部测试：

```bash
python -m tests.run_all
```

预期所有项目均 `PASS`。

运行一周高速模拟：

```bash
python -m examples.simulate_week
```

查看 Domain Event 示例：

```bash
python -m examples.domain_events
```

使用真实时钟运行：

```bash
python -m src.life
```

---

## 3. 推荐阅读顺序

第一次不要按文件名顺序硬啃。建议：

```text
README.md
↓
docs/01_Architecture.md
↓
examples/simulate_week.py
↓
src/life/runtime.py
↓
src/life/kernel.py
↓
src/life/behavior.py
↓
src/life/physiology.py
↓
src/life/models.py
```

然后再读：

```text
docs/02_State_and_Ownership.md
docs/03_Time_Event_Action.md
docs/04_Behavior_Psychology.md
docs/05_World_Perception_Movement.md
docs/06_Persistence_Runtime.md
docs/07_Configuration.md
docs/08_NoneBot_Integration.md
docs/09_Testing_and_Calibration.md
docs/10_Migration_From_Prototype.md
docs/11_Theory_References.md
```

---

## 4. 这版与 prototype 最大的变化

prototype 的重要价值是证明了：

```text
时间 → 状态 → 行为 → 状态
```

能够真正跑起来。

正式版进一步解决：

1. `switch_threshold` 现在真的参与普通重新决策，不再只是配置字段；
2. `hard schedule` 不再是 `+120` 的高权重提示，而是直接优先于 Utility；
3. 地点不再由日程“瞬移”：Kernel 会根据下一条 hard schedule 和路线时间提前唤醒并出发；
4. `home_place_id` 提供非硬编码的生活基地回归倾向，避免日程结束后无限滞留；
5. Runtime 改成 copy-on-write：DB commit 失败不会提前污染内存状态；
6. Future Event 会落 SQLite，重启后仍会按发生时间处理；
7. `LifeState` 把 Runtime、World、Goal、Relationship、Habit、Memory、Health 分域；
8. Affect 加入显著情绪及独立衰减；
9. Goal 与 Habit 都真实参与 Behavior arbitration；
10. Memory 可以通过时间衰减的 action bias 影响近期行为；
11. Health condition 会持续恢复并影响身体；
12. Perception 真正读取环境和附近 Entity；
13. Rule-based Appraisal 提供了不依赖 LLM 的完整事件意义链路。

---

## 5. 当前边界

这是一套正式**工程架构**和可运行**行为模拟模型**，不是医学、临床心理学或神经科学意义上的精确人体仿真。

以下参数仍然需要后续通过理论、长期模拟和角色设定校准：

- 生理变化速率；
- Process C 的精度；
- Utility 权重；
- emotion half-life；
- habit learning rate；
- memory influence；
- Goal urgency；
- Appraisal 映射系数。

但这些都已经被限制在各自模块里。调整模型时不需要重写 Runtime、Persistence 或 NoneBot 接口。

---

## 6. 代码原则

新增任何状态字段前都应回答：

```text
它属于哪个数据域？
谁可以修改它？
为什么会改变？
按什么时间尺度改变？
能否由别的字段推导？
```

若最后一问答案是“能”，优先放进 `derived.py`，不要制造第二份真相。
