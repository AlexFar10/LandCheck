"""The shared result format. Every module returns a list of ModuleResult.

Scoring and the report only read this format, so modules can change
their internals freely as long as they return it.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Literal

Level = Literal["Low", "Medium", "High", "Unknown"]
Confidence = Literal["Low", "Medium", "High"]


@dataclass
class Source:
    """One piece of data a result is based on ("based on what?")."""
    collection: str                 # e.g. "sentinel-2-l2a", "egms-ortho", "jrc-gsw-occurrence"
    item_id: str | None = None      # STAC item / scene ID, or dataset version
    acquired: date | None = None


@dataclass
class ModuleResult:
    risk: str                       # e.g. "flood_history", "ground_stability", "land_use"
    level: Level                    # "Unknown" when there is no data, never a guess
    value: float | None             # main number, e.g. mm/year, % of time flooded
    unit: str | None
    confidence: Confidence
    summary: str                    # one plain sentence the report can use
    sources: list[Source] = field(default_factory=list)
    date_range: tuple[date, date] | None = None
    method_version: str = "0.1"
    details: dict = field(default_factory=dict)   # module-specific extras

    def to_dict(self) -> dict:
        d = asdict(self)
        # JSON-friendly dates
        if self.date_range:
            d["date_range"] = [x.isoformat() for x in self.date_range]
        for s in d["sources"]:
            if s["acquired"]:
                s["acquired"] = s["acquired"].isoformat()
        return d


def no_coverage(risk: str, reason: str) -> ModuleResult:
    """Use when there is no data for the parcel. The report says 'no coverage', not 'safe'."""
    return ModuleResult(risk=risk, level="Unknown", value=None, unit=None,
                        confidence="Low", summary=f"No coverage: {reason}")
