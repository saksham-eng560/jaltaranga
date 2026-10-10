"""Pydantic v2 models for every schema in SHARED_RESOURCES §5, with the §11 amendments.

These models are the single source; JSON Schemas are exported with
``python -m jt_shared.export_schemas``. Models we *produce* forbid unknown fields so drift
fails loudly; models we only *consume* ignore extra fields so a teammate's additive change
does not break a reader.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, PlainSerializer, model_validator

from .timeutil import iso, parse_ts


def _aware(v: Any) -> datetime:
    return parse_ts(v)


Ts = Annotated[
    datetime,
    AfterValidator(_aware),
    PlainSerializer(iso, return_type=str, when_used="always"),
    Field(json_schema_extra={"format": "date-time", "pattern": r"\+05:30$"}),
]
LonLat = Annotated[list[float], Field(min_length=2, max_length=2)]


class Produced(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Consumed(BaseModel):
    model_config = ConfigDict(extra="ignore")


# --- §5.1 GaugeReading (+ §11.3) -------------------------------------------------------------
class GaugeReading(Consumed):
    station_id: str
    ts: Ts
    level_m: float | None = None
    discharge_cumecs: float | None = None
    source: Literal["cwc", "floodhub", "digitized", "synthetic", "glofas", "news"]
    qc_flag: Literal["ok", "imputed", "suspect"] = "ok"
    source_ref: str | None = None
    note: str | None = None

    @model_validator(mode="after")
    def _one_value(self) -> GaugeReading:
        if self.level_m is None and self.discharge_cumecs is None:
            raise ValueError("at least one of level_m / discharge_cumecs must be set")
        return self


# --- §5.2 ForecastNode -----------------------------------------------------------------------
class ForecastNode(Consumed):
    scenario_id: str
    issued_at: Ts
    station_id: str
    horizon_h: int
    valid_at: Ts
    level_m: float
    lo_m: float
    hi_m: float
    coverage: float = 0.8
    model: str

    @model_validator(mode="after")
    def _band(self) -> ForecastNode:
        if not (self.lo_m <= self.level_m <= self.hi_m):
            raise ValueError("expected lo_m <= level_m <= hi_m")
        return self


# --- §5.3 FloodSurface index -----------------------------------------------------------------
class FloodIndexEntry(Consumed):
    valid_at: Ts
    tif: str
    geojson: str
    level_m_ref: float


# --- §5.4 RoadSegmentStatus ------------------------------------------------------------------
class RoadSegmentStatus(Produced):
    edge_id: str = Field(pattern=r"^osm:\d+:\d+:\d+$")
    status: Literal["green", "amber", "red"]
    depth_m: float = Field(ge=0)
    cutoff_at: Ts | None = None
    reason: Literal["depth>0.3m", "forecast_cutoff<2h", "field_report"] | None = None


# --- §5.5 Colony, Shelter (+ §11.3 free_beds) --------------------------------------------------
class Vulnerable(Consumed):
    elderly: int = 0
    disabled: int = 0
    children_u5: int = 0
    pregnant: int = 0


class Contact(Consumed):
    role: str
    name: str
    channel: Literal["email", "sms"]
    address: str


class Colony(Consumed):
    colony_id: str
    name_en: str
    name_hi: str
    centroid: LonLat
    population_est: int = Field(ge=0)
    ground_elev_m: float | None = None
    vulnerable: Vulnerable = Field(default_factory=Vulnerable)
    contacts: list[Contact] = Field(default_factory=list)


class Shelter(Consumed):
    shelter_id: str
    name_en: str
    name_hi: str
    location: LonLat
    ground_elev_m: float | None = None
    capacity: int = Field(ge=0)
    occupied: int = Field(ge=0)
    free_beds: int | None = None
    type: Literal["school", "community_hall", "relief_camp", "medical"]
    updated_at: Ts | None = None

    @model_validator(mode="after")
    def _beds(self) -> Shelter:
        if self.free_beds is None:
            self.free_beds = max(0, self.capacity - self.occupied)
        return self


# --- §5.6 EvacuationPlan (+ §11.3 avoid.edge_ids, §11.8-3 time-to-water) -----------------------
class RouteOption(Produced):
    shelter_id: str
    route_geojson: dict[str, Any]
    distance_m: float = Field(ge=0)
    walk_min: float = Field(ge=0)
    via_names_en: list[str] = Field(default_factory=list)
    via_names_hi: list[str] = Field(default_factory=list)
    max_depth_m: float = Field(ge=0)


class AvoidEntry(Produced):
    name_en: str
    name_hi: str
    cutoff_at: Ts
    edge_ids: list[str] = Field(default_factory=list)


class PlanExt(Produced):
    """Optional additive block (Saksham plan §11 ask (b)); null when unused."""

    walk_speed_kmh: float | None = None
    transport_needed: bool = False
    replanned_due_to: str | None = None
    origin_offset_m: float | None = None
    assigned_people: int | None = None
    demand_people: int | None = None


class EvacuationPlan(Produced):
    scenario_id: str
    colony_id: str
    computed_at: Ts
    t_submersion: Ts
    t_submersion_earliest: Ts | None = None
    t_submersion_latest: Ts | None = None
    lead_time_h: float
    primary: RouteOption
    backup: RouteOption | None = None
    avoid: list[AvoidEntry] = Field(default_factory=list)
    priority: float = Field(ge=0, le=1)
    ext: PlanExt | None = None


class UnreachableEntry(Produced):
    colony_id: str
    reason: Literal["already_wet", "no_dry_origin", "no_feasible_route", "no_shelter_capacity"]
    population: int


class TrapStep(Produced):
    valid_at: Ts
    trapped_population: int
    colonies: list[str]
    roads: list[str]


class TrapSummary(Produced):
    scenario_id: str
    steps: list[TrapStep]
    max_trapped_population: int
    max_at: Ts | None = None


# --- §5.7 DispatchCard -------------------------------------------------------------------------
AlertType = Literal["URGENT_EVACUATION_DISPATCH", "PREPARE", "ALL_CLEAR", "SHELTER_IN_PLACE"]
CheckName = Literal["numbers_match", "names_match", "slots_used", "phones_whitelist", "length", "script"]


class PlanRef(Produced):
    scenario_id: str
    colony_id: str
    computed_at: Ts


class Validation(Produced):
    passed: bool
    checks: list[CheckName]
    fallback_used: bool
    failed_checks: list[CheckName] = Field(default_factory=list)
    fallback_fields: list[Literal["message_hi", "message_en", "sms_hi"]] = Field(default_factory=list)
    source: Literal["bedrock", "template", "cache"] = "template"


class DispatchCard(Produced):
    dispatch_id: str
    plan_ref: PlanRef
    alert_type: AlertType
    message_hi: str = Field(max_length=600)
    message_en: str = Field(max_length=600)
    sms_hi: str = Field(max_length=160)
    audio_url_hi: str | None = None
    validation: Validation
    status: Literal["draft", "approved", "sent", "acknowledged"]
    approved_by: str | None = None
    ts: Ts


# --- §5.8 FieldReport (+ §11.4 POST /reports response) -----------------------------------------
class FieldReport(Produced):
    report_id: str
    ts: Ts
    location: LonLat
    kind: Literal["water_depth", "road_blocked", "shelter_full", "sos"]
    depth_cm: float | None = None
    photo_key: str | None = None
    reporter_id: str
    trust: float = Field(ge=0, le=1)
    verified: bool = False


class PresignedPost(Produced):
    url: str
    fields: dict[str, str]


class ReportPostResponse(Produced):
    report: FieldReport
    upload: PresignedPost | None = None


# --- §11.2 colony thresholds, §11.3 manifest ---------------------------------------------------
class ColonyThreshold(Consumed):
    colony_id: str
    wet_at_level_m: float | None
    cutoff_at_level_m: float | None
    buffer_m: float = 150


class ManifestEvent(Consumed):
    kind: str
    ts: Ts
    level_m: float | None = None
    ts_verified: bool = True


class Manifest(Consumed):
    scenario_id: str
    mode: Literal["replay", "live"] = "replay"
    title_en: str | None = None
    title_hi: str | None = None
    start: Ts
    end: Ts
    step_min: int = 60
    valid_at: list[Ts]
    issued_at: list[Ts] = Field(default_factory=list)
    default_at: Ts | None = None
    ref_station: str = "DELHI_RLY_BRIDGE"
    thresholds: dict[str, float] = Field(default_factory=dict)
    events: list[ManifestEvent] = Field(default_factory=list)
    artefacts: dict[str, Literal["real", "fixture", "missing"]] = Field(default_factory=dict)
    context: dict[str, Any] | None = None
    sources: list[dict[str, Any]] = Field(default_factory=list)
    built_at: Ts | None = None
    git_sha: str | None = None
    data_version: str | None = None


class ApiError(Produced):
    class Body(Produced):
        code: str
        message: str

    error: Body


ALL_MODELS: dict[str, type[BaseModel]] = {
    "gauge_reading": GaugeReading,
    "forecast_node": ForecastNode,
    "flood_index_entry": FloodIndexEntry,
    "road_segment_status": RoadSegmentStatus,
    "colony": Colony,
    "shelter": Shelter,
    "evacuation_plan": EvacuationPlan,
    "unreachable_entry": UnreachableEntry,
    "trap_summary": TrapSummary,
    "dispatch_card": DispatchCard,
    "field_report": FieldReport,
    "report_post_response": ReportPostResponse,
    "colony_threshold": ColonyThreshold,
    "manifest": Manifest,
    "api_error": ApiError,
}
