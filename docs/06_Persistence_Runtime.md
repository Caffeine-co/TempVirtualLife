# 06. Persistence / Runtime

## 1. Single Writer

`LifeRuntime` 内只有一个 `_lock` 控制写事务。

两个事件同时发生：

```text
A acquire
→ compute
→ commit
→ release
B acquire
→ read new revision
→ compute
```

不会互相覆盖。

## 2. Copy-on-write

这是正式版比 prototype 更重要的改动。

每次事务：

```text
self._state
↓ deep copy
working state
↓ Kernel mutate
DB transaction commit
↓ success
self._state = working
```

如果 DB commit 抛异常：

```text
self._state 仍然是旧状态
```

不会发生“内存已经 revision 20，磁盘还在 revision 19”。

## 3. 三张表

### life_snapshot

当前完整 LifeState。

### life_event

审计日志：解释为什么变成现在这样。

### life_pending_event

未来事件；重启后仍会继续。

## 4. Background Loop

Runtime 睡到：

```text
Kernel next_wakeup_time
或
Repository next_pending_time
```

外界 submit 会 `_wakeup.set()` 提前唤醒。

## 5. Listener

`runtime.add_listener()` 只在 commit 成功后收到通知。

适合：

```text
日志 UI
Action Executor
监控
调试面板
```

listener 崩溃不会回滚生命状态。
