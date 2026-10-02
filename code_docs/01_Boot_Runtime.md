# 01：从启动开始理解 `LifeRuntime`

对应源码：

```text
src/life/factory.py
src/life/clock.py
src/life/runtime.py
src/life/repository.py
src/plugins/host/nonebot.py
```

## 1. `build_life_runtime()`

它只做依赖组装：

```python
if clock is None:
    clock = RealClock(config.timezone)

kernel = LifeKernel(config)
repository = SQLiteLifeRepository(config.database_path)
return LifeRuntime(kernel, repository, clock)
```

含义：

```text
Clock       “现在几点？”
Kernel      “生命怎么变化？”
Repository  “生命怎么保存？”
             ↓
Runtime
```

外部代码不要到处重复 new 这些对象。

## 2. Clock 为什么单独抽象

生产：

```python
RealClock.now()
```

测试：

```python
clock = SimulationClock(t0)
clock.advance(timedelta(hours=8))
```

如果 Kernel 自己到处 `datetime.now()`，高速模拟就做不了。

## 3. `start()` 第一次启动

```text
repository.initialize()
↓
repository.load_state()
↓
没有 Snapshot
↓
kernel.create_initial_state(now)
↓
kernel.initialize(initial)
↓
如果没有 Action，Behavior 选一个
↓
revision = 1
↓
repository.commit()
↓
self._state = initial
↓
sync()
↓
background_loop
```

关键点：先数据库成功，再发布成内存权威状态。

## 4. 非第一次启动

```text
load_state()
→ self._state = old snapshot
→ sync()
```

例如停机 8 小时：

```text
Snapshot.as_of=01:00
Clock.now=09:00
```

`sync()` 会补算 01:00→09:00。

## 5. `_state` 为什么不能直接返回

`get_state()`：

```python
return self._state.model_copy(deep=True)
```

所以外部拿到的是照片，不是本体。

```python
state = await runtime.get_state()
state.character.body.energy = 0
```

不会修改真实 Runtime 状态。

## 6. `sync()` 的事务结构

```text
① 获取 Lock
② 读 current
③ now = clock.now()
④ 读取 due pending events
⑤ deep copy current → working
⑥ Kernel 只改 working
⑦ SQLite commit
⑧ self._state = working
⑨ 释放 Lock
⑩ Listener
```

## 7. copy-on-write 的必要性

错误：

```text
先改 self._state
→ SQLite 失败
→ 内存新、磁盘旧
```

现在：

```text
old state
→ deep copy working
→ 修改 working
→ commit 成功
→ 才替换 self._state
```

失败时旧权威状态仍完整。

## 8. Lock 的作用

同时：

```text
A: runtime.submit(message)
B: background sync()
```

没有 Lock 可能都从 revision 10 开始写 revision 11。

有：

```python
async with self._lock:
```

后状态事务严格串行。

## 9. Future Event

如果：

```python
event.occurred_at > now
```

`submit()` 不立即应用，而是：

```text
repository.schedule_event()
→ life_pending_event
→ wake background loop
```

到时间才处理。

## 10. 迟到 Event

如果：

```text
state.as_of=15:00
event.occurred_at=14:50
```

当前版本不回滚历史，而是：

```text
记录 late_event_applied
→ 在当前状态应用
```

## 11. `_background_loop()`

它不每秒 tick。

候选唤醒时间：

```text
Kernel 内部 next_wakeup_time
Repository 下一个 pending event
```

取最早一个，直接 sleep 到那时。

外部 Event 到来时：

```python
self._wakeup.set()
```

提前唤醒。

## 12. Listener 为什么锁外执行

如果在锁内：

```text
Runtime 持锁
→ listener()
→ listener 又 runtime.get_state()
→ 等同一个锁
→ 死锁
```

正式版先释放锁，再 `_notify()`。

## 13. Runtime 不应该放哪些逻辑

不要放：

```text
hunger 怎么涨
work 为什么高分
情绪怎么衰减
关系怎么变
地图距离怎么算
```

这些属于 Domain / Kernel。
