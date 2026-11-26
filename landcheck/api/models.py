"""Dataset and API models (PRD Sections 7.4 and 12). Loading validates every file strictly.

The shared layer format these models define is documented in docs/LAYER_FORMAT.md.
"""

from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

HazardType = Literal["flood_history", "flood_hazard_zone", "ground_stability", "land_use"]
# Coverage semantics, PRD Section 8.2. A stored zone is only ever observed or not_observed:
# no_coverage (outside the layer coverage) and not_assessed (layer missing or failed) are
# derived by the API, never written as features.
CoverageStatus = Literal["observed", "not_observed", "no_coverage", "not_assessed"]
StoredCoverageStatus = Literal["observed", "not_observed"]
# Per-query coverage, PRD Section 12.5.
QueryCoverage = Literal["full", "partial", "none"]

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LegendEntry(Strict):
    label: str
    color: str


class LayerMeta(Strict):
    """One layer entry in manifest.json."""

    # Served by GET /api/v1/layers (PRD 12.4).
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
    # Overrides the manifest's method_version, for datasets that mix modules.
    method_version: str | None = None
    # Grid layers name their grid (config/grid.yaml). Null for source polygon layers.
    grid_id: str | None = None

    # Integrity, checked on load (PRD 7.5 step 8, 12.7 checksum failure).
    feature_count: int = Field(ge=0)
    output_sha256: Sha256

    # Provenance from PRD 7.4. Not served by the API. The source_* fields describe a
    # downloaded package, so layers built from other inputs leave them null.
    acquired_at_as_published: str | None = None
    source_package: str | None = None
    source_package_sha256: Sha256 | None = None
    source_layer: str | None = None
    invalid_geometries_repaired: int | None = Field(default=None, ge=0)
    area_ha_before_repair: float | None = None
    area_ha_after_repair: float | None = None
    # Anything else an ingest needs to record (input checksums, counts, parameters).
    provenance: dict[str, Any] = Field(default_factory=dict)


class Manifest(Strict):
    dataset_id: str
    dataset_version: str
    # Default for every layer that does not set its own.
    method_version: str
    # True for fixtures. Every response carries it so sample data is never shown as real.
    sample: bool
    # PRD 7.4 provenance.
    created_at: datetime
    code_commit: str
    pilot_crs_metric: str
    coverage_sha256: Sha256
    layers: list[LayerMeta]

    def method_version_of(self, layer: LayerMeta) -> str:
        return layer.method_version or self.method_version


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
    coverage_status: StoredCoverageStatus
    method_version: str
    dataset_version: str
    sample: bool

    @model_validator(mode="after")
    def _value_rules(self) -> "ZoneProperties":
        if self.measurement is not None and not self.unit:
            raise ValueError("unit is required when measurement exists")
        if self.measurement is None and self.unit is not None:
            raise ValueError("unit without a measurement")
        if self.coverage_status == "not_observed" and (
            self.classification is not None or self.measurement is not None
        ):
            # Section 8.2: "no flooding mapped" must never carry a value that reads as a result.
            raise ValueError("not_observed zones carry no classification or measurement")
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
