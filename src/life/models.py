from __future__ import annotations

from datetime import datetime, time
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


Score = Annotated[float, Field(ge=0, le=100)]
BipolarScore = Annotated[float, Field(ge=-100, le=100)]
UnitScore = Annotated[float, Field(ge=0, le=1)]


class SchemaModel(BaseModel):
    """所有 Life Core 数据模型的共同基类。"""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class SpatialState(SchemaModel):
    """角色在世界里的语义位置。

    第一版不强制使用 3D 坐标。以后接 Unity / Godot 时可以继续扩展。
    """

    place_id: str = "unknown"
    zone_id: str | None = None
    anchor_id: str | None = None
    posture: Literal["standing", "sitting", "lying", "moving"] = "standing"


class BodyState(SchemaModel):
    """需要真正持久化的基础生理状态。"""

    energy: Score = 65
    physical_fatigue: Score = 25
    sleep_pressure: Score = 30
    sleep_debt: Score = 20
    hunger: Score = 30
    hydration: Score = 75
    pain: Score = 0
    physiological_arousal: Score = 40
    sensory_load: Score = 20
    health: Score = 100


class AffectState(SchemaModel):
    """低维连续情感状态。

    valence: -100 表示强负面，+100 表示强正面。
    arousal / stress 使用 0~100。
    """

    valence: BipolarScore = 0
    arousal: Score = 40
    stress: Score = 20


class DriveState(SchemaModel):
    """行为系统真正消费的动态驱动力。"""

    social_need: Score = 35
    social_energy: Score = 70
    creative_urge: Score = 45
    achievement_urge: Score = 45
    novelty_urge: Score = 35


class ActionState(SchemaModel):
    """当前正在执行的行为。

    行为不是一句自由文本，而是一条有开始、预计结束、可中断性的事实。
    """

    type: str
    started_at: datetime
    expected_end_at: datetime
    progress: UnitScore = 0
    interruptibility: UnitScore = 0.5
    commitment: UnitScore = 0.5
    source: Literal["behavior", "schedule", "external", "manual"] = "behavior"
    target: str | None = None


class CharacterRuntimeState(SchemaModel):
    """Life Runtime 唯一权威的实时状态快照。"""

    revision: int = 0
    as_of: datetime
    spatial: SpatialState = Field(default_factory=SpatialState)
    body: BodyState = Field(default_factory=BodyState)
    affect: AffectState = Field(default_factory=AffectState)
    drives: DriveState = Field(default_factory=DriveState)
    action: ActionState | None = None


class BiologicalRhythm(SchemaModel):
    """长期节律参数，不属于高频 Runtime 状态。"""

    preferred_sleep_hour: float = Field(default=23.5, ge=0, lt=24)
    preferred_wake_hour: float = Field(default=7.5, ge=0, lt=24)
    sleep_pressure_awake_tau_hours: float = Field(default=16.0, gt=0)
    sleep_pressure_sleep_tau_hours: float = Field(default=4.0, gt=0)


class BehavioralProfile(SchemaModel):
    """长期行为先验。

    默认值全部是中性值，不对应任何具体角色。
    """

    social_reward: UnitScore = 0.5
    creative_reward: UnitScore = 0.5
    achievement_reward: UnitScore = 0.5
    novelty_reward: UnitScore = 0.5
    persistence: UnitScore = 0.5
    impulsivity: UnitScore = 0.5


class AffectBaseline(SchemaModel):
    """没有新事件时，情感状态缓慢回归的长期基线。"""

    valence: BipolarScore = 0
    arousal: Score = 35
    stress: Score = 20
    half_life_hours: float = Field(default=6.0, gt=0)


class RuntimeTuning(SchemaModel):
    """工程调参项，不属于角色设定。"""

    decision_noise: float = Field(default=3.0, ge=0)
    switch_threshold: float = Field(default=12.0, ge=0)
    interrupt_threshold: float = Field(default=0.35, ge=0, le=1)


class ScheduleBlock(SchemaModel):
    """每周重复的日程块。

    weekdays 使用 Python 标准：周一=0，周日=6。
    """

    name: str
    weekdays: list[int] = Field(default_factory=list)
    start: time
    end: time
    action_type: str
    place_id: str | None = None
    rigidity: UnitScore = 0.8


class LifeConfig(SchemaModel):
    timezone: str = "Asia/Tokyo"
    database_path: str = "life.db"
    random_seed: int | None = None
    rhythm: BiologicalRhythm = Field(default_factory=BiologicalRhythm)
    profile: BehavioralProfile = Field(default_factory=BehavioralProfile)
    affect_baseline: AffectBaseline = Field(default_factory=AffectBaseline)
    tuning: RuntimeTuning = Field(default_factory=RuntimeTuning)
    schedule: list[ScheduleBlock] = Field(default_factory=list)


class ImpulseEvent(SchemaModel):
    """已经经过语义解释后的外部/内部刺激。

    Life Core 不负责理解原始自然语言。以后 LLM Appraisal 层可以把原始消息
    转成这种结构，再交给 Kernel。
    """

    type: Literal["impulse"] = "impulse"
    occurred_at: datetime
    name: str
    intensity: UnitScore = 0.5
    urgency: UnitScore = 0.0
    valence: float = Field(default=0.0, ge=-1, le=1)
    arousal: float = Field(default=0.0, ge=-1, le=1)
    stress: float = Field(default=0.0, ge=-1, le=1)
    target_action: str | None = None


class LocationChangedEvent(SchemaModel):
    type: Literal["location_changed"] = "location_changed"
    occurred_at: datetime
    place_id: str
    zone_id: str | None = None
    anchor_id: str | None = None


class ForceActionEvent(SchemaModel):
    """调试、管理员命令或未来上层规划器可以使用的强制行为事件。"""

    type: Literal["force_action"] = "force_action"
    occurred_at: datetime
    action_type: str
    duration_minutes: float | None = Field(default=None, gt=0)
    target: str | None = None


LifeEvent = ImpulseEvent | LocationChangedEvent | ForceActionEvent


class JournalRecord(SchemaModel):
    """用于解释“为什么现在会变成这样”的事件日志。"""

    occurred_at: datetime
    kind: str
    data: dict = Field(default_factory=dict)


class DerivedState(SchemaModel):
    """不持久化、随时可以从 Runtime State 重新计算的指标。"""

    sleepiness: Score
    thirst: Score
    physical_stamina: Score
    attention: Score
    mental_clarity: Score
    available_for_interruption: Score
    mood_label: str


class RuntimeView(SchemaModel):
    state: CharacterRuntimeState
    derived: DerivedState
