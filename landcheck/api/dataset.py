"""Load a dataset folder (PRD Section 7.4) and answer zone queries.

Layout: manifest.json, coverage.geojson (one feature per layer, properties.layer_id) and
layers/<layer_id>.geojson. Any missing, extra or inconsistent file is an error.
"""

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from shapely.geometry import box, shape
from shapely.geometry.base import BaseGeometry

from landcheck.api.models import LayerMeta, Manifest, QueryCoverage, ZoneProperties

BBox = tuple[float, float, float, float]


class DatasetError(Exception):
    """The dataset is missing or invalid."""


@dataclass(frozen=True)
class Zone:
    id: str
    geometry: dict[str, Any]
    shape: BaseGeometry
    properties: ZoneProperties

    def feature(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        props = self.properties.model_dump(mode="json")
        return {
            "type": "Feature",
            "id": self.id,
            "geometry": self.geometry,
            "properties": {**props, **(extra or {})},
        }


@dataclass(frozen=True)
class LoadedLayer:
    meta: LayerMeta
    coverage_geometry: dict[str, Any]
    coverage_shape: BaseGeometry
    zones: tuple[Zone, ...]


@dataclass(frozen=True)
class Dataset:
    manifest: Manifest
    layers: dict[str, LoadedLayer]
    zones: dict[str, tuple[Zone, LoadedLayer]]

    def query_zones(self, bbox: BBox, layer_ids: list[str]) -> dict[str, Any]:
        query = box(*bbox)
        coverage: list[dict[str, str]] = []
        features: list[dict[str, Any]] = []
        for layer_id in layer_ids:
            layer = self.layers[layer_id]
            coverage.append({"layer_id": layer_id, "status": _coverage(layer, query)})
            features.extend(z.feature() for z in layer.zones if z.shape.intersects(query))
        return {"type": "FeatureCollection", "coverage": coverage, "features": features}


def _coverage(layer: LoadedLayer, query: BaseGeometry) -> QueryCoverage:
    if layer.coverage_shape.contains(query):
        return "full"
    if layer.coverage_shape.intersects(query):
        return "partial"
    return "none"


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise DatasetError(f"Missing dataset file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DatasetError(f"Invalid JSON in {path}: {exc}") from exc


def _geometry(geometry: Any, where: str) -> BaseGeometry:
    try:
        geom = shape(geometry)
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise DatasetError(f"Invalid geometry in {where}: {exc}") from exc
    if geom.is_empty or not geom.is_valid:
        raise DatasetError(f"Empty or invalid geometry in {where}")
    west, south, east, north = geom.bounds
    if not (-180 <= west <= east <= 180 and -90 <= south <= north <= 90):
        raise DatasetError(f"Geometry in {where} is not WGS84 (lon, lat)")
    return geom


def load_dataset(root: Path) -> Dataset:
    try:
        return _load(root)
    except ValidationError as exc:
        raise DatasetError(f"Invalid dataset in {root}: {exc}") from exc


def _load(root: Path) -> Dataset:
    manifest = Manifest.model_validate(_read_json(root / "manifest.json"))
    layer_ids = [layer.layer_id for layer in manifest.layers]
    if len(set(layer_ids)) != len(layer_ids):
        raise DatasetError("Duplicate layer_id in manifest.json")

    coverage_by_layer: dict[str, Any] = {}
    for feature in _read_json(root / "coverage.geojson").get("features", []):
        layer_id = (feature.get("properties") or {}).get("layer_id")
        if layer_id in coverage_by_layer:
            raise DatasetError(f"coverage.geojson has two features for {layer_id}")
        coverage_by_layer[layer_id] = feature.get("geometry")
    if set(coverage_by_layer) != set(layer_ids):
        raise DatasetError("coverage.geojson must have exactly one feature per manifest layer")

    layer_files = {p.stem for p in (root / "layers").glob("*.geojson")}
    if layer_files != set(layer_ids):
        raise DatasetError(f"layers/ files {sorted(layer_files)} do not match the manifest")

    layers: dict[str, LoadedLayer] = {}
    zones: dict[str, tuple[Zone, LoadedLayer]] = {}
    for meta in manifest.layers:
        path = root / "layers" / f"{meta.layer_id}.geojson"
        layer_zones: list[Zone] = []
        for feature in _read_json(path).get("features", []):
            zone_id = feature.get("id")
            where = f"{path} feature {zone_id}"
            if not isinstance(zone_id, str) or not zone_id:
                raise DatasetError(f"Feature without a string id in {path}")
            props = ZoneProperties.model_validate(feature.get("properties"))
            _check_props(props, meta, manifest, where)
            geom = _geometry(feature.get("geometry"), where)
            layer_zones.append(Zone(zone_id, feature["geometry"], geom, props))
        cov = coverage_by_layer[meta.layer_id]
        layer = LoadedLayer(meta, cov, _geometry(cov, "coverage.geojson"), tuple(layer_zones))
        layers[meta.layer_id] = layer
        for zone in layer_zones:
            if zone.id in zones:
                raise DatasetError(f"Duplicate zone id {zone.id}")
            zones[zone.id] = (zone, layer)
    return Dataset(manifest, layers, zones)


def _check_props(props: ZoneProperties, meta: LayerMeta, manifest: Manifest, where: str) -> None:
    expected = {
        "layer_id": meta.layer_id,
        "hazard_type": meta.hazard_type,
        "dataset_version": manifest.dataset_version,
        "sample": manifest.sample,
    }
    for field, value in expected.items():
        if getattr(props, field) != value:
            raise DatasetError(f"{where}: {field} does not match its layer or manifest")
    if props.measurement is not None and not math.isfinite(props.measurement):
        raise DatasetError(f"{where}: measurement is not finite")
