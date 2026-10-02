# 11. Theory References：理论来源如何映射到代码

Formal Core 不宣称“已经精确复制真实人类”。这里列出的理论作用是给模型提供**稳定的方向约束和可解释变量**，避免重新回到“LLM 凭常识猜数值”。

## 1. Sleep：Two-Process Model

参考：

- Borbély AA, Daan S, Wirz-Justice A, Deboer T. *The two-process model of sleep regulation: a reappraisal*. Journal of Sleep Research. 2016;25(2):131-143. DOI: 10.1111/jsr.12371.

核心思想：

```text
Process S：睡眠稳态压力
+
Process C：昼夜节律过程
```

代码映射：

```text
physiology.py
→ sleep_pressure 指数积累/下降

behavior.py
→ circadian_sleep_drive()
```

当前 Process C 只是工程近似，后续可继续替换。

## 2. Affect：Circumplex / Core Affect

参考：

- Russell JA. *A circumplex model of affect*. Journal of Personality and Social Psychology. 1980;39(6):1161-1178. DOI: 10.1037/h0077714.

代码映射：

```text
AffectState.valence
AffectState.arousal
```

Formal Core 另外保存 `stress`，因为它对行为负担和长期恢复很实用。

## 3. Appraisal：Component Process Model

参考：

- Scherer KR. *Emotions are emergent processes: they require a dynamic computational architecture*. Philosophical Transactions of the Royal Society B. 2009;364:3459-3474. DOI: 10.1098/rstb.2009.0141.
- Scherer KR. *The dynamic architecture of emotion: Evidence for the component process model*. Cognition and Emotion. 2009;23(7):1307-1351. DOI: 10.1080/02699930902928969.

代码映射：

```text
AppraisalInput
├─ relevance
├─ goal_congruence
├─ controllability
├─ novelty
├─ social_evaluation
├─ threat
└─ urgency

RuleBasedAppraisal
→ MeaningEvent
```

未来 LLM 最适合替换“如何从复杂自然语言/社会情境得到 AppraisalInput”，而不是替换 Kernel。

## 4. Habit / Goal-directed behavior

参考：

- Wood W, Rünger D. *Psychology of Habit*. Annual Review of Psychology. 2016;67:289-314. DOI: 10.1146/annurev-psych-122414-033417.

核心思想：重复情境中的行为会形成较自动的上下文—反应关系，并与目标导向行为共同影响现实行为。

代码映射：

```text
habits.py
→ context-specific habit learning / decay

behavior.py
→ goal-directed score + habit score arbitration
```

## 5. Allostasis

参考：

- McEwen BS, Wingfield JC. *The concept of allostasis in biology and biomedicine*. Hormones and Behavior. 2003;43(1):2-15. DOI: 10.1016/S0018-506X(02)00024-7.

Formal Core 当前还没有实现完整 allostatic load 生物模型，但设计上已经把：

```text
current state
future schedule / goal
opportunity / environment
```

分开，为后续预测性需求模型保留位置。

## 6. 使用这些理论时的限制

这些理论不是一套能够精确输入“一个人现在所有变量”并输出“下一秒一定做什么”的统一方程。

因此项目应当追求：

```text
理论方向正确
时间尺度合理
因果链明确
可校准
长期行为统计自然
```

而不是追求虚假的“心理数值绝对精确”。
