"""Flood module. Owner: ______

Returns two results:
  "flood_history"        - has this parcel been under water, how often, how long
  "flood_susceptibility" - how likely, even if it never flooded (LightGBM)

Data
- Sentinel-1 GRD (radar, sees through clouds): water = dark backscatter (VV in dB)
- JRC Global Surface Water occurrence: permanent water to EXCLUDE (rivers, lakes, ponds)
- Copernicus DEM GLO-30: HAND (height above nearest drainage), slope
- ANAR flood hazard maps (official, EU Floods Directive): the legal reference
- Optional: Copernicus GFM / EMS rapid mapping as observed history and ground truth
- Optional: Sentinel-2 MNDWI via core.s2 for before/after report images only

Steps for flood_history
1. Search S1 GRD over parcel.area_wgs84 (Copernicus Data Space; not on EOCube).
2. Calibrate -> dB, speckle filter, terrain-flatten/shadow-mask with the DEM.
3. Water per date: VV_dB < threshold (Otsu per scene, or fixed from config).
4. Exclude: JRC occurrence > X% (permanent water), slope > Y deg, high HAND, urban.
5. Per parcel: % of observations flooded, longest consecutive run (water persistence).
6. Record every S1 scene ID used in sources.

Validation cases: Covasna (May 2025), Galați (13-14 Sept 2024).
Never split pixels randomly: hold out whole basins or years.
"""
from landcheck.core import ModuleResult, Parcel

RISKS = ("flood_history", "flood_susceptibility")


def run(parcel: Parcel) -> list[ModuleResult]:
    raise NotImplementedError("flood module not built yet")
