"""Dataset and API models (PRD Sections 7.4 and 12). Loading validates every file strictly."""

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, HttpUrl, model_validator

HazardType = Literal["flood_history", "flood_hazard_zone", "ground_stability", "land_use"]
# Per-feature coverage semantics, PRD Section 8.2.
CoverageStatus = Literal["observed", "not_observed", "no_coverage", "not_assessed"]
# Per-query coverage, PRD Section 12.5.
QueryCoverage = Literal["full", "partial", "none"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LegendEntry(Strict):
    label: str
    color: str


class LayerMeta(Strict):
    """One layer entry in manifest.json."""

    layer_id: str
    title: str
    hazard_type: HazardType
    default_visible: bool
    observation_date: date
    sensor: str | None
    source_name: str
    source_url: HttpUrl
    attribution: str
    meaning: str
    limitations: list[str]
    legend: list[LegendEntry]


class Manifest(Strict):
    dataset_id: str
    dataset_version: str
    method_version: str
    # True for fixtures. Every response carries it so sample data is never shown as real.
    sample: bool
    layers: list[LayerMeta]


class ZoneProperties(Strict):
    """Section 12.2 zone fields, plus layer_id, dataset_version and sample."""

    layer_id: str
    hazard_type: HazardType
    classification: str | None
    measurement: float | None
    unit: str | None
    observation_date: date
    source_name: str
    source_url: HttpUrl
    coverage_status: CoverageStatus
    method_version: str
    dataset_version: str
    sample: bool

    @model_validator(mode="after")
    def _unit_with_measurement(self) -> "ZoneProperties":
        if self.measurement is not None and not self.unit:
            raise ValueError("unit is required when measurement exists")
        return self


class Health(BaseModel):
    status: Literal["ok", "error"]
    version: str
    git_commit: str
    dataset_id: str | None
    dataset_version: str | None
    sample: bool | None


class Layer(BaseModel):
    """Section 12.4 layer object, plus sample."""

    id: str
    title: str
    hazard_type: HazardType
    default_visible: bool
    observation_date: date
    sensor: str | None
    source_name: str
    source_url: str
    attribution: str
    meaning: str
    limitations: list[str]
    legend: list[LegendEntry]
    feature_count: int
    coverage: dict[str, Any]
    method_version: str
    dataset_version: str
    sample: bool


class LayersResponse(BaseModel):
    layers: list[Layer]
