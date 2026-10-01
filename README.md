# Life Core v2 Prototype

这是为 25:01 下一代 Life / VirtualLife 核心准备的**可运行第一版骨架**。

特点：

- 与 NoneBot 可同进程运行；
- `LifeKernel` 不依赖 NoneBot；
- 单写者 Runtime；
- 状态随时间连续推进；
- 行为驱动状态变化；
- SQLite Snapshot + Event Journal；
- 支持真实时钟和高速模拟时钟；
- 不依赖任何具体角色设定；
- 第一版不依赖 LLM。

## 依赖

当前 25:01 已经包含：

```text
pydantic
nonebot2（仅 NoneBot host 需要）
```

所以复制到现有项目后不需要新增第三方依赖。

## 快速运行

在本目录执行：

```bash
python -m tests.smoke_test
```

预期：

```text
smoke_test: PASS
```

运行 24 小时高速模拟：

```bash
python -m examples.simulate_day
```

查看外部刺激如何影响当前行为：

```bash
python -m examples.submit_impulse
```

## 阅读顺序

先读：

```text
docs/Life_Core_v2.md
```

再按：

```text
examples/simulate_day.py
→ runtime.py
→ kernel.py
→ behavior.py / physiology.py
```

最后读迁移说明：

```text
docs/Migration_From_25-01.md
```
