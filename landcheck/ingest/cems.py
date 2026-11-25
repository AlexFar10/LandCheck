"""Ingest Copernicus EMS EMSR758 AOI03 flood products into a dataset folder (PRD Section 7.5).

Usage:
    python -m landcheck.ingest.cems --raw data/cems --out datasets/pilot-pechea/v1

Reads three pinned ZIP packages, checks their SHA-256, repairs invalid geometries, measures
areas in EPSG:32635 and writes manifest.json, coverage.geojson and layers/<layer_id>.geojson
in the exact shape that landcheck.api.dataset loads. Provenance (checksums, repair counts,
areas) goes to a separate report file, because the API loader rejects extra files.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import shapely
from shapely.geometry import mapping
from shapely.geometry.base import BaseGeometry
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

METHOD_VERSION = "cems-ingest-0.1"
DATASET_ID = "pilot-pechea"
DATASET_VERSION = "v1"
METRIC_CRS = "EPSG:32635"
SOURCE_NAME = "Copernicus EMS Rapid Mapping EMSR758"
SOURCE_URL = "https://mapping.emergency.copernicus.eu/activations/EMSR758"
ATTRIBUTION = "Copernicus Emergency Management Service (CEMS), EMSR758, AOI03"
GRID = 1e-6  # about 0.1 m; coordinates are snapped so output is stable across runs


class IngestError(Exception):
    """The raw data does not match what the pipeline expects. Never continue past this."""


@dataclass(frozen=True)
class LayerSpec:
    layer_id: str
    title: str
    package: str
    sha256: str
    size: int
    observation_date: str
    acquired_at: str
    sensor: str
    expected_features: int
    default_visible: bool


# Pins from PRD Section 7.3. Counts from PRD Section 7.2.
LAYERS = (
    LayerSpec(
        "flood_emsr758_aoi03_fep_v1",
        "Flood extent, first estimate (14 Sep 2024)",
        "EMSR758_AOI03_FEP_PRODUCT_v1.zip",
        "95e81d5839d3fd8b24ebb68651bc7f3b349168ac04847204a8e3dadc36df133b",
        2_222_132,
        "2024-09-14",
        "2024-09-14",
        "Sentinel-1",
        108,
        False,
    ),
    LayerSpec(
        "flood_emsr758_aoi03_del_v1",
        "Flood extent, delineation (15 Sep 2024)",
        "EMSR758_AOI03_DEL_PRODUCT_v1.zip",
        "8cb85940a59291147b11dbe9dfd5be75c37d37e1c061c1832a531cb543d7642e",
        5_301_056,
        "2024-09-15",
        "2024-09-15T15:59:00",
        "PAZ",
        131,
        True,
    ),
    LayerSpec(
        "flood_emsr758_aoi03_monit01_v1",
        "Flood extent, monitoring 1 (17 Sep 2024)",
        "EMSR758_AOI03_DEL_MONIT01_v1.zip",
        "c5f662293b7cfb977504bf84335c25218e65b4786e78baed4bd1444a3b6e1eb5",
        8_088_771,
        "2024-09-17",
        "2024-09-17T16:13:00",
        "COSMO-SkyMed Second Generation",
        237,
        False,
    ),
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_package(raw_dir: Path, spec: LayerSpec) -> Path:
    path = raw_dir / spec.package
    if not path.is_file():
        raise IngestError(f"missing package: {path}")
    if path.stat().st_size != spec.size:
        raise IngestError(f"{spec.package}: size {path.stat().st_size} != pinned {spec.size}")
    digest = sha256_file(path)
    if digest != spec.sha256:
        raise IngestError(f"{spec.package}: sha256 {digest} != pinned {spec.sha256}")
    return path


def read_source_layer(extract_dir: Path, kind: str) -> gpd.GeoDataFrame:
    """Read the one shapefile whose name contains `_<kind>_` (e.g. observedEventA)."""
    matches = sorted(extract_dir.rglob(f"*_{kind}_*.shp"))
    if len(matches) != 1:
        raise IngestError(f"expected exactly one {kind} shapefile, found {len(matches)}")
    gdf = gpd.read_file(matches[0])
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        raise IngestError(f"{matches[0].name}: CRS is {gdf.crs}, expected EPSG:4326")
    return gdf


def area_ha(geoms: gpd.GeoSeries) -> float:
    return float(geoms.to_crs(METRIC_CRS).area.sum() / 10_000)


def polygons_only(geom: BaseGeometry) -> BaseGeometry | None:
    """Keep only polygonal parts (make_valid can return lines or points as well)."""
    if geom is None or geom.is_empty:
        return None
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        return geom
    parts = [g for g in getattr(geom, "geoms", []) if g.geom_type in ("Polygon", "MultiPolygon")]
    if not parts:
        return None
    return unary_union(parts)


def clean(geom: BaseGeometry) -> BaseGeometry | None:
    """Snap to the grid, normalise ring order and orientation (RFC 7946: exterior CCW)."""
    geom = shapely.set_precision(geom, GRID)
    geom = polygons_only(geom)
    if geom is None or geom.is_empty:
        return None
    geom = shapely.normalize(geom)
    if geom.geom_type == "Polygon":
        return orient(geom, 1.0)
    return shapely.MultiPolygon([orient(p, 1.0) for p in geom.geoms])


def repair(gdf: gpd.GeoDataFrame) -> tuple[list[BaseGeometry], dict[str, Any]]:
    invalid = int((~gdf.geometry.is_valid).sum())
    before = area_ha(gdf.geometry)
    fixed = [clean(shapely.make_valid(g)) if not g.is_valid else clean(g) for g in gdf.geometry]
    dropped = sum(g is None for g in fixed)
    fixed = [g for g in fixed if g is not None]
    still_bad = sum(not g.is_valid for g in fixed)
    if still_bad:
        raise IngestError(f"{still_bad} geometries are still invalid after repair")
    after = area_ha(gpd.GeoSeries(fixed, crs="EPSG:4326"))
    return fixed, {
        "feature_count_source": len(gdf),
        "feature_count": len(fixed),
        "dropped_empty": dropped,
        "invalid_geometries_repaired": invalid,
        "area_ha_published_column": round(float(gdf["area"].sum()), 2),
        "area_ha_before_repair": round(before, 2),
        "area_ha_after_repair": round(after, 2),
    }


def feature_id(layer_id: str, geom: BaseGeometry) -> str:
    """Deterministic id from the layer id and the canonical geometry (PRD 7.5 rule 6)."""
    digest = hashlib.sha256(shapely.to_wkb(geom, output_dimension=2, byte_order=1)).hexdigest()
    return f"{layer_id}-{digest[:12]}"


def build_coverage(aoi: gpd.GeoDataFrame, footprint: gpd.GeoDataFrame) -> BaseGeometry:
    """Coverage = area of interest intersected with the image footprint (PRD 7.5 rule 5)."""
    a = unary_union([shapely.make_valid(g) for g in aoi.geometry])
    f = unary_union([shapely.make_valid(g) for g in footprint.geometry])
    cov = clean(a.intersection(f))
    if cov is None:
        raise IngestError("AOI and image footprint do not overlap")
    return cov


def geojson_geometry(geom: BaseGeometry) -> dict[str, Any]:
    return mapping(geom)


def dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"


def layer_meta(spec: LayerSpec) -> dict[str, Any]:
    return {
        "layer_id": spec.layer_id,
        "title": spec.title,
        "hazard_type": "flood_history",
        "default_visible": spec.default_visible,
        "observation_date": spec.observation_date,
        "sensor": spec.sensor,
        "source_name": SOURCE_NAME,
        "source_url": SOURCE_URL,
        "attribution": ATTRIBUTION,
        "meaning": (
            "Area mapped as flooded from satellite radar after the 13-14 September 2024 flood "
            "near Pechea, Galati. It shows where water was seen on the observation date."
        ),
        "limitations": [
            "Shows one moment only. Water may have been present earlier or later.",
            "Outside the satellite image footprint there is no information, which is not the same as safe.",
            "Radar can miss shallow water, water under vegetation and water between buildings.",
            "It is a record of a past event, not a forecast of future flooding.",
        ],
        "legend": [{"label": "Mapped as flooded", "color": "#1d4ed8"}],
    }


def git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        )
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def run(raw_dir: Path, out_dir: Path, report_path: Path | None = None) -> dict[str, Any]:
    if out_dir.exists():
        raise IngestError(f"{out_dir} already exists. Dataset versions are immutable: use a new version.")

    # Verify every package first, so nothing is written if any checksum is wrong.
    packages = {spec.layer_id: verify_package(raw_dir, spec) for spec in LAYERS}

    zones_by_layer: dict[str, list[dict[str, Any]]] = {}
    coverage_features: list[dict[str, Any]] = []
    report_layers: list[dict[str, Any]] = []

    for spec in LAYERS:
        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(packages[spec.layer_id]) as z:
                z.extractall(tmp)
            tmp_dir = Path(tmp)
            events = read_source_layer(tmp_dir, "observedEventA")
            aoi = read_source_layer(tmp_dir, "areaOfInterestA")
            footprint = read_source_layer(tmp_dir, "imageFootprintA")

        if len(events) != spec.expected_features:
            raise IngestError(
                f"{spec.layer_id}: {len(events)} polygons, expected {spec.expected_features}"
            )
        geoms, stats = repair(events)
        coverage = build_coverage(aoi, footprint)

        # Same canonical geometry always gets the same id, and the file order follows the id.
        keyed = sorted(((feature_id(spec.layer_id, g), g) for g in geoms), key=lambda t: t[0])
        ids = [k for k, _ in keyed]
        if len(set(ids)) != len(ids):
            raise IngestError(f"{spec.layer_id}: duplicate feature ids (identical geometries)")

        props_base = {
            "layer_id": spec.layer_id,
            "hazard_type": "flood_history",
            "classification": "Mapped as flooded",
            "measurement": None,
            "unit": None,
            "observation_date": spec.observation_date,
            "source_name": SOURCE_NAME,
            "source_url": SOURCE_URL,
            "coverage_status": "observed",
            "method_version": METHOD_VERSION,
            "dataset_version": DATASET_VERSION,
            "sample": False,
        }
        zones_by_layer[spec.layer_id] = [
            {
                "type": "Feature",
                "id": fid,
                "geometry": geojson_geometry(g),
                "properties": dict(props_base),
            }
            for fid, g in keyed
        ]
        coverage_features.append(
            {
                "type": "Feature",
                "id": spec.layer_id,
                "geometry": geojson_geometry(coverage),
                "properties": {"layer_id": spec.layer_id},
            }
        )
        report_layers.append(
            {
                "layer_id": spec.layer_id,
                "observation_date": spec.observation_date,
                "acquired_at_as_published": spec.acquired_at,
                "sensor": spec.sensor,
                "source_package": spec.package,
                "source_package_sha256": spec.sha256,
                "source_layer": "observedEventA",
                "coverage_area_ha": round(area_ha(gpd.GeoSeries([coverage], crs="EPSG:4326")), 2),
                **stats,
            }
        )

    # Write only after everything has been checked.
    (out_dir / "layers").mkdir(parents=True)
    manifest = {
        "dataset_id": DATASET_ID,
        "dataset_version": DATASET_VERSION,
        "method_version": METHOD_VERSION,
        "sample": False,
        "layers": [layer_meta(s) for s in LAYERS],
    }
    (out_dir / "manifest.json").write_text(dumps(manifest), encoding="utf-8")
    (out_dir / "coverage.geojson").write_text(
        dumps({"type": "FeatureCollection", "features": coverage_features}), encoding="utf-8"
    )
    for entry in report_layers:
        lid = entry["layer_id"]
        path = out_dir / "layers" / f"{lid}.geojson"
        path.write_text(
            dumps({"type": "FeatureCollection", "features": zones_by_layer[lid]}), encoding="utf-8"
        )
        entry["output_sha256"] = sha256_file(path)

    report = {
        "dataset_id": DATASET_ID,
        "dataset_version": DATASET_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "code_commit": git_commit(),
        "method_version": METHOD_VERSION,
        "pilot_crs_metric": METRIC_CRS,
        "manifest_sha256": sha256_file(out_dir / "manifest.json"),
        "coverage_sha256": sha256_file(out_dir / "coverage.geojson"),
        "layers": report_layers,
    }
    report_path = report_path or out_dir.with_name(out_dir.name + ".ingest.json")
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--raw", type=Path, required=True, help="folder with the three CEMS ZIPs")
    p.add_argument("--out", type=Path, required=True, help="new dataset folder, e.g. datasets/pilot-pechea/v1")
    p.add_argument("--report", type=Path, help="where to write the ingest report (default: next to --out)")
    args = p.parse_args(argv)
    try:
        report = run(args.raw, args.out, args.report)
    except IngestError as e:
        print(f"INGEST FAILED: {e}", file=sys.stderr)
        return 1
    for layer in report["layers"]:
        print(
            f"{layer['layer_id']}: {layer['feature_count']} polygons, "
            f"{layer['invalid_geometries_repaired']} repaired, "
            f"{layer['area_ha_before_repair']} -> {layer['area_ha_after_repair']} ha"
        )
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
