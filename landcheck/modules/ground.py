"""Ground stability module. Owner: ______

Returns one result: "ground_stability" (vertical velocity in mm/year, trend).

Data
- EGMS Ortho (Level 3, 100 m grid): vertical + east-west velocity, time series.
  Easiest start. Download needs an EU Login; precompute for the pilot county.
- EGMS Basic/Calibrated (point clouds) later, for building-level detail.
- Copernicus DEM slope: is movement on a slope (landslide) or flat ground (subsidence)?

Steps
1. Points (or grid cells) within parcel.area_utm.
2. If none -> core.no_coverage("ground_stability", "no EGMS points within N m").
   Report "no coverage", NEVER "stable". (Common on fields/forest.)
3. Median vertical velocity; robust trend; acceleration in recent years.
4. Level from config thresholds (e.g. subsidence faster than ~5 mm/yr -> High).
5. Confidence from point count and how consistent neighbouring points are
   (the colleague's warning: neighbours can disagree).
6. sources: EGMS product + release (e.g. 2020-2024), point IDs.
"""
from landcheck.core import ModuleResult, Parcel

RISKS = ("ground_stability",)


def run(parcel: Parcel) -> list[ModuleResult]:
    raise NotImplementedError("ground module not built yet")
