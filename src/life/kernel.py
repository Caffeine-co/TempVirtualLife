from __future__ import annotations

import random
from datetime import datetime

from .actions import ActionDefinition, default_actions
from .behavior import BehaviorEngine
from .models import (
    CharacterRuntimeState,
    ForceActionEvent,
    ImpulseEvent,
    JournalRecord,
    LifeConfig,
    LifeEvent,
    LocationChangedEvent,
)
from .physiology import advance_continuous, clamp
from .schedule import ScheduleService


class LifeKernel:
    """纯生命逻辑核心。

    它不知道 NoneBot、OneBot、SQLite，也不主动读取真实时间。
    Runtime 把“现在几点”“发生了什么”传进来，它只负责状态转移。
    """

    def __init__(self, config: LifeConfig):
        self.config = config
        self.actions: dict[str, ActionDefinition] = default_actions()
        self.schedule = ScheduleService(config.schedule, config.timezone)
        self.rng = random.Random(config.random_seed)
        self.behavior = BehaviorEngine(
            self.actions,
            self.schedule,
            config,
            self.rng,
        )

    def initialize(self, state: CharacterRuntimeState) -> list[JournalRecord]:
        records: list[JournalRecord] = []
        if state.action is None:
            records.extend(self._select_and_start_action(state, state.as_of, True))
        return records

    def next_wakeup_time(self, state: CharacterRuntimeState) -> datetime | None:
        candidates: list[datetime] = []
        if state.action and state.action.expected_end_at > state.as_of:
            candidates.append(state.action.expected_end_at)

        boundary = self.schedule.next_boundary_after(state.as_of)
        if boundary:
            candidates.append(boundary)

        return min(candidates) if candidates else None

    def advance_to(
        self,
        state: CharacterRuntimeState,
        target_time: datetime,
    ) -> list[JournalRecord]:
        """把状态从 state.as_of 连续推进到 target_time。"""

        if target_time < state.as_of:
            raise ValueError(
                f"不能倒退时间: state={state.as_of.isoformat()} target={target_time.isoformat()}"
            )

        records: list[JournalRecord] = []
        records.extend(self.initialize(state))

        while state.as_of < target_time:
            action_end = state.action.expected_end_at if state.action else None
            schedule_boundary = self.schedule.next_boundary_after(state.as_of)

            candidates = [target_time]
            if action_end and action_end > state.as_of:
                candidates.append(action_end)
            if schedule_boundary and schedule_boundary > state.as_of:
                candidates.append(schedule_boundary)

            boundary = min(candidates)
            old_as_of = state.as_of
            hours = (boundary - old_as_of).total_seconds() / 3600

            action_def = self.actions[state.action.type] if state.action else self.actions["idle"]
            advance_continuous(state, action_def, hours, self.config)
            state.as_of = boundary
            self._update_action_progress(state)

            ended = bool(
                state.action
                and state.action.expected_end_at <= state.as_of
            )
            hit_schedule_boundary = bool(
                schedule_boundary
                and schedule_boundary == state.as_of
            )

            if ended:
                records.extend(self._complete_current_action(state))

            if hit_schedule_boundary:
                records.append(
                    JournalRecord(
                        occurred_at=state.as_of,
                        kind="schedule_boundary",
                        data={},
                    )
                )
                if state.action is not None:
                    # 到了日程边界，允许重新评估，但仍由 Utility + 日程刚性决定。
                    records.extend(self._reconsider_current_action(state))

            if state.action is None:
                records.extend(self._select_and_start_action(state, state.as_of, True))

            # 防御性检查，避免未来新增规则时意外形成零时间死循环。
            if state.as_of == old_as_of:
                raise RuntimeError("LifeKernel.advance_to 未能推进时间")

        return records

    def handle_event(
        self,
        state: CharacterRuntimeState,
        event: LifeEvent,
    ) -> list[JournalRecord]:
        """应用一个已经发生的离散事件。"""

        if isinstance(event, ImpulseEvent):
            return self._handle_impulse(state, event)
        if isinstance(event, LocationChangedEvent):
            state.spatial.place_id = event.place_id
            state.spatial.zone_id = event.zone_id
            state.spatial.anchor_id = event.anchor_id
            return [
                JournalRecord(
                    occurred_at=state.as_of,
                    kind="location_changed",
                    data={
                        "place_id": event.place_id,
                        "zone_id": event.zone_id,
                        "anchor_id": event.anchor_id,
                    },
                )
            ]
        if isinstance(event, ForceActionEvent):
            return self._force_action(state, event)
        raise TypeError(f"未知事件类型: {type(event)!r}")

    def _handle_impulse(
        self,
        state: CharacterRuntimeState,
        event: ImpulseEvent,
    ) -> list[JournalRecord]:
        scale = event.intensity
        state.affect.valence = clamp(
            state.affect.valence + event.valence * 30 * scale,
            -100,
            100,
        )
        state.affect.arousal = clamp(
            state.affect.arousal + event.arousal * 25 * scale
        )
        state.affect.stress = clamp(
            state.affect.stress + event.stress * 30 * scale
        )

        records = [
            JournalRecord(
                occurred_at=state.as_of,
                kind="impulse_applied",
                data={
                    "name": event.name,
                    "intensity": event.intensity,
                    "urgency": event.urgency,
                    "target_action": event.target_action,
                },
            )
        ]

        if not event.target_action or event.target_action not in self.actions:
            return records

        current_interruptibility = (
            state.action.interruptibility if state.action else 1.0
        )
        interrupt_score = event.urgency * current_interruptibility
        if interrupt_score < self.config.tuning.interrupt_threshold:
            return records

        bonus = {event.target_action: event.urgency * 80}
        selected, reason, schedule = self.behavior.choose_action(
            state,
            state.as_of,
            force_reconsider=True,
            bonus=bonus,
        )

        if state.action and selected == state.action.type:
            return records

        if state.action:
            records.append(
                JournalRecord(
                    occurred_at=state.as_of,
                    kind="action_interrupted",
                    data={
                        "action": state.action.type,
                        "reason": event.name,
                    },
                )
            )

        source = "schedule" if reason.startswith("schedule:") else "external"
        state.action = self.behavior.start_action(
            selected,
            state.as_of,
            source=source,
        )
        self._apply_schedule_location(state, schedule)
        records.append(self._action_started_record(state, reason))
        return records

    def _force_action(
        self,
        state: CharacterRuntimeState,
        event: ForceActionEvent,
    ) -> list[JournalRecord]:
        if event.action_type not in self.actions:
            raise ValueError(f"未知 action_type: {event.action_type}")

        records: list[JournalRecord] = []
        if state.action:
            records.append(
                JournalRecord(
                    occurred_at=state.as_of,
                    kind="action_interrupted",
                    data={"action": state.action.type, "reason": "force_action"},
                )
            )

        state.action = self.behavior.start_action(
            event.action_type,
            state.as_of,
            source="manual",
            target=event.target,
            duration_minutes=event.duration_minutes,
        )
        records.append(self._action_started_record(state, "manual"))
        return records

    def _complete_current_action(
        self,
        state: CharacterRuntimeState,
    ) -> list[JournalRecord]:
        if state.action is None:
            return []

        action_type = state.action.type
        completed = JournalRecord(
            occurred_at=state.as_of,
            kind="action_completed",
            data={"action": action_type},
        )

        # 第一版使用少量完成时效果，避免把“吃饭 20 分钟”写成复杂摄食模型。
        if action_type == "eat":
            state.body.hunger = clamp(state.body.hunger - 40)
        elif action_type == "drink":
            state.body.hydration = clamp(state.body.hydration + 30)
        elif action_type == "socialize":
            state.drives.social_need = clamp(state.drives.social_need - 20)
        elif action_type == "create":
            state.drives.creative_urge = clamp(state.drives.creative_urge - 15)
        elif action_type == "work":
            state.drives.achievement_urge = clamp(state.drives.achievement_urge - 15)
        elif action_type == "leisure":
            state.drives.novelty_urge = clamp(state.drives.novelty_urge - 15)
        elif action_type == "rest":
            state.affect.stress = clamp(state.affect.stress - 5)

        state.action = None
        return [completed]

    def _reconsider_current_action(
        self,
        state: CharacterRuntimeState,
    ) -> list[JournalRecord]:
        if state.action is None:
            return []

        selected, reason, schedule = self.behavior.choose_action(
            state,
            state.as_of,
            force_reconsider=True,
        )
        if selected == state.action.type:
            self._apply_schedule_location(state, schedule)
            return []

        old = state.action.type
        state.action = self.behavior.start_action(
            selected,
            state.as_of,
            source="schedule" if reason.startswith("schedule:") else "behavior",
        )
        self._apply_schedule_location(state, schedule)
        return [
            JournalRecord(
                occurred_at=state.as_of,
                kind="action_switched",
                data={"from": old, "to": selected, "reason": reason},
            ),
            self._action_started_record(state, reason),
        ]

    def _select_and_start_action(
        self,
        state: CharacterRuntimeState,
        now: datetime,
        force_reconsider: bool,
    ) -> list[JournalRecord]:
        selected, reason, schedule = self.behavior.choose_action(
            state,
            now,
            force_reconsider=force_reconsider,
        )
        source = "schedule" if reason.startswith("schedule:") else "behavior"
        state.action = self.behavior.start_action(
            selected,
            now,
            source=source,
        )
        self._apply_schedule_location(state, schedule)
        return [self._action_started_record(state, reason)]

    def _apply_schedule_location(
        self,
        state: CharacterRuntimeState,
        schedule,
    ) -> None:
        if schedule and schedule.action_type == state.action.type and schedule.place_id:
            state.spatial.place_id = schedule.place_id
            state.spatial.zone_id = None
            state.spatial.anchor_id = None

    @staticmethod
    def _update_action_progress(state: CharacterRuntimeState) -> None:
        if state.action is None:
            return
        total = (state.action.expected_end_at - state.action.started_at).total_seconds()
        if total <= 0:
            state.action.progress = 1
            return
        elapsed = (state.as_of - state.action.started_at).total_seconds()
        state.action.progress = max(0.0, min(1.0, elapsed / total))

    @staticmethod
    def _action_started_record(
        state: CharacterRuntimeState,
        reason: str,
    ) -> JournalRecord:
        assert state.action is not None
        return JournalRecord(
            occurred_at=state.as_of,
            kind="action_started",
            data={
                "action": state.action.type,
                "reason": reason,
                "expected_end_at": state.action.expected_end_at.isoformat(),
            },
        )
