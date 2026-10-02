from __future__ import annotations

import random
from datetime import datetime

from .actions import ActionDefinition, default_actions
from .affect import advance_affect, clamp as affect_clamp, upsert_emotion
from .behavior import BehaviorDecision, BehaviorEngine
from .goals import apply_action_progress, fail_expired_goals, next_goal_deadline
from .habits import reinforce_habit
from .health import advance_health, apply_health_impact
from .memory import add_memory, make_memory
from .models import (
    AdapterAvailabilityEvent,
    EntityPresenceEvent,
    ForceActionEvent,
    GoalProgressEvent,
    GoalUpsertEvent,
    HealthCondition,
    HealthImpactEvent,
    JournalRecord,
    LifeConfig,
    LifeEvent,
    LifeState,
    LocationChangedEvent,
    MeaningEvent,
    MemoryEvent,
    RelationshipEvent,
    WorldEnvironmentEvent,
)
from .movement import MovementService
from .perception import PerceptionService
from .physiology import advance_physiology, clamp
from .relationships import apply_relationship_delta
from .schedule import ScheduleService
from .world import WorldService


class LifeKernel:
    """纯生命状态转移核心。

    Kernel 不知道 NoneBot、SQLite、真实系统时间和 LLM。
    外界只需要给它一个 LifeState、目标时间或 LifeEvent。
    """

    def __init__(self, config: LifeConfig):
        self.config = config
        self.actions: dict[str, ActionDefinition] = default_actions()
        self.rng = random.Random(config.random_seed)

        # World / Schedule / Movement 都是纯领域服务，不做 I/O。
        self.world = WorldService(config)
        self.perception = PerceptionService(self.world)
        self.movement = MovementService(config)
        self.schedule = ScheduleService(config.schedule, config.timezone)
        self.behavior = BehaviorEngine(
            self.actions,
            self.schedule,
            self.movement,
            config,
            self.rng,
        )

    def create_initial_state(self, now: datetime) -> LifeState:
        """从配置冷启动一个新的生命快照。"""

        character = self.config.initial.model_dump(mode="python")
        from .models import CharacterState

        state = LifeState(
            revision=0,
            as_of=now,
            character=CharacterState(**character),
        )
        # 如果冷启动地点仍是 unknown，而地图恰好只有一个地点，就安全地使用它。
        if state.character.spatial.place_id == "unknown" and len(self.world.places) == 1:
            state.character.spatial.place_id = next(iter(self.world.places))
        return state

    def initialize(self, state: LifeState) -> list[JournalRecord]:
        """保证角色至少拥有一个当前行为。"""

        if state.character.action is not None:
            return []
        perception = self.perception.frame(state)
        decision = self.behavior.decide(
            state,
            state.as_of,
            perception,
            allow_continue=False,
        )
        return self._apply_decision(state, decision, replace_current=True)

    def next_wakeup_time(self, state: LifeState) -> datetime | None:
        """返回下一个值得 Runtime 醒来的内部时间点。"""

        candidates: list[datetime] = []
        action = state.character.action
        if action and action.expected_end_at > state.as_of:
            candidates.append(action.expected_end_at)

        schedule_boundary = self.schedule.next_boundary_after(state.as_of)
        if schedule_boundary is not None:
            candidates.append(schedule_boundary)

        deadline = next_goal_deadline(state, state.as_of)
        if deadline is not None:
            candidates.append(deadline)

        departure = self.behavior.next_required_departure_time(state, state.as_of)
        if departure is not None and departure > state.as_of:
            candidates.append(departure)

        return min(candidates) if candidates else None

    def advance_to(self, state: LifeState, target_time: datetime) -> list[JournalRecord]:
        """把 LifeState 从 as_of 连续推进到 target_time。"""

        if target_time < state.as_of:
            raise ValueError(
                f"不能倒退生命时间: state={state.as_of.isoformat()} target={target_time.isoformat()}"
            )

        records: list[JournalRecord] = []
        records.extend(self.initialize(state))
        steps = 0

        while state.as_of < target_time:
            steps += 1
            if steps > self.config.tuning.maximum_kernel_steps:
                raise RuntimeError("LifeKernel.advance_to 超过最大步数，疑似出现零时间事件循环")

            action = state.character.action
            action_end = action.expected_end_at if action else None
            schedule_boundary = self.schedule.next_boundary_after(state.as_of)
            goal_deadline = next_goal_deadline(state, state.as_of)
            departure_boundary = self.behavior.next_required_departure_time(state, state.as_of)

            candidates = [target_time]
            for candidate in (action_end, schedule_boundary, goal_deadline, departure_boundary):
                if candidate is not None and candidate > state.as_of:
                    candidates.append(candidate)

            boundary = min(candidates)
            old_as_of = state.as_of
            hours = (boundary - old_as_of).total_seconds() / 3600.0

            # 这一段时间内 Action 不变，因此连续动态可以一次性积分。
            action_def = self.actions[action.type] if action else self.actions["idle"]
            perception = self.perception.frame(state)
            advance_health(state, hours)
            advance_physiology(state, action_def, perception, hours, self.config)
            advance_affect(
                state,
                self.config.affect_baseline,
                hours,
                action_stress_per_hour=action_def.effects.stress,
                action_arousal_per_hour=action_def.effects.arousal,
            )

            state.as_of = boundary
            self._update_action_progress(state)

            # deadline 是内部离散边界，到点后立即更新 Goal status。
            if goal_deadline is not None and goal_deadline == state.as_of:
                for goal_id in fail_expired_goals(state, state.as_of):
                    records.append(
                        JournalRecord(
                            occurred_at=state.as_of,
                            kind="goal_failed",
                            data={"goal_id": goal_id},
                        )
                    )

            # Action 到期必须完成；完成以后由状态重新产生下一行为。
            if (
                state.character.action is not None
                and state.character.action.expected_end_at <= state.as_of
            ):
                records.extend(self._complete_current_action(state))

            # 日程边界允许重新评估，但普通情况下会应用 hysteresis。
            if schedule_boundary is not None and schedule_boundary == state.as_of:
                records.append(
                    JournalRecord(
                        occurred_at=state.as_of,
                        kind="schedule_boundary",
                        data={},
                    )
                )
                if state.character.action is not None:
                    records.extend(self._reconsider(state, reason="schedule_boundary"))

            if departure_boundary is not None and departure_boundary == state.as_of:
                records.append(
                    JournalRecord(
                        occurred_at=state.as_of,
                        kind="schedule_departure_boundary",
                        data={},
                    )
                )
                if state.character.action is not None:
                    records.extend(self._reconsider(state, reason="schedule_departure"))

            if state.character.action is None:
                perception = self.perception.frame(state)
                decision = self.behavior.decide(
                    state,
                    state.as_of,
                    perception,
                    allow_continue=False,
                )
                records.extend(self._apply_decision(state, decision, replace_current=True))

            if state.as_of == old_as_of:
                raise RuntimeError("LifeKernel.advance_to 未能推进时间")

        return records

    def handle_event(self, state: LifeState, event: LifeEvent) -> list[JournalRecord]:
        """把一个已经发生的离散事件应用到当前状态。"""

        if isinstance(event, MeaningEvent):
            return self._handle_meaning(state, event)
        if isinstance(event, LocationChangedEvent):
            return self._handle_location(state, event)
        if isinstance(event, ForceActionEvent):
            return self._handle_force_action(state, event)
        if isinstance(event, WorldEnvironmentEvent):
            state.world.environment_overrides[event.place_id] = event.environment
            return [self._record(state, "world_environment_changed", {"place_id": event.place_id})]
        if isinstance(event, EntityPresenceEvent):
            if event.present:
                state.world.entities[event.entity.entity_id] = event.entity
            else:
                state.world.entities.pop(event.entity.entity_id, None)
            return [
                self._record(
                    state,
                    "entity_presence_changed",
                    {"entity_id": event.entity.entity_id, "present": event.present},
                )
            ]
        if isinstance(event, AdapterAvailabilityEvent):
            state.world.adapters[event.adapter] = event.available
            records = [
                self._record(
                    state,
                    "adapter_availability_changed",
                    {"adapter": event.adapter, "available": event.available},
                )
            ]
            records.extend(self._reconsider(state, reason="adapter_availability"))
            return records
        if isinstance(event, GoalUpsertEvent):
            state.goals[event.goal.goal_id] = event.goal
            records = [self._record(state, "goal_upserted", {"goal_id": event.goal.goal_id})]
            records.extend(self._reconsider(state, reason="goal_changed"))
            return records
        if isinstance(event, GoalProgressEvent):
            goal = state.goals.get(event.goal_id)
            if goal is None:
                raise ValueError(f"未知 goal_id: {event.goal_id}")
            goal.progress = min(1.0, max(0.0, goal.progress + event.delta))
            if goal.progress >= 1.0:
                goal.status = "completed"
            return [
                self._record(
                    state,
                    "goal_progressed",
                    {"goal_id": event.goal_id, "progress": goal.progress},
                )
            ]
        if isinstance(event, RelationshipEvent):
            apply_relationship_delta(
                state,
                target_id=event.target_id,
                familiarity_delta=event.familiarity_delta,
                closeness_delta=event.closeness_delta,
                trust_delta=event.trust_delta,
                comfort_delta=event.comfort_delta,
                tension_delta=event.tension_delta,
                dependency_delta=event.dependency_delta,
                occurred_at=state.as_of,
            )
            return [self._record(state, "relationship_changed", {"target_id": event.target_id})]
        if isinstance(event, HealthImpactEvent):
            apply_health_impact(
                state,
                HealthCondition(
                    name=event.name,
                    severity=event.severity,
                    started_at=state.as_of,
                    recovery_half_life_hours=event.recovery_half_life_hours,
                    pain_effect=event.pain_effect,
                    fatigue_effect=event.fatigue_effect,
                    energy_penalty=event.energy_penalty,
                ),
            )
            return [self._record(state, "health_impact", {"name": event.name})]
        if isinstance(event, MemoryEvent):
            add_memory(state, self.config, event.memory)
            return [self._record(state, "memory_added", {"memory_id": event.memory.memory_id})]

        raise TypeError(f"未知 LifeEvent: {type(event)!r}")

    def _handle_meaning(self, state: LifeState, event: MeaningEvent) -> list[JournalRecord]:
        """处理已经完成 Appraisal 的语义刺激。"""

        scale = event.intensity
        affect = state.character.affect
        affect.valence = affect_clamp(affect.valence + event.valence * 30 * scale, -100, 100)
        affect.arousal = clamp(affect.arousal + event.arousal * 25 * scale)
        affect.stress = clamp(affect.stress + event.stress * 30 * scale)

        if event.emotion:
            upsert_emotion(
                state,
                name=event.emotion,
                intensity=event.intensity * 100,
                started_at=state.as_of,
                half_life_hours=event.emotion_half_life_hours,
                source=event.name,
            )

        if event.related_entity:
            # 单纯发生一次有意义互动只小幅提高 familiarity；关系价值变化应另发 RelationshipEvent。
            apply_relationship_delta(
                state,
                target_id=event.related_entity,
                familiarity_delta=1.5 * event.intensity,
                occurred_at=state.as_of,
            )

        if event.memory_salience > 0:
            action_bias: dict[str, float] = {}
            if event.target_action:
                # 正向事件使未来短期更愿意重复该行为，负向事件反之。
                action_bias[event.target_action] = event.valence * 25.0
            add_memory(
                state,
                self.config,
                make_memory(
                    occurred_at=state.as_of,
                    kind="meaning_event",
                    salience=event.memory_salience,
                    valence=event.valence,
                    related_entity=event.related_entity,
                    tags=[event.name],
                    action_bias=action_bias,
                ),
            )

        records = [
            self._record(
                state,
                "meaning_applied",
                {
                    "name": event.name,
                    "intensity": event.intensity,
                    "urgency": event.urgency,
                    "target_action": event.target_action,
                },
            )
        ]

        if not event.target_action or event.target_action not in self.actions:
            return records

        current = state.character.action
        current_interruptibility = current.interruptibility if current else 1.0
        interrupt_score = event.urgency * current_interruptibility
        if interrupt_score < self.config.tuning.interrupt_threshold:
            return records

        perception = self.perception.frame(state)
        decision = self.behavior.decide(
            state,
            state.as_of,
            perception,
            allow_continue=True,
            external_bonus={event.target_action: event.urgency * 80.0},
        )
        records.extend(self._apply_decision(state, decision, replace_current=False))
        return records

    def _handle_location(self, state: LifeState, event: LocationChangedEvent) -> list[JournalRecord]:
        spatial = state.character.spatial
        spatial.place_id = event.place_id
        spatial.zone_id = event.zone_id
        spatial.anchor_id = event.anchor_id
        spatial.position = event.position
        return [self._record(state, "location_changed", {"place_id": event.place_id})]

    def _handle_force_action(self, state: LifeState, event: ForceActionEvent) -> list[JournalRecord]:
        if event.action_type not in self.actions:
            raise ValueError(f"未知 action_type: {event.action_type}")

        decision = BehaviorDecision(
            action_type=event.action_type,
            reason="manual",
            score=float("inf"),
            source="manual",
            target=event.target,
            duration_minutes=event.duration_minutes,
            forced=True,
        )
        return self._apply_decision(state, decision, replace_current=True)

    def _complete_current_action(self, state: LifeState) -> list[JournalRecord]:
        action = state.character.action
        if action is None:
            return []

        duration_hours = max(
            0.0,
            (action.expected_end_at - action.started_at).total_seconds() / 3600.0,
        )
        records: list[JournalRecord] = [
            self._record(
                state,
                "action_completed",
                {"action": action.type, "target": action.target},
            )
        ]

        # 完成时效果用于“进食完成”“到达目的地”等离散结果。
        body = state.character.body
        drives = state.character.drives
        if action.type == "eat":
            body.hunger = clamp(body.hunger - 40)
        elif action.type == "drink":
            body.hydration = clamp(body.hydration + 30)
        elif action.type in {"socialize", "communicate"}:
            drives.social_need = clamp(drives.social_need - 15)
        elif action.type == "create":
            drives.creative_urge = clamp(drives.creative_urge - 12)
        elif action.type == "work":
            drives.achievement_urge = clamp(drives.achievement_urge - 12)
        elif action.type == "leisure":
            drives.novelty_urge = clamp(drives.novelty_urge - 12)
        elif action.type == "rest":
            state.character.affect.stress = clamp(state.character.affect.stress - 5)
        elif action.type == "travel" and action.destination_place_id:
            state.character.spatial.place_id = action.destination_place_id
            state.character.spatial.zone_id = None
            state.character.spatial.anchor_id = None
            state.character.spatial.position = None
            state.character.spatial.locomotion = "idle"
            records.append(
                self._record(
                    state,
                    "travel_arrived",
                    {"place_id": action.destination_place_id},
                )
            )

        # Goal 与 Habit 都在行为真正完成后更新，而不是行为一开始就奖励。
        for goal_id in apply_action_progress(
            state,
            action_type=action.type,
            target=action.target,
            duration_hours=duration_hours,
        ):
            records.append(self._record(state, "goal_completed", {"goal_id": goal_id}))

        habit = reinforce_habit(
            state,
            self.config,
            action.type,
            state.as_of,
            original_context=action.habit_context_key,
        )
        records.append(
            self._record(
                state,
                "habit_reinforced",
                {
                    "action": action.type,
                    "context": habit.context_key,
                    "strength": habit.strength,
                },
            )
        )

        state.character.action = None
        return records

    def _reconsider(self, state: LifeState, *, reason: str) -> list[JournalRecord]:
        if state.character.action is None:
            return []
        perception = self.perception.frame(state)
        decision = self.behavior.decide(
            state,
            state.as_of,
            perception,
            allow_continue=True,
        )
        return self._apply_decision(state, decision, replace_current=False, trigger=reason)

    def _apply_decision(
        self,
        state: LifeState,
        decision: BehaviorDecision,
        *,
        replace_current: bool,
        trigger: str | None = None,
    ) -> list[JournalRecord]:
        current = state.character.action

        # decide() 明确要求 continue 时，不重建 ActionState，这样 started_at/progress 不丢失。
        if current is not None and decision.action_type == current.type and not replace_current:
            # 对 travel 还要保证目的地一致；否则同类动作也属于切换。
            same_destination = (
                decision.action_type != "travel"
                or decision.destination_place_id in {None, current.destination_place_id}
            )
            if same_destination:
                return []

        records: list[JournalRecord] = []
        if current is not None:
            records.append(
                self._record(
                    state,
                    "action_interrupted",
                    {
                        "action": current.type,
                        "reason": trigger or decision.reason,
                    },
                )
            )

        state.character.action = self.behavior.start_action(
            state,
            decision,
            state.as_of,
        )
        if decision.action_type == "travel":
            state.character.spatial.locomotion = "walking"
            state.character.spatial.posture = "moving"
        else:
            state.character.spatial.locomotion = "idle"
            if state.character.spatial.posture == "moving":
                state.character.spatial.posture = "standing"

        records.append(
            self._record(
                state,
                "action_started",
                {
                    "action": state.character.action.type,
                    "reason": decision.reason,
                    "score": decision.score,
                    "source": state.character.action.source,
                    "target": state.character.action.target,
                    "destination_place_id": state.character.action.destination_place_id,
                    "expected_end_at": state.character.action.expected_end_at.isoformat(),
                },
            )
        )
        return records

    @staticmethod
    def _update_action_progress(state: LifeState) -> None:
        action = state.character.action
        if action is None:
            return
        total = (action.expected_end_at - action.started_at).total_seconds()
        if total <= 0:
            action.progress = 1.0
            return
        elapsed = (state.as_of - action.started_at).total_seconds()
        action.progress = max(0.0, min(1.0, elapsed / total))

    @staticmethod
    def _record(state: LifeState, kind: str, data: dict) -> JournalRecord:
        return JournalRecord(occurred_at=state.as_of, kind=kind, data=data)
