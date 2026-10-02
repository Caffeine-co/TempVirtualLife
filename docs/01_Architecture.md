# 01. Architecture：为什么这样拆

## 1. 目标

Formal Core 的目标是让“角色存在”本身成为程序主体，而不是把状态推演继续附着在聊天流程上。

旧式 Agent 常见结构：

```text
定时器
→ LLM 重新描述状态
→ LLM 决定行为
→ 聊天
```

Formal Core：

```text
World + Time
→ LifeState
→ Perception
→ Behavior Arbitration
→ Action
→ Continuous Dynamics
→ LifeState'
```

外界事件只通过 `LifeEvent` 进入。

## 2. 三层

### Domain Layer

`kernel.py` 和它下面的服务。

职责：生命规则。

不允许知道：

```text
NoneBot
SQLite
真实系统时钟
具体 LLM SDK
```

### Runtime Layer

`runtime.py + repository.py + clock.py`

职责：

```text
单写者
并发
持久化
未来事件
停机恢复
后台唤醒
```

不负责：

```text
角色为什么累
为什么想工作
为什么焦虑
```

### Host / Adapter Layer

例如 `host/nonebot.py`。

职责：把某个平台挂到 Runtime。

## 3. LifeState 是 Aggregate Root

正式版不再把所有东西叫 CharacterStatus。

```text
LifeState
├─ character
│  ├─ spatial
│  ├─ body
│  ├─ cognition
│  ├─ affect
│  ├─ drives
│  └─ action
├─ world
├─ health
├─ goals
├─ relationships
├─ habits
└─ memories
```

原因：

`friendship_closeness` 不是角色身体的一部分；`world.noise` 也不是人物的一部分。不同数据域需要不同更新规则。

## 4. 唯一写入口

外部模块禁止直接：

```python
state.character.body.energy = 100
```

正常业务只能：

```python
await runtime.submit(event)
```

时间推进只能：

```python
await runtime.sync()
```

Runtime 内部再调用 Kernel。

## 5. 为什么仍然与 NoneBot 同进程

目前 Host 可以：

```python
@driver.on_startup
await runtime.start()
```

这只是部署选择。

只要 Kernel/Runtime 不 import OneBot，未来拆进程时只需要替换 Host，而不需要重写生命规则。
