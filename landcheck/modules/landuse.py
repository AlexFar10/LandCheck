"""Land-use history module. Owner: ______

Returns one result: "land_use" (class per year + plain-language history).

Data
- Sentinel-2 L2A via landcheck.core.s2 (search, load, to_reflectance, select_clear, ndvi)
- ESA WorldCover / CORINE Land Cover for context and sanity checks
- LUCAS survey points as training labels for the classifier

Steps
1. items = s2.search(parcel, "2017-01-01", today); ds = s2.load(items, parcel,
   ["red", "nir", "scl"]); ds = s2.to_reflectance(ds, s2.offsets_by_date(items));
   ds = s2.select_clear(ds)
2. NDVI per date, averaged over parcel pixels only (not the buffer).
3. Per year: median, peak, seasonal amplitude. Gaps stay gaps (no ffill).
4. Classify each year: forest/orchard (stable high), arable (strong seasonal cycle),
   built/bare (persistently low), cleared (sudden lasting drop). Rules first,
   then LightGBM trained on LUCAS.
5. Summary like "Used as cropland 2017-2021; cleared in 2022; bare since."
6. sources = s2.sources_from_items(items)

Closest to the course notebook: start here.
"""
from landcheck.core import ModuleResult, Parcel

RISKS = ("land_use",)


def run(parcel: Parcel) -> list[ModuleResult]:
    raise NotImplementedError("land-use module not built yet")
