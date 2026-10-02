# 09：SQLite、Future Event、恢复与 NoneBot 共存

## 1. 三张表

### `life_snapshot`

当前权威状态：

```text
id=1
revision
as_of
state_json
```

### `life_event`

审计日志：

```text
seq
revision
occurred_at
kind
data_json
```

回答“为什么变成这样”。

### `life_pending_event`

未来事件：

```text
id
occurred_at
event_json
```

进程重启后仍存在。

## 2. 原子事务

Repository 提交：

```text
BEGIN
→ 写 snapshot
→ 写 journal records
→ 删除已消费 pending events
→ COMMIT
```

三类修改必须一起成功。

否则可能出现：

```text
Snapshot 前进了
但 pending event 没删除
→ 下次重复执行
```

## 3. 为什么 pending event 到 commit 才删除

Runtime 只是先读取并在 working state 计算。

只有新 Snapshot 成功提交，才说明该未来事件真正完成消费。

失败时它仍留在 pending 表，可下次重试。

## 4. 停机恢复

最后：

```text
Snapshot 01:00
pending 03:00 MeaningEvent
```

09:00 重启：

```text
load 01:00
→ due event 03:00
→ advance 01:00→03:00
→ handle event
→ advance 03:00→09:00
→ 原子 commit
```

## 5. NoneBot Host 很薄

`src/plugins/host/nonebot.py` 只做：

```python
@driver.on_startup
await runtime.start()

@driver.on_shutdown
await runtime.stop()
```

NoneBot 是 Host，不是 Life Core。

## 6. 推荐初始化

```python
config = load_life_config("life.json")
life_runtime = build_life_runtime(config)
mount_to_nonebot(life_runtime)
```

其他插件只拿 `life_runtime`。

不要访问：

```text
runtime._state
Kernel 私有方法
Repository 内部连接
```

## 7. OneBot 收消息

最终链：

```text
OneBot Event
→ Adapter 提取结构化信息
→ Appraisal/语义层
→ MeaningEvent
→ runtime.submit()
```

## 8. Life 想发消息

推荐 Listener / Action Executor。

Listener 观察 Journal：

```text
action_started
action=communicate
```

再调用 OneBot 执行真实消息行为。

概念：

```python
async def listener(view, records):
    for record in records:
        if (
            record.kind == "action_started"
            and record.data["action"] == "communicate"
        ):
            await executor.execute(...)
```

Listener 在 Runtime 锁外，所以可以再次：

```python
await runtime.submit(...)
```

## 9. 为什么 Kernel 不能 `get_bot()`

否则依赖反转：

```text
Kernel → NoneBot
```

单独测试、Web Host、3D Host 都会被绑死。

## 10. 同进程共存

运行时：

```text
一个 Python process
一个 asyncio loop
├─ NoneBot tasks
└─ LifeRuntime background task
```

架构上依然是：

```text
NoneBot → Runtime → Kernel
```

所以没有额外 IPC 成本，也保留未来拆进程能力。
