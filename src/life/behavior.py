from __future__ import annotations

import math
import random
from datetime import datetime, timedelta

from .actions import ActionDefinition
from .models import ActionState, CharacterRuntimeState, LifeConfig, ScheduleBlock
from .schedule import ScheduleService


def _circular_distance_hours(a: float, b: float) -> float:
    diff = abs(a - b) % 24
    return min(diff, 24 - diff)


def circadian_sleep_drive(now: datetime, config: LifeConfig) -> float:
    """0~100 的简化昼夜睡眠倾向。

    这不是最终生理模型，只负责让第一版行为选择具有基本昼夜节律。
    """

    hour = now.hour + now.minute / 60 + now.second / 3600
    sleep = config.rhythm.preferred_sleep_hour
    wake = config.rhythm.preferred_wake_hour

    duration = (wake - sleep) % 24
    if duration <= 0:
        duration = 8.0
    midpoint = (sleep + duration / 2) % 24

    distance = _circular_distance_hours(hour, midpoint)
    sigma = max(2.5, duration / 2.4)
    return 100 * math.exp(-(distance * distance) / (2 * sigma * sigma))


class BehaviorEngine:
    """使用约束 + Utility + 小幅决策噪声选择下一行为。"""

    def __init__(
        self,
        actions: dict[str, ActionDefinition],
        schedule: ScheduleService,
        config: LifeConfig,
        rng: random.Random,
    ):
        self.actions = actions
        self.schedule = schedule
        self.config = config
        self.rng = rng

    def _scores(
        self,
        state: CharacterRuntimeState,
        now: datetime,
        bonus: dict[str, float] | None = None,
    ) -> tuple[dict[str, float], ScheduleBlock | None]:
        body = state.body
        affect = state.affect
        drives = state.drives
        profile = self.config.profile

        circadian = circadian_sleep_drive(now, self.config)

        scores = {
            "idle": 20.0,
            "sleep": (
                body.sleep_pressure * 0.60
                + body.physical_fatigue * 0.20
                + circadian * 0.25
            ),
            "eat": body.hunger * 0.95,
            "drink": (100 - body.hydration) * 1.10,
            "rest": (
                body.physical_fatigue * 0.55
                + (100 - body.energy) * 0.35
                + affect.stress * 0.20
            ),
            "socialize": (
                drives.social_need * (0.55 + 0.45 * profile.social_reward)
                + drives.social_energy * 0.20
            ),
            "create": (
                drives.creative_urge * (0.55 + 0.45 * profile.creative_reward)
                + body.energy * 0.15
                - affect.stress * 0.05
            ),
            "work": (
                drives.achievement_urge * (0.55 + 0.45 * profile.achievement_reward)
                + body.energy * 0.12
                - body.physical_fatigue * 0.08
            ),
            "leisure": (
                drives.novelty_urge * (0.55 + 0.45 * profile.novelty_reward)
                + affect.stress * 0.25
            ),
        }

        # 普通情况下，人不会仅仅因为“有一点累”就在白天进入长睡眠。
        # 只有进入睡眠时相，或者睡眠压力/疲劳已经明显偏高时，sleep 才保持完整分数。
        # 这是一个第一版睡眠门控，后续可替换成更严格的 Process C / 睡眠机会模型。
        if circadian < 25 and body.sleep_pressure < 70 and body.physical_fatigue < 75:
            scores["sleep"] -= 35

        # 极低能量时压低高投入行为，但不直接写死“禁止”。
        if body.energy < 15:
            scores["create"] -= 25
            scores["work"] -= 30
            scores["socialize"] -= 15

        active_schedule = self.schedule.active_block(now)
        if active_schedule and active_schedule.action_type in scores:
            scores[active_schedule.action_type] += 120 * active_schedule.rigidity

        if bonus:
            for action_type, value in bonus.items():
                if action_type in scores:
                    scores[action_type] += value

        # 决策噪声只能改变“相近选项”，不能越过日程等硬约束。
        noise = self.config.tuning.decision_noise * (0.7 + 0.6 * profile.impulsivity)
        if noise > 0:
            for key in scores:
                scores[key] += self.rng.gauss(0, noise)

        return scores, active_schedule

    def choose_action(
        self,
        state: CharacterRuntimeState,
        now: datetime,
        *,
        force_reconsider: bool,
        bonus: dict[str, float] | None = None,
    ) -> tuple[str, str, ScheduleBlock | None]:
        scores, active_schedule = self._scores(state, now, bonus)
        best = max(scores, key=scores.get)

        if state.action and not force_reconsider:
            current_type = state.action.type
            current_score = scores.get(current_type, float("-inf"))
            threshold = self.config.tuning.switch_threshold * (
                0.5 + state.action.commitment
            ) * (0.75 + 0.75 * self.config.profile.persistence)
            if scores[best] <= current_score + threshold:
                return current_type, "continue", active_schedule

        if active_schedule and best == active_schedule.action_type:
            return best, f"schedule:{active_schedule.name}", active_schedule
        if bonus and best in bonus:
            return best, "external_impulse", active_schedule
        return best, "utility", active_schedule

    def start_action(
        self,
        action_type: str,
        now: datetime,
        *,
        source: str,
        target: str | None = None,
        duration_minutes: float | None = None,
    ) -> ActionState:
        definition = self.actions[action_type]
        duration = duration_minutes
        if duration is None:
            duration = self.rng.uniform(
                definition.min_duration_minutes,
                definition.max_duration_minutes,
            )

        return ActionState(
            type=action_type,
            started_at=now,
            expected_end_at=now + timedelta(minutes=duration),
            progress=0,
            interruptibility=definition.interruptibility,
            commitment=definition.commitment,
            source=source,  # type: ignore[arg-type]
            target=target,
        )
