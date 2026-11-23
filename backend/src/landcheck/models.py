"""API models. RiskResult mirrors contracts/result.schema.json (requirements section 6.1)."""

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class Risk(StrEnum):
    FLOOD_HISTORY = "flood_history"
    FLOOD_SUSCEPTIBILITY = "flood_susceptibility"
    GROUND_STABILITY = "ground_stability"
    LAND_USE_HISTORY = "land_use_history"


class Level(StrEnum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    UNKNOWN = "Unknown"


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    url: str | None = None


class DateRange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: date
    end: date

    @model_validator(mode="after")
    def _start_before_end(self) -> "DateRange":
        if self.start > self.end:
            raise ValueError("date_range.start is after date_range.end")
        return self


class RiskResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk: Risk
    level: Level
    value: float | None
    unit: str
    confidence: float | None
    summary: str
    sources: list[Source]
    date_range: DateRange

    @model_validator(mode="after")
    def _unknown_means_no_value(self) -> "RiskResult":
        # No data means Unknown, never Low: value/confidence are null exactly when level is Unknown.
        if self.level is Level.UNKNOWN:
            if self.value is not None or self.confidence is not None:
                raise ValueError("level Unknown requires value and confidence to be null")
        elif self.value is None or self.confidence is None:
            raise ValueError(f"level {self.level} requires a value and a confidence")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        if not self.sources:
            raise ValueError("sources must not be empty")
        return self


Position = list[float]


class PolygonGeometry(BaseModel):
    """A GeoJSON Polygon geometry (RFC 7946), lon/lat in WGS84."""

    type: Literal["Polygon"]
    coordinates: list[list[Position]]

    @field_validator("coordinates")
    @classmethod
    def _valid_rings(cls, rings: list[list[Position]]) -> list[list[Position]]:
        if not rings:
            raise ValueError("polygon needs at least one ring")
        for ring in rings:
            if len(ring) < 4:
                raise ValueError("each ring needs at least 4 positions")
            if ring[0] != ring[-1]:
                raise ValueError("each ring must be closed (first position == last position)")
            for position in ring:
                if len(position) not in (2, 3):
                    raise ValueError("each position must be [lon, lat] or [lon, lat, alt]")
                lon, lat = position[0], position[1]
                if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                    raise ValueError(f"position out of range: {position}")
        return rings


class AnalyzeResponse(BaseModel):
    results: list[RiskResult]
