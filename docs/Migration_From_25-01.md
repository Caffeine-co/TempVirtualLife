# 从当前 25:01 迁移到 Life Core v2

本文只说明迁移关系，不要求一次性重写现有功能。

## 1. 当前设施与新设施对应

| 当前 25:01 | Life v2 | 第一阶段处理 |
|---|---|---|
| `CharacterStatus` | `CharacterRuntimeState` | 并存，不立即删除旧类 |
| `status_update()` | `LifeRuntime.sync()` / `LifeKernel.advance_to()` | v2 不再请求 LLM |
| `active_probability()` | `BehaviorEngine` | 暂时并存 |
| `pre_chat.new_status` | Event / Action result | 暂时保留旧逻辑 |
| `chatting.new_status` | Event / Action result | 暂时保留旧逻辑 |
| APScheduler | 系统任务 | 继续保留 |
| OneBot matcher | Adapter | 继续保留 |
| memory DB | Memory 子系统 | 暂不改 |
| session DB | Communication World | 暂不改 |

## 2. 第一阶段不要做什么

不要：

```text
删除旧 status.json
删除旧 status_update
删除 active_probability
让 Life v2 直接发送 QQ 消息
让 LLM 修改 Life v2 state
```

先让两个系统平行运行。

## 3. 推荐新增文件

把本包的：

```text
src/life/
```

直接复制到仓库：

```text
25-01/src/life/
```

然后复制：

```text
life.example.json
```

为：

```text
25-01/life.json
```

第一阶段可以保持：

```json
"schedule": []
```

先验证纯自主行为与时间推进。

## 4. 新增 Life Host

建议：

```python
# src/plugins/living/life_host.py

from src.life import build_life_runtime, load_life_config
from src.life.host import mount_to_nonebot


life_runtime = build_life_runtime(
    load_life_config("life.json")
)

mount_to_nonebot(life_runtime)
```

然后只要确保这个模块会被加载即可。

## 5. 第一阶段观察日志的方法

Life v2 的行为轨迹目前保存在 SQLite：

```text
life.db
```

重点看：

```text
life_snapshot
life_event
```

例如：

```sql
SELECT *
FROM life_event
ORDER BY seq DESC
LIMIT 100;
```

可以检查：

```text
是不是频繁切换行为
睡眠会不会异常
行为有没有没有原因地被打断
固定日程是否生效
```

## 6. 第二阶段才接 OneBot 输入

收到消息时，暂时不要直接把自然语言塞进 Kernel。

正确目标链路是：

```text
OneBot message
→ Social/Perception adapter
→ Appraisal
→ ImpulseEvent
→ LifeRuntime.submit()
```

目前 Appraisal 尚未实现，因此测试时可以人为构造：

```python
from src.life import ImpulseEvent

await life_runtime.submit(
    ImpulseEvent(
        occurred_at=life_runtime.clock.now(),
        name="social_message",
        intensity=0.4,
        urgency=0.3,
        target_action="socialize",
    )
)
```

这只是接口验证，不应该成为最终消息理解逻辑。

## 7. 什么情况下再开始替换旧核心

建议至少完成这些验证：

```text
连续模拟 24h 不产生非法状态
连续模拟 7d 不产生异常行为震荡
程序关闭后重新启动能够正确补算
同一时刻并发 submit 不会覆盖状态
Event Journal 能解释主要状态变化
Schedule 能稳定压过普通决策噪声
```

满足后再开始让 Life v2 接管：

```text
“什么时候打开社交软件”
```

而不是先接管聊天内容生成。
