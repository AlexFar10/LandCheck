"""FastAPI app (PRD Section 12).

Dev:  uvicorn landcheck.api.main:app --reload --host 127.0.0.1 --port 3000
Prod: python -m landcheck.api   (binds 0.0.0.0:${PORT:-3000})
"""

import logging
import math
import os
import subprocess
from importlib.metadata import version as package_version
from typing import Annotated, Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from landcheck.api.config import REPO_ROOT, Settings, get_settings
from landcheck.api.dataset import BBox, Dataset, DatasetError, load_dataset
from landcheck.api.errors import ApiError, install_error_handlers
from landcheck.api.models import Health, Layer, LayersResponse

log = logging.getLogger(__name__)

BBOX_MESSAGE = "bbox must be west,south,east,north in WGS84."
# Manifest layer fields that GET /api/v1/layers serves as they are (PRD 12.4).
SERVED_LAYER_FIELDS = {
    "title",
    "hazard_type",
    "default_visible",
    "observation_date",
    "sensor",
    "source_name",
    "attribution",
    "meaning",
    "limitations",
    "legend",
}


def git_commit() -> str:
    """GIT_COMMIT if set (container builds have no .git), else the checkout's HEAD."""
    if commit := os.environ.get("GIT_COMMIT", "").strip():
        return commit
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return out.stdout.strip() or "unknown"


def parse_bbox(raw: str | None) -> BBox:
    details = {"bbox": raw[:200] if raw is not None else None}
    parts = (raw or "").split(",")
    try:
        west, south, east, north = (float(p) for p in parts)
    except ValueError:
        raise ApiError(400, "INVALID_BBOX", BBOX_MESSAGE, details) from None
    values = (west, south, east, north)
    if not (
        all(math.isfinite(v) for v in values)
        and -180 <= west < east <= 180
        and -90 <= south < north <= 90
    ):
        raise ApiError(400, "INVALID_BBOX", BBOX_MESSAGE, details)
    return values


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    dataset_dir = settings.resolved_dataset_dir
    # Loaded once at startup. A broken dataset is logged and reported as 503, never hidden.
    dataset: Dataset | None
    try:
        dataset = load_dataset(dataset_dir)
    except DatasetError:
        log.exception("Dataset unavailable: %s", dataset_dir)
        dataset = None
    else:
        if dataset.manifest.sample:
            log.warning("Serving SAMPLE fixture data from %s. Not real results.", dataset_dir)

    commit = git_commit()
    app_version = package_version("landcheck")

    app = FastAPI(title="Land Check API", version=app_version)
    install_error_handlers(app)
    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_methods=["GET"],
            allow_headers=["Content-Type"],
        )

    def require_dataset() -> Dataset:
        if dataset is None:
            raise ApiError(503, "DATASET_UNAVAILABLE", "The dataset is not available.")
        return dataset

    @app.get("/health", response_model=Health)
    def health() -> Any:
        if dataset is None:
            body = Health(
                status="error",
                version=app_version,
                git_commit=commit,
                dataset_id=None,
                dataset_version=None,
                sample=None,
            )
            return JSONResponse(body.model_dump(), status_code=503)
        manifest = dataset.manifest
        return Health(
            status="ok",
            version=app_version,
            git_commit=commit,
            dataset_id=manifest.dataset_id,
            dataset_version=manifest.dataset_version,
            sample=manifest.sample,
        )

    @app.get("/api/v1/layers")
    def layers() -> LayersResponse:
        data = require_dataset()
        manifest = data.manifest
        return LayersResponse(
            layers=[
                Layer(
                    # Only the Section 12.4 fields. Provenance stays in the manifest.
                    **layer.meta.model_dump(include=SERVED_LAYER_FIELDS),
                    id=layer.meta.layer_id,
                    source_url=str(layer.meta.source_url),
                    feature_count=len(layer.zones),
                    coverage=layer.coverage_geometry,
                    method_version=manifest.method_version_of(layer.meta),
                    dataset_version=manifest.dataset_version,
                    sample=manifest.sample,
                )
                for layer in data.layers.values()
            ]
        )

    @app.get("/api/v1/zones")
    def zones(
        bbox: Annotated[str | None, Query(description="west,south,east,north in WGS84")] = None,
        layer: Annotated[str | None, Query(description="Optional layer ID")] = None,
    ) -> dict[str, Any]:
        data = require_dataset()
        bounds = parse_bbox(bbox)
        if layer is not None and layer not in data.layers:
            raise ApiError(404, "LAYER_NOT_FOUND", "Unknown layer ID.", {"layer": layer[:200]})
        layer_ids = [layer] if layer is not None else list(data.layers)
        return data.query_zones(bounds, layer_ids)

    @app.get("/api/v1/zones/{zone_id}")
    def zone(zone_id: str) -> dict[str, Any]:
        data = require_dataset()
        found = data.zones.get(zone_id)
        if found is None:
            raise ApiError(404, "ZONE_NOT_FOUND", "Unknown zone ID.", {"id": zone_id[:200]})
        feature, layer = found
        return feature.feature(
            {
                "meaning": layer.meta.meaning,
                "limitations": layer.meta.limitations,
                "attribution": layer.meta.attribution,
            }
        )

    return app


app = create_app()
