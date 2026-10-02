# TempVirtualLife 代码讲解文档

这套文档针对当前仓库 `Caffeine-co/TempVirtualLife` 的 `main` 分支正式版代码编写。

目标不是再讲一遍“架构思想”，而是让你能够回答：

- `runtime.start()` 之后到底发生了什么？
- `sync()` 为什么能把停机期间补回来？
- `kernel.advance_to()` 为什么不需要每秒 tick？
- 行为为什么会从 `work` 切到 `travel` / `sleep`？
- `Goal / Habit / Memory / Schedule` 到底分别在哪一步进入决策？
- World 和 Perception 为什么要分开？
- 一个外界刺激是怎么变成情绪、记忆、关系变化和行为打断的？
- SQLite 三张表分别是什么？
- NoneBot 接入时应该调用谁、绝对不应该调用谁？
- 如果想增加新行为、新状态、新事件，应该改哪些文件？

## 推荐阅读顺序

```text
00_One_Page_Map.md
→ 01_Boot_Runtime.md
→ 02_Kernel_Time_Action.md
→ 03_Behavior_Decision.md
→ 04_Annotated_Core_Functions.md
→ 05_State_Models.md
→ 06_World_Schedule_Movement.md
→ 07_Psychology_Domains.md
→ 08_Events_Appraisal.md
→ 09_Persistence_NoneBot.md
→ 10_Debugging_Modification.md
→ 11_Full_Scenarios.md
→ 12_Glossary.md
```

阅读源码时始终把代码归入四类：

```text
事实（State）
发生了什么（Event）
规则怎么变（Kernel / Domain）
程序怎么承载（Runtime / Repository / Host）
```

如果一段代码暂时不知道属于哪一类，先回到这四个问题。
