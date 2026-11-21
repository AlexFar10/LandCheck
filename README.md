# Land Check: pipeline skeleton

The shared core is implemented and tested. Each risk module is a stub that sets out its interface, data sources and steps, for its owner to build.

```
landcheck/
├── config/thresholds.yaml      # all thresholds, versioned (placeholders for now)
├── landcheck/
│   ├── core/                   # OWNER: ______  (everyone uses it, one person maintains it)
│   │   ├── parcel.py           # polygon -> Parcel (UTM zone, buffer, bbox)
│   │   ├── s2.py               # Sentinel-2: search, load, offset fix, SCL mask, indices
│   │   ├── output.py           # ModuleResult: the shared result format
│   │   └── config.py           # reads thresholds.yaml
│   ├── modules/
│   │   ├── flood.py            # OWNER: ______  flood_history, flood_susceptibility
│   │   ├── ground.py           # OWNER: ______  ground_stability (EGMS)
│   │   └── landuse.py          # OWNER: ______  land_use (Sentinel-2 NDVI)
│   └── pipeline.py             # runs all modules on one parcel, in parallel
└── tests/test_core.py
```

## The contract

Each module exposes exactly this:

```python
RISKS = ("ground_stability",)                 # names of the results it returns
def run(parcel: Parcel) -> list[ModuleResult]: ...
```

`Parcel` gives you: `geom_wgs84`, `geom_utm`, `area_utm` (parcel + buffer), `area_wgs84`, `bbox_wgs84`, `epsg`.

`ModuleResult` has these fields: `risk, level (Low/Medium/High/Unknown), value, unit, confidence, summary, sources, date_range, method_version, details`.

## Rules everyone follows

1. **Coordinates:** store in WGS84 as (lon, lat), measure in the parcel's UTM zone. Never hard-code a zone: Romania has zones 34 and 35.
2. **Provenance:** every result lists the scene or dataset IDs and dates it used.
3. **No data means `Unknown`**, never `Low`. Use `no_coverage(...)`.
4. **Fail loudly:** no `fail_on_error=False`, no silent fills, no `ffill`.
5. **Thresholds go in `config/thresholds.yaml`**, not in code.
6. **Validation:** hold out whole basins, regions or years. Never split pixels randomly.
7. **Changes to `core/`** go through its owner (PR review).

## Run

```bash
pip install -e ".[dev]"
pytest                       # core tests
python -m landcheck.pipeline # demo parcel: all modules return "Unknown" until built
```

## Open questions

- Do EOCube's COGs carry the +1000 offset in `raster:bands`? `s2.offset_for_item` handles both cases. Confirm on one post-2022 item.
- Do EOCube's terms allow commercial use?
- Sentinel-1 GRD isn't on EOCube, so the flood module needs Copernicus Data Space.
- What cadastre access (ANCPI/eTerra) do we have for parcel input?
