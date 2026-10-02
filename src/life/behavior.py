from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta

from .actions import ActionDefinition
from .derived import derive_state
from .goals import dominant_goal, goal_bonus
from .habits import context_key, effective_habit_strength
from .memory import memory_action_bonus
from .models import LifeConfig, LifeState, PerceptionFrame, ScheduleBlock
from .movement import MovementService
from .schedule import ScheduleService


def _circular_distance_hours(a: float, b: float) -> float:
    diff = abs(a - b) % 24
    return min(diff, 24 - diff)


def circadian_sleep_drive(now: datetime, config: LifeConfig) -> float:
    """0~100 的昼夜睡眠倾向；后续可替换为更完整 Process C。"""

    hour = now.hour + now.minute / 60 + now.second / 3600
    sleep = config.rhythm.preferred_sleep_hour
    wake = config.rhythm.preferred_wake_hour
    duration = (wake - sleep) % 24 or 8.0
    midpoint = (sleep + duration / 2) % 24
    distance = _circular_distance_hours(hour, midpoint)
    sigma = max(2.5, duration / 2.4)
    return 100 * math.exp(-(distance * distance) / (2 * sigma * sigma))


@dataclass(frozen=True)
class BehaviorDecision:
    action_type: str
    reason: str
    score: float
    source: str
    target: str | None = None
    destination_place_id: str | None = None
    duration_minutes: float | None = None
    forced: bool = False


class BehaviorEngine:
    """Hard Constraint + Goal-directed Utility + Habit + bounded noise 的仲裁器。"""

    def __init__(
        self,
        actions: dict[str, ActionDefinition],
        schedule: ScheduleService,
        movement: MovementService,
        config: LifeConfig,
        rng: random.Random,
    ):
        self.actions = actions
        self.schedule = schedule
        self.movement = movement
        self.config = config
        self.rng = rng

    def _base_scores(
        self,
        state: LifeState,
        now: datetime,
        perception: PerceptionFrame,
    ) -> dict[str, float]:
        body = state.character.body
        affect = state.character.affect
        drives = state.character.drives
        profile = self.config.profile
        derived = derive_state(state)
        circadian = circadian_sleep_drive(now, self.config)

        scores = {
            "idle": 18.0,
            "sleep": body.sleep_pressure * 0.60 + body.physical_fatigue * 0.20 + circadian * 0.25,
            "eat": body.hunger * 0.95,
            "drink": (100 - body.hydration) * 1.10,
            "rest": body.physical_fatigue * 0.55 + (100 - body.energy) * 0.35 + affect.stress * 0.20,
            "socialize": drives.social_need * (0.55 + 0.45 * profile.social_reward) + drives.social_energy * 0.20,
            "communicate": drives.social_need * (0.50 + 0.40 * profile.social_reward) + drives.social_energy * 0.15,
            "create": drives.creative_urge * (0.55 + 0.45 * profile.creative_reward) + body.energy * 0.15 - affect.stress * 0.05,
            "work": drives.achievement_urge * (0.55 + 0.45 * profile.achievement_reward) + body.energy * 0.12 - body.physical_fatigue * 0.08,
            "leisure": drives.novelty_urge * (0.55 + 0.45 * profile.novelty_reward) + affect.stress * 0.25,
        }

        # 没有“人”在附近时，线下 socialize 不进入候选。
        if not any(entity.kind == "person" for entity in perception.nearby_entities):
            scores.pop("socialize", None)

        # 没有任何在线 Adapter 时，communicate 不进入候选。
        if not perception.available_adapters:
            scores.pop("communicate", None)

        # 白天普通疲劳不应该频繁触发 6~9 小时长睡。
        if circadian < 25 and body.sleep_pressure < 70 and body.physical_fatigue < 75:
            scores["sleep"] -= 35

        # 极低体力压低高投入行为，但不制造硬禁止。
        if body.energy < 15:
            for key, penalty in (("create", 25), ("work", 30), ("socialize", 15)):
                if key in scores:
                    scores[key] -= penalty

        # 低注意力降低工作/创作的目标导向执行质量。
        if derived.attention < 25:
            if "work" in scores:
                scores["work"] -= 15
            if "create" in scores:
                scores["create"] -= 10

        # home_place_id 不是硬命令，只提供“回到生活基地”的普通行为候选。
        home = self.config.home_place_id
        current_place = state.character.spatial.place_id
        if home and home != current_place:
            minutes = self.movement.travel_minutes(current_place, home)
            if minutes is not None:
                # 越接近睡眠时相、越疲劳，回家的倾向越高。
                scores["travel"] = 8.0 + circadian * 0.30 + body.physical_fatigue * 0.18

        return scores

    def next_required_departure_time(
        self,
        state: LifeState,
        now: datetime,
    ) -> datetime | None:
        """根据下一条 hard schedule 和当前位置，计算最晚应出发时间。"""

        upcoming = self.schedule.next_hard_start_after(now)
        if upcoming is None:
            return None
        start, block = upcoming
        if not block.place_id or block.place_id == state.character.spatial.place_id:
            return None
        minutes = self.movement.travel_minutes(
            state.character.spatial.place_id,
            block.place_id,
        )
        if minutes is None:
            raise ValueError(
                f"即将开始的 hard schedule {block.name} 要求地点 {block.place_id}，"
                f"但从 {state.character.spatial.place_id} 不可达"
            )
        departure = start - timedelta(minutes=minutes)
        return departure if departure > now else now

    def _upcoming_hard_travel_decision(
        self,
        state: LifeState,
        now: datetime,
    ) -> BehaviorDecision | None:
        upcoming = self.schedule.next_hard_start_after(now)
        if upcoming is None:
            return None
        start, block = upcoming
        if not block.place_id or block.place_id == state.character.spatial.place_id:
            return None
        minutes = self.movement.travel_minutes(
            state.character.spatial.place_id,
            block.place_id,
        )
        if minutes is None:
            return None
        departure = start - timedelta(minutes=minutes)
        if now < departure:
            return None
        return BehaviorDecision(
            action_type="travel",
            reason=f"hard_schedule_departure:{block.name}",
            score=math.inf,
            source="schedule",
            destination_place_id=block.place_id,
            duration_minutes=max(1.0, minutes),
            forced=True,
        )

    def _hard_schedule_decision(
        self,
        state: LifeState,
        now: datetime,
    ) -> BehaviorDecision | None:
        block = self.schedule.primary_hard_block(now)
        if block is None:
            return None

        current_place = state.character.spatial.place_id
        if block.place_id and block.place_id != current_place:
            minutes = self.movement.travel_minutes(current_place, block.place_id)
            if minutes is None:
                raise ValueError(
                    f"hard schedule {block.name} 要求地点 {block.place_id}，"
                    f"但从 {current_place} 不可达"
                )
            return BehaviorDecision(
                action_type="travel",
                reason=f"hard_schedule_travel:{block.name}",
                score=math.inf,
                source="schedule",
                destination_place_id=block.place_id,
                duration_minutes=max(1.0, minutes),
                forced=True,
            )

        # 地点已经满足时直接执行硬日程行为。
        if block.action_type not in self.actions:
            raise ValueError(f"日程 {block.name} 使用了未知 action_type={block.action_type}")
        return BehaviorDecision(
            action_type=block.action_type,
            reason=f"hard_schedule:{block.name}",
            score=math.inf,
            source="schedule",
            forced=True,
        )

    def _soft_schedule_bonus(self, now: datetime, action_type: str) -> float:
        bonus = 0.0
        for block in self.schedule.active_blocks(now):
            if block.mode == "soft" and block.action_type == action_type:
                bonus += 80.0 * block.weight * (1.1 - 0.4 * self.config.profile.autonomy_preference)
        return bonus

    def decide(
        self,
        state: LifeState,
        now: datetime,
        perception: PerceptionFrame,
        *,
        allow_continue: bool,
        external_bonus: dict[str, float] | None = None,
    ) -> BehaviorDecision:
        # Hard schedule 是真正约束，不进入随机 Utility 排名。
        hard = self._hard_schedule_decision(state, now)
        if hard is not None:
            return hard

        # hard schedule 尚未开始，但已经到达最晚出发时间时，提前进入 travel。
        departure = self._upcoming_hard_travel_decision(state, now)
        if departure is not None:
            return departure

        scores = self._base_scores(state, now, perception)
        derived = derive_state(state)

        # 注意力越差、认知负荷越高，越容易让习惯而非显式目标接管行为。
        goal_weight = self.config.tuning.goal_directed_base_weight
        goal_weight += (derived.attention - 50.0) / 250.0
        goal_weight -= state.character.cognition.cognitive_load / 500.0
        goal_weight = max(1.0 - self.config.habit.max_weight, min(0.95, goal_weight))
        habit_weight = min(
            self.config.habit.max_weight,
            (1.0 - goal_weight) * (0.7 + 0.6 * self.config.profile.routine_preference),
        )
        # 两类权重重新归一化，避免总和因为 personality 调制偏离 1。
        total_weight = goal_weight + habit_weight
        goal_weight /= total_weight
        habit_weight /= total_weight

        final_scores: dict[str, float] = {}
        reasons: dict[str, str] = {}
        for action_type, base in scores.items():
            directed = base
            directed += self._soft_schedule_bonus(now, action_type)
            directed += goal_bonus(state, action_type, now)
            directed += memory_action_bonus(state, self.config, action_type, now)
            if external_bonus:
                directed += external_bonus.get(action_type, 0.0)

            habit = effective_habit_strength(state, self.config, action_type, now) * 100.0
            combined = directed * goal_weight + habit * habit_weight

            # 噪声只用于接近的合理候选；impulsivity 会稍微放大它。
            noise = self.config.tuning.decision_noise * (
                0.7 + 0.6 * self.config.profile.impulsivity
            )
            combined += self.rng.gauss(0, noise) if noise > 0 else 0.0
            final_scores[action_type] = combined

            if external_bonus and external_bonus.get(action_type, 0) > 0:
                reasons[action_type] = "external_impulse"
            elif goal_bonus(state, action_type, now) > 0:
                reasons[action_type] = "goal"
            elif habit > directed * 0.5:
                reasons[action_type] = "habit"
            else:
                reasons[action_type] = "utility"

        best = max(final_scores, key=final_scores.get)

        # 普通重新评估时使用 hysteresis，防止 1~2 分的小差异导致行为来回抖动。
        current = state.character.action
        if allow_continue and current and current.type in final_scores:
            current_score = final_scores[current.type]
            threshold = self.config.tuning.switch_threshold
            threshold *= 0.5 + current.commitment
            threshold *= 0.75 + 0.75 * self.config.profile.persistence
            if final_scores[best] <= current_score + threshold:
                return BehaviorDecision(
                    action_type=current.type,
                    reason="continue",
                    score=current_score,
                    source=current.source,
                    target=current.target,
                    destination_place_id=current.destination_place_id,
                )

        source = reasons[best]
        destination = None
        duration = None
        target = None

        # Goal 可以要求行为在特定地点发生；此时先旅行，再回来继续 Goal 行为。
        goal = dominant_goal(state, best, now)
        if goal is not None:
            target = goal.target
            if (
                goal.required_place_id
                and goal.required_place_id != state.character.spatial.place_id
            ):
                minutes = self.movement.travel_minutes(
                    state.character.spatial.place_id,
                    goal.required_place_id,
                )
                if minutes is None:
                    raise ValueError(
                        f"goal {goal.goal_id} 要求地点 {goal.required_place_id}，"
                        f"但从 {state.character.spatial.place_id} 不可达"
                    )
                return BehaviorDecision(
                    action_type="travel",
                    reason=f"goal_travel:{goal.goal_id}",
                    score=final_scores[best],
                    source="goal",
                    destination_place_id=goal.required_place_id,
                    duration_minutes=max(1.0, minutes),
                )

        # 普通 Utility 选择 travel 时，当前唯一的自主目的地是 home_place_id。
        if best == "travel" and self.config.home_place_id:
            destination = self.config.home_place_id
            duration = self.movement.travel_minutes(
                state.character.spatial.place_id,
                destination,
            )

        return BehaviorDecision(
            action_type=best,
            reason=source,
            score=final_scores[best],
            source=source if source in {"goal", "habit"} else ("external" if source == "external_impulse" else "behavior"),
            target=target,
            destination_place_id=destination,
            duration_minutes=duration,
        )

    def start_action(
        self,
        state: LifeState,
        decision: BehaviorDecision,
        now: datetime,
    ):
        definition = self.actions[decision.action_type]
        duration = decision.duration_minutes
        if duration is None:
            duration = self.rng.uniform(
                definition.min_duration_minutes,
                definition.max_duration_minutes,
            )

        from .models import ActionState

        return ActionState(
            type=decision.action_type,
            started_at=now,
            expected_end_at=now + timedelta(minutes=duration),
            progress=0,
            interruptibility=definition.interruptibility,
            commitment=definition.commitment,
            source=decision.source,  # Pydantic 会再次校验 source。
            target=decision.target,
            destination_place_id=decision.destination_place_id,
            habit_context_key=context_key(state, now),
        )
