# 07. Configuration

主配置见 `life.example.json`。

## initial

只描述冷启动，不指定正在执行的 Action。

## rhythm

```text
preferred_sleep_hour
preferred_wake_hour
Process S tau
```

## profile

长期行为先验，而不是每轮动态状态：

```text
social_reward
creative_reward
achievement_reward
novelty_reward
persistence
impulsivity
routine_preference
autonomy_preference
```

其中目前真正进入算法的主要是前六项；后两项保留给后续更细规划器使用。

## habit

```text
learning_rate
half_life_days
max_weight
```

## memory

限制结构化 MemoryTrace 数量和行为影响衰减速度。

## tuning

这是工程算法参数，不是人物设定。

## world

定义地点和旅行边。

## schedule

`mode`：

```text
hard -> 真正约束
soft -> Utility bonus
```
