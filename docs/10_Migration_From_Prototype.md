# 10. Migration From Prototype

这份 Formal Core 可以直接覆盖当前 TempVirtualLife prototype 的对应路径。

## 1. 建议操作

先在本地新建分支：

```bash
git switch -c formal-life-core
```

把正式版压缩包解压到仓库根目录并允许覆盖：

```text
README.md
life.example.json
requirements-life.txt
src/life/**
examples/**
tests/**
docs/**
```

## 2. 建议删除的旧 prototype 文件

Formal Core 不再使用：

```text
docs/Life_Core_v2.md
docs/State_Ownership.md
docs/Migration_From_25-01.md
examples/simulate_day.py
examples/submit_impulse.py
```

仓库根目录的旧 `life_core_v2.zip` 也只是历史产物，可以删除。

## 3. 不需要动 bot.py

Formal Core 仍然可以先独立测试。

如果要挂 NoneBot，再创建一个薄 Host 模块：

```python
from src.life import build_life_runtime, load_life_config
from src.life.host import mount_to_nonebot

life_runtime = build_life_runtime(load_life_config("life.json"))
mount_to_nonebot(life_runtime)
```

## 4. 旧数据库不能直接复用

prototype 的 `life_snapshot.state_json` 使用旧 `CharacterRuntimeState` schema。

Formal Core 使用新的 `LifeState` aggregate，因此第一次迁移建议：

```text
备份旧 life.db
→ 使用新的数据库文件
→ 从 life.example.json / 配置重新冷启动
```

不要直接让新代码读取旧 snapshot。

后续如果正式项目已经有重要长期数据，再单独写 migration script。

## 5. 验证

覆盖后先运行：

```bash
python -m tests.run_all
```

再运行：

```bash
python -m examples.simulate_week
```

确认通过后再接 NoneBot。
