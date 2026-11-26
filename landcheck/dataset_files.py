"""Write a dataset folder in the shared layer format (PRD Section 7.4, docs/LAYER_FORMAT.md).

Ingest commands build the manifest and features, and this module writes them with the fields
the API loader checks: feature_count, output_sha256 and coverage_sha256. Files are canonical
JSON (sorted keys, no extra spaces, UTF-8, one trailing newline), so the same input always
gives byte-identical files. landcheck.api.dataset.load_dataset reads the result.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class DatasetWriteError(ValueError):
    """The dataset cannot be written in the shared format."""


@dataclass(frozen=True)
class LayerFiles:
    meta: dict[str, Any]  # the manifest entry for the layer, without feature_count/output_sha256
    coverage: dict[str, Any]  # GeoJSON geometry, WGS84
    features: list[dict[str, Any]]


def canonical_json(obj: Any) -> bytes:
    text = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return (text + "\n").encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_dataset(root: Path, manifest: dict[str, Any], layers: list[LayerFiles]) -> None:
    """Write manifest.json, coverage.geojson and layers/<layer_id>.geojson into root.

    `manifest` holds the dataset-level fields. Layer entries come from `layers`. Published
    versions are immutable, so root must not exist yet or must be empty."""
    if root.exists() and any(root.iterdir()):
        raise DatasetWriteError(f"{root} is not empty. Write a new dataset version instead.")
    if "layers" in manifest or "coverage_sha256" in manifest:
        raise DatasetWriteError("manifest must not contain layers or coverage_sha256")
    ids = [layer.meta.get("layer_id") for layer in layers]
    if not ids or len(set(ids)) != len(ids) or not all(isinstance(i, str) and i for i in ids):
        raise DatasetWriteError("layers need unique, non-empty layer_id values")

    (root / "layers").mkdir(parents=True, exist_ok=True)
    entries = []
    for layer in layers:
        for key in ("feature_count", "output_sha256"):
            if key in layer.meta:
                raise DatasetWriteError(f"{layer.meta['layer_id']}: {key} is computed here")
        data = canonical_json({"type": "FeatureCollection", "features": layer.features})
        (root / "layers" / f"{layer.meta['layer_id']}.geojson").write_bytes(data)
        entries.append(
            {**layer.meta, "feature_count": len(layer.features), "output_sha256": sha256(data)}
        )

    coverage = canonical_json(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "id": layer.meta["layer_id"],
                    "geometry": layer.coverage,
                    "properties": {"layer_id": layer.meta["layer_id"]},
                }
                for layer in layers
            ],
        }
    )
    (root / "coverage.geojson").write_bytes(coverage)
    full = {**manifest, "coverage_sha256": sha256(coverage), "layers": entries}
    (root / "manifest.json").write_bytes(canonical_json(full))
