from __future__ import annotations

from datetime import datetime, time
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


# 0~100 的通用标量。大多数身体、认知和驱动力都使用这个范围。
Score = Annotated[float, Field(ge=0, le=100)]
# -100~100 的双极标量。情绪正负性使用它，0 表示中性。
BipolarScore = Annotated[float, Field(ge=-100, le=100)]
# 0~1 的归一化标量。人格先验、刚性、可打断性等使用它。
UnitScore = Annotated[float, Field(ge=0, le=1)]


class SchemaModel(BaseModel):
    """所有 Life 数据结构共同使用的严格 Pydantic 基类。"""

    # extra="forbid" 可以尽早发现拼错字段或过期配置。
    # validate_assignment=True 则让运行时赋值也继续受范围约束。
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Vec3(SchemaModel):
    """局部三维坐标。第一版不强迫每个地点都必须使用坐标。"""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class SpatialState(SchemaModel):
    """角色在世界里的当前空间事实。"""

    place_id: str = "unknown"
    zone_id: str | None = None
    anchor_id: str | None = None
    position: Vec3 | None = None
    posture: Literal["standing", "sitting", "lying", "moving"] = "standing"
    locomotion: Literal["idle", "walking", "running", "vehicle"] = "idle"


class BodyState(SchemaModel):
    """需要真正持久化的基础生理变量。"""

    energy: Score = 65
    physical_fatigue: Score = 25
    sleep_pressure: Score = 30
    sleep_debt: Score = 20
    hunger: Score = 30
    hydration: Score = 75
    pain: Score = 0
    physiological_arousal: Score = 40
    sensory_load: Score = 20


class CognitionState(SchemaModel):
    """少量需要保留历史连续性的认知状态。"""

    # cognitive_load 表示当前任务占用了多少认知资源。
    cognitive_load: Score = 20
    # rumination 表示有多少注意资源被反复思考占用。
    rumination: Score = 15


class SalientEmotion(SchemaModel):
    """只保存当前真正显著的离散情绪，而不是让所有情绪永远占一个字段。"""

    name: str
    intensity: Score
    started_at: datetime
    half_life_hours: float = Field(default=2.0, gt=0)
    source: str | None = None


class AffectState(SchemaModel):
    """连续核心情感 + 当前显著情绪。"""

    valence: BipolarScore = 0
    arousal: Score = 40
    stress: Score = 20
    emotions: list[SalientEmotion] = Field(default_factory=list)


class DriveState(SchemaModel):
    """BehaviorEngine 真正消费的动态驱动力。"""

    social_need: Score = 35
    social_energy: Score = 70
    creative_urge: Score = 45
    achievement_urge: Score = 45
    novelty_urge: Score = 35


class ActionState(SchemaModel):
    """当前正在执行的行为实例。"""

    type: str
    started_at: datetime
    expected_end_at: datetime
    progress: UnitScore = 0
    interruptibility: UnitScore = 0.5
    commitment: UnitScore = 0.5
    source: Literal["behavior", "schedule", "external", "manual", "goal", "habit"] = "behavior"
    target: str | None = None
    destination_place_id: str | None = None
    # 行为开始时的上下文快照，用于行为完成后正确强化 Habit。
    habit_context_key: str | None = None


class CharacterState(SchemaModel):
    """角色当前实时状态。时间和 revision 放在更外层的 LifeState。"""

    spatial: SpatialState = Field(default_factory=SpatialState)
    body: BodyState = Field(default_factory=BodyState)
    cognition: CognitionState = Field(default_factory=CognitionState)
    affect: AffectState = Field(default_factory=AffectState)
    drives: DriveState = Field(default_factory=DriveState)
    action: ActionState | None = None


class HealthCondition(SchemaModel):
    """当前持续存在的健康状态，例如感冒、受伤、头痛。"""

    name: str
    severity: Score
    started_at: datetime
    recovery_half_life_hours: float = Field(default=24.0, gt=0)
    pain_effect: Score = 0
    fatigue_effect: Score = 0
    energy_penalty: Score = 0


class HealthState(SchemaModel):
    conditions: dict[str, HealthCondition] = Field(default_factory=dict)


class EnvironmentState(SchemaModel):
    """某个地点当前的可感知环境。"""

    noise: Score = 20
    crowding: Score = 10
    privacy: Score = 70
    comfort: Score = 70
    temperature_c: float = 22.0
    light: Score = 60


class WorldEntity(SchemaModel):
    """世界中角色可能感知到的实体。"""

    entity_id: str
    kind: Literal["person", "object", "device", "other"] = "other"
    place_id: str
    zone_id: str | None = None
    active: bool = True
    tags: list[str] = Field(default_factory=list)


class WorldState(SchemaModel):
    """运行时会变化的世界状态。静态地图定义放在 LifeConfig.world。"""

    # key=place_id。未出现的地点使用配置里的默认环境。
    environment_overrides: dict[str, EnvironmentState] = Field(default_factory=dict)
    # key=entity_id。
    entities: dict[str, WorldEntity] = Field(default_factory=dict)
    # key=adapter name，例如 onebot/web。True 表示该通信渠道当前可用。
    adapters: dict[str, bool] = Field(default_factory=dict)


class GoalState(SchemaModel):
    """结构化目标/任务。它不是自由文本计划器。"""

    goal_id: str
    title: str
    action_type: str
    priority: UnitScore = 0.5
    progress: UnitScore = 0
    progress_per_hour: float = Field(default=0.1, gt=0)
    deadline: datetime | None = None
    target: str | None = None
    required_place_id: str | None = None
    status: Literal["active", "completed", "failed", "cancelled"] = "active"


class RelationshipState(SchemaModel):
    """角色与某一个具体对象之间的关系边。"""

    target_id: str
    familiarity: Score = 0
    closeness: Score = 0
    trust: Score = 50
    comfort: Score = 50
    tension: Score = 0
    dependency: Score = 0
    last_interaction_at: datetime | None = None


class HabitState(SchemaModel):
    """某个上下文中形成的行为习惯。"""

    context_key: str
    action_type: str
    strength: UnitScore = 0
    repetitions: int = Field(default=0, ge=0)
    last_performed_at: datetime | None = None


class MemoryTrace(SchemaModel):
    """不依赖 LLM 的结构化记忆痕迹。"""

    memory_id: str
    occurred_at: datetime
    kind: str
    salience: UnitScore = 0.5
    valence: float = Field(default=0.0, ge=-1, le=1)
    related_entity: str | None = None
    tags: list[str] = Field(default_factory=list)
    # action_bias 可以让某段记忆暂时提高/降低某类行为效用。
    action_bias: dict[str, float] = Field(default_factory=dict)
    note: str | None = None


class LifeState(SchemaModel):
    """数据库里唯一权威的完整生命快照。"""

    revision: int = Field(default=0, ge=0)
    as_of: datetime
    character: CharacterState = Field(default_factory=CharacterState)
    world: WorldState = Field(default_factory=WorldState)
    health: HealthState = Field(default_factory=HealthState)
    goals: dict[str, GoalState] = Field(default_factory=dict)
    relationships: dict[str, RelationshipState] = Field(default_factory=dict)
    habits: dict[str, HabitState] = Field(default_factory=dict)
    memories: list[MemoryTrace] = Field(default_factory=list)


class InitialCharacterState(SchemaModel):
    """配置文件中的冷启动状态。故意不允许提前塞入一个正在运行的 Action。"""

    spatial: SpatialState = Field(default_factory=SpatialState)
    body: BodyState = Field(default_factory=BodyState)
    cognition: CognitionState = Field(default_factory=CognitionState)
    affect: AffectState = Field(default_factory=AffectState)
    drives: DriveState = Field(default_factory=DriveState)


class BiologicalRhythm(SchemaModel):
    """长期生理节律参数。"""

    preferred_sleep_hour: float = Field(default=23.5, ge=0, lt=24)
    preferred_wake_hour: float = Field(default=7.5, ge=0, lt=24)
    sleep_pressure_awake_tau_hours: float = Field(default=16.0, gt=0)
    sleep_pressure_sleep_tau_hours: float = Field(default=4.0, gt=0)


class BehavioralProfile(SchemaModel):
    """长期行为先验。默认值中性，不依赖具体角色。"""

    social_reward: UnitScore = 0.5
    creative_reward: UnitScore = 0.5
    achievement_reward: UnitScore = 0.5
    novelty_reward: UnitScore = 0.5
    persistence: UnitScore = 0.5
    impulsivity: UnitScore = 0.5
    routine_preference: UnitScore = 0.5
    autonomy_preference: UnitScore = 0.5


class AffectBaseline(SchemaModel):
    valence: BipolarScore = 0
    arousal: Score = 35
    stress: Score = 20
    half_life_hours: float = Field(default=6.0, gt=0)


class HabitTuning(SchemaModel):
    learning_rate: float = Field(default=0.08, ge=0, le=1)
    half_life_days: float = Field(default=30.0, gt=0)
    max_weight: UnitScore = 0.45


class MemoryTuning(SchemaModel):
    max_records: int = Field(default=300, ge=10)
    half_life_days: float = Field(default=14.0, gt=0)


class RuntimeTuning(SchemaModel):
    decision_noise: float = Field(default=2.5, ge=0)
    switch_threshold: float = Field(default=10.0, ge=0)
    interrupt_threshold: float = Field(default=0.35, ge=0, le=1)
    goal_directed_base_weight: UnitScore = 0.7
    maximum_kernel_steps: int = Field(default=10000, ge=100)


class TravelLink(SchemaModel):
    to_place_id: str
    minutes: float = Field(gt=0)
    bidirectional: bool = True


class PlaceDefinition(SchemaModel):
    place_id: str
    name: str | None = None
    default_environment: EnvironmentState = Field(default_factory=EnvironmentState)
    links: list[TravelLink] = Field(default_factory=list)


class WorldConfig(SchemaModel):
    places: list[PlaceDefinition] = Field(default_factory=list)


class ScheduleBlock(SchemaModel):
    """每周重复日程。mode=hard 时是真正硬约束。"""

    name: str
    weekdays: list[int] = Field(default_factory=list)
    start: time
    end: time
    action_type: str
    place_id: str | None = None
    mode: Literal["hard", "soft"] = "soft"
    weight: UnitScore = 0.8


class LifeConfig(SchemaModel):
    timezone: str = "Asia/Tokyo"
    database_path: str = "life.db"
    # 可选的生活基地。设置后，夜间/疲劳时 Behavior 会把“回家”作为一个普通候选行为。
    home_place_id: str | None = None
    random_seed: int | None = None
    initial: InitialCharacterState = Field(default_factory=InitialCharacterState)
    rhythm: BiologicalRhythm = Field(default_factory=BiologicalRhythm)
    profile: BehavioralProfile = Field(default_factory=BehavioralProfile)
    affect_baseline: AffectBaseline = Field(default_factory=AffectBaseline)
    habit: HabitTuning = Field(default_factory=HabitTuning)
    memory: MemoryTuning = Field(default_factory=MemoryTuning)
    tuning: RuntimeTuning = Field(default_factory=RuntimeTuning)
    world: WorldConfig = Field(default_factory=WorldConfig)
    schedule: list[ScheduleBlock] = Field(default_factory=list)


class MeaningEvent(SchemaModel):
    """Appraisal 的结构化输出；LLM 以后只需要生成这一层，而不是改状态。"""

    type: Literal["meaning"] = "meaning"
    occurred_at: datetime
    name: str
    intensity: UnitScore = 0.5
    urgency: UnitScore = 0
    valence: float = Field(default=0.0, ge=-1, le=1)
    arousal: float = Field(default=0.0, ge=-1, le=1)
    stress: float = Field(default=0.0, ge=-1, le=1)
    emotion: str | None = None
    emotion_half_life_hours: float = Field(default=2.0, gt=0)
    target_action: str | None = None
    related_entity: str | None = None
    memory_salience: UnitScore = 0


class LocationChangedEvent(SchemaModel):
    type: Literal["location_changed"] = "location_changed"
    occurred_at: datetime
    place_id: str
    zone_id: str | None = None
    anchor_id: str | None = None
    position: Vec3 | None = None


class ForceActionEvent(SchemaModel):
    type: Literal["force_action"] = "force_action"
    occurred_at: datetime
    action_type: str
    duration_minutes: float | None = Field(default=None, gt=0)
    target: str | None = None


class WorldEnvironmentEvent(SchemaModel):
    type: Literal["world_environment"] = "world_environment"
    occurred_at: datetime
    place_id: str
    environment: EnvironmentState


class EntityPresenceEvent(SchemaModel):
    type: Literal["entity_presence"] = "entity_presence"
    occurred_at: datetime
    entity: WorldEntity
    present: bool = True


class AdapterAvailabilityEvent(SchemaModel):
    type: Literal["adapter_availability"] = "adapter_availability"
    occurred_at: datetime
    adapter: str
    available: bool


class GoalUpsertEvent(SchemaModel):
    type: Literal["goal_upsert"] = "goal_upsert"
    occurred_at: datetime
    goal: GoalState


class GoalProgressEvent(SchemaModel):
    type: Literal["goal_progress"] = "goal_progress"
    occurred_at: datetime
    goal_id: str
    delta: float


class RelationshipEvent(SchemaModel):
    type: Literal["relationship"] = "relationship"
    occurred_at: datetime
    target_id: str
    familiarity_delta: float = 0
    closeness_delta: float = 0
    trust_delta: float = 0
    comfort_delta: float = 0
    tension_delta: float = 0
    dependency_delta: float = 0


class HealthImpactEvent(SchemaModel):
    type: Literal["health_impact"] = "health_impact"
    occurred_at: datetime
    name: str
    severity: Score
    recovery_half_life_hours: float = Field(default=24.0, gt=0)
    pain_effect: Score = 0
    fatigue_effect: Score = 0
    energy_penalty: Score = 0


class MemoryEvent(SchemaModel):
    type: Literal["memory"] = "memory"
    occurred_at: datetime
    memory: MemoryTrace


LifeEvent = Annotated[
    MeaningEvent
    | LocationChangedEvent
    | ForceActionEvent
    | WorldEnvironmentEvent
    | EntityPresenceEvent
    | AdapterAvailabilityEvent
    | GoalUpsertEvent
    | GoalProgressEvent
    | RelationshipEvent
    | HealthImpactEvent
    | MemoryEvent,
    Field(discriminator="type"),
]


class JournalRecord(SchemaModel):
    occurred_at: datetime
    kind: str
    data: dict = Field(default_factory=dict)


class PerceptionFrame(SchemaModel):
    """从 WorldState + 角色位置即时生成，不持久化。"""

    environment: EnvironmentState
    nearby_entities: list[WorldEntity] = Field(default_factory=list)
    available_adapters: list[str] = Field(default_factory=list)


class DerivedState(SchemaModel):
    """由 Canonical State 随时计算，不写回数据库。"""

    sleepiness: Score
    thirst: Score
    health_score: Score
    physical_stamina: Score
    attention: Score
    mental_clarity: Score
    available_for_interruption: Score
    mood_label: str


class RuntimeView(SchemaModel):
    state: LifeState
    perception: PerceptionFrame
    derived: DerivedState


class AppraisalInput(SchemaModel):
    """规则型 Appraisal 的输入。

    这里已经是“结构化刺激”，不尝试理解自然语言本身。
    文本语义未来可由 LLM/规则解析器转换到这些维度。
    """

    occurred_at: datetime
    name: str
    relevance: UnitScore = 0.5
    goal_congruence: float = Field(default=0.0, ge=-1, le=1)
    controllability: UnitScore = 0.5
    novelty: UnitScore = 0.5
    social_evaluation: float = Field(default=0.0, ge=-1, le=1)
    threat: UnitScore = 0.0
    urgency: UnitScore = 0.0
    related_entity: str | None = None
    target_action: str | None = None
    memory_salience: UnitScore = 0.0
