# 09. Testing / Calibration

正式版把测试分成两种。

## A. 工程正确性

当前：

```text
smoke_test
recovery_test
schedule_movement_test
future_event_test
domain_modules_test
long_simulation_test
```

它们验证：

```text
状态不会越界
时间能前进
行为能结束
Hard Schedule 可驱动 Travel
未来事件不会丢
停机恢复正常
Domain State 可持久化
30 天不会死循环
```

## B. 模型合理性

后续应该增加统计测试，而不是写死某个瞬间数字。

建议观察：

```text
24h/7d 睡眠时段
一天行为切换次数
单行为持续时间分布
Hard Schedule 违约率
疲劳/能量日内曲线
情绪恢复时间
Habit 重复率
Goal 完成率
收到刺激后的 interruption rate
```

## 校准方法

```text
Theory / Character facts
↓
SimulationClock 跑 7~30 天
↓
统计行为轨迹
↓
发现偏差
↓
只调整对应模块参数
```

不要为了修一个问题同时改 5 个模块。

## 回归原则

任何算法升级后至少运行：

```bash
python -m tests.run_all
```

如果改变 Behavior，应额外跑长模拟并人工查看 `life_event`。
