"""Cut the EGMS Ortho (Level 3) tiles down to the pilot zone (PRD Sections 7.1 and 8).

Usage:
    python -m landcheck.ingest.egms --raw data/egms \
        --coverage datasets/pilot-pechea/v1/coverage.geojson \
        --out datasets/pilot-pechea/ground/egms_ortho_pechea_2020_2025.csv

Input: the downloaded EGMS_L3_<tile>_100km_U_* (vertical) and _E_* (east-west) folders. Each CSV has
one row per radar point (EPSG:3035 easting and northing, mean velocity in mm/year, time series).
Output: one small CSV with the points inside the pilot zone (the CEMS coverage plus a buffer),
vertical and east-west joined by point id, with WGS84 coordinates. The time series is dropped.
Also writes <out>.ingest.json: input checksums, counts, and a cross-check against the area averages
copied by hand from the EGMS Explorer (egms_pechea_*.txt).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import shapely
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import unary_union

DATASET_ID = "egms-ortho-l3-pechea"
SRC_CRS = "EPSG:3035"
KEEP = ["height_ortho", "mean_velocity", "mean_velocity_std", "acceleration", "acceleration_std"]
OUT_COLUMNS = (["pid", "lon", "lat", "easting", "northing", "height_ortho_m"]
               + ["up_mm_yr", "up_std", "up_acc", "up_acc_std"]
               + ["ew_mm_yr", "ew_std", "ew_acc", "ew_acc_std"])
TILE = re.compile(r"EGMS_L3_(?P<tile>E\d+N\d+)_100km_(?P<comp>[UE])_(?P<period>\d{4}_\d{4})_\d+")


class IngestError(Exception):
    """The raw data does not match what the pipeline expects. Never continue past this."""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_tiles(raw: Path) -> dict[str, dict[str, Path]]:
    """{tile: {'U': csv, 'E': csv}} from the folders the EGMS download unpacks."""
    tiles: dict[str, dict[str, Path]] = {}
    for csv_path in sorted(raw.glob("EGMS_L3_*/*.csv")):
        m = TILE.fullmatch(csv_path.stem)
        if m:
            tiles.setdefault(m["tile"], {})[m["comp"]] = csv_path
    if not tiles:
        raise IngestError(f"no EGMS_L3_*/*.csv files under {raw}")
    for tile, parts in tiles.items():
        if set(parts) != {"U", "E"}:
            raise IngestError(f"tile {tile}: need both vertical (U) and east-west (E), have {sorted(parts)}")
    return tiles


def zone_bounds(coverage_geojson: Path, buffer_m: float) -> tuple[float, float, float, float]:
    """Bounding box (EPSG:3035 metres) of the coverage plus a buffer."""
    fc = json.loads(coverage_geojson.read_text(encoding="utf-8"))
    geom = unary_union([shape(f["geometry"]) for f in fc["features"]])
    t = Transformer.from_crs("EPSG:4326", SRC_CRS, always_xy=True)
    g = shapely.transform(geom, lambda x, y: t.transform(x, y), interleaved=False)
    return g.buffer(buffer_m).bounds


def read_points(path: Path, box: tuple[float, float, float, float]) -> dict[str, dict[str, float]]:
    """Rows inside `box`, keyed by point id, with only the columns we keep."""
    xmin, ymin, xmax, ymax = box
    out: dict[str, dict[str, float]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        idx = {name: i for i, name in enumerate(header)}
        missing = [c for c in ["pid", "easting", "northing", *KEEP] if c not in idx]
        if missing:
            raise IngestError(f"{path.name}: missing columns {missing}")
        ix, iy, ip = idx["easting"], idx["northing"], idx["pid"]
        for row in reader:
            x, y = float(row[ix]), float(row[iy])
            if xmin <= x <= xmax and ymin <= y <= ymax:
                rec = {"easting": x, "northing": y}
                rec.update({k: float(row[idx[k]]) for k in KEEP})
                out[row[ip]] = rec
    return out


def build_rows(tiles: dict[str, dict[str, Path]], box: tuple[float, float, float, float]):
    t = Transformer.from_crs(SRC_CRS, "EPSG:4326", always_xy=True)
    rows: dict[str, list[Any]] = {}
    per_tile: dict[str, dict[str, int]] = {}
    for tile, parts in sorted(tiles.items()):
        up = read_points(parts["U"], box)
        ew = read_points(parts["E"], box)
        per_tile[tile] = {"vertical_points": len(up), "east_west_points": len(ew),
                          "without_east_west": sum(1 for p in up if p not in ew)}
        for pid, u in up.items():
            if pid in rows:  # tiles do not overlap; a repeated id would be a data error
                raise IngestError(f"point id {pid} appears in more than one tile")
            lon, lat = t.transform(u["easting"], u["northing"])
            e = ew.get(pid)
            rows[pid] = [pid, f"{lon:.6f}", f"{lat:.6f}", f"{u['easting']:.0f}", f"{u['northing']:.0f}",
                         f"{u['height_ortho']:.2f}",
                         u["mean_velocity"], u["mean_velocity_std"], u["acceleration"], u["acceleration_std"],
                         *( [e["mean_velocity"], e["mean_velocity_std"], e["acceleration"], e["acceleration_std"]]
                            if e else ["", "", "", ""])]
    return [rows[k] for k in sorted(rows)], per_tile


def parse_average_file(path: Path) -> dict[str, Any]:
    """Read an Explorer 'Name/Value' export (egms_pechea_*.txt): header lines before DATA."""
    meta: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() == "DATA":
            break
        if "\t" in line:
            k, v = line.split("\t", 1)
            meta[k.strip()] = v.strip()
    n = re.search(r"(\d+)", meta.get("Point ID", ""))
    return {"file": path.name, "dataset": meta.get("Dataset"), "points": int(n[1]) if n else None,
            "easting": float(meta["easting"]), "northing": float(meta["northing"]),
            "mean_velocity": float(meta["mean_velocity"])}


def cross_check(rows: list[list[Any]], avg: dict[str, Any]) -> dict[str, Any]:
    """Mean of the k points nearest the Explorer average's centre, against the published average.

    The Explorer area is unknown, so this is a plausibility check, not an exact reproduction."""
    col = 6 if avg["dataset"] == "Vertical" else 10
    pts = [(((float(r[3]) - avg["easting"]) ** 2 + (float(r[4]) - avg["northing"]) ** 2) ** 0.5, float(r[col]))
           for r in rows if r[col] != ""]
    pts.sort()
    k = min(avg["points"] or len(pts), len(pts))
    mean = statistics.fmean(v for _, v in pts[:k]) if k else None
    return {**avg, "nearest_k_used": k,
            "nearest_k_mean_velocity": None if mean is None else round(mean, 3),
            "difference_mm_yr": None if mean is None else round(mean - avg["mean_velocity"], 3),
            "radius_m": None if not k else round(pts[k - 1][0])}


def run(raw: Path, coverage: Path, out: Path, buffer_km: float = 5.0,
        averages: list[Path] | None = None) -> dict[str, Any]:
    if out.exists():
        raise IngestError(f"{out} already exists. Delete it on purpose or pick a new name.")
    tiles = find_tiles(raw)
    box = zone_bounds(coverage, buffer_km * 1000)
    rows, per_tile = build_rows(tiles, box)
    if not rows:
        raise IngestError("no radar points inside the pilot zone")

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(OUT_COLUMNS)
        w.writerows(rows)

    t = Transformer.from_crs(SRC_CRS, "EPSG:4326", always_xy=True)
    ups = [float(r[6]) for r in rows]
    report = {
        "dataset_id": DATASET_ID,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_crs": SRC_CRS,
        "zone_buffer_km": buffer_km,
        "zone_bounds_epsg3035": [round(v) for v in box],
        "zone_bounds_wgs84": [round(v, 5) for v in (*t.transform(box[0], box[1]), *t.transform(box[2], box[3]))],
        "points": len(rows),
        "points_without_east_west": sum(1 for r in rows if r[10] == ""),
        "median_vertical_mm_yr": round(statistics.median(ups), 3),
        "per_tile": per_tile,
        "inputs": {p.name: sha256_file(p) for parts in tiles.values() for p in parts.values()},
        "output_sha256": sha256_file(out),
        "cross_check_explorer_averages": [cross_check(rows, parse_average_file(p)) for p in averages or []],
    }
    out.with_name(out.name + ".ingest.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--raw", type=Path, required=True, help="folder with the unpacked EGMS_L3_* folders")
    p.add_argument("--coverage", type=Path, required=True, help="coverage.geojson of the pilot dataset")
    p.add_argument("--out", type=Path, required=True, help="output CSV")
    p.add_argument("--buffer-km", type=float, default=5.0)
    p.add_argument("--average", type=Path, action="append",
                   help="Explorer average export for the cross-check (repeatable)")
    args = p.parse_args(argv)
    try:
        r = run(args.raw, args.coverage, args.out, args.buffer_km, args.average)
    except IngestError as e:
        print(f"INGEST FAILED: {e}", file=sys.stderr)
        return 1
    print(f"{r['points']} points kept, median vertical {r['median_vertical_mm_yr']} mm/yr")
    for c in r["cross_check_explorer_averages"]:
        print(f"{c['dataset']}: Explorer {c['mean_velocity']} vs nearest {c['nearest_k_used']} points "
              f"{c['nearest_k_mean_velocity']} (difference {c['difference_mm_yr']})")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
