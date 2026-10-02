# 08. NoneBot Integration

## 1. Host 挂载

示例：

```python
from src.life import build_life_runtime, load_life_config
from src.life.host import mount_to_nonebot

life_runtime = build_life_runtime(
    load_life_config("life.json")
)

mount_to_nonebot(life_runtime)
```

这样仍是一个 Python 进程。

## 2. OneBot 在线状态

连接建立时：

```python
await life_runtime.submit(
    AdapterAvailabilityEvent(
        occurred_at=life_runtime.clock.now(),
        adapter="onebot",
        available=True,
    )
)
```

断开时发送 `available=False`。

## 3. 收到消息

不要：

```text
OneBot message -> Kernel
```

应该：

```text
OneBot message
→ Social Perception
→ Appraisal
→ MeaningEvent
→ runtime.submit()
```

现在可以先用 `RuleBasedAppraisal`；未来再替换为 LLM Appraisal。

## 4. 角色选择 communicate 后怎么办

用 `runtime.add_listener()` 监听 `action_started`：

```text
action == communicate
```

然后交给 Communication Executor。

Executor 完成以后再提交：

```text
MeaningEvent / RelationshipEvent / MemoryEvent
```

把真实结果反馈给生命核心。

## 5. 不允许的依赖

`src/life/kernel.py` 里不要出现：

```python
from nonebot import ...
```

`matcher` 里也不要直接修改 `runtime._state`。
