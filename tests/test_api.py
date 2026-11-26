"""API contract tests (PRD Section 12) against the bundled sample fixture."""

import json
import shutil

import pytest
from fastapi.testclient import TestClient

from landcheck.api.config import SAMPLE_DATASET_DIR, Settings
from landcheck.api.main import create_app, parse_bbox

ZONE_FIELDS = {
    "hazard_type",
    "classification",
    "measurement",
    "unit",
    "observation_date",
    "source_name",
    "source_url",
    "coverage_status",
    "method_version",
    "layer_id",
    "dataset_version",
}
LAYER_ID = "sample_flood_history_v0"
ZONE_ID = "sample_flood_history_v0-0001"
PILOT_BBOX = "27.70,45.55,27.90,45.70"  # contains the fixture coverage
INSIDE_BBOX = "27.76,45.61,27.79,45.63"  # inside coverage, overlaps zone 0001
EMPTY_INSIDE_BBOX = "27.85,45.66,27.86,45.67"  # inside coverage, no zones
OUTSIDE_BBOX = "21.20,45.70,21.30,45.80"  # Timișoara, outside the pilot


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(Settings(dataset_dir=None, cors_origins="")))


def assert_error(response, status: int, code: str) -> None:
    assert response.status_code == status
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]
    assert isinstance(body["error"]["details"], dict)


# /health (LC-06)


def test_health_returns_section_12_3_shape(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert {"status", "version", "git_commit", "dataset_id", "dataset_version"} <= set(body)
    assert body["status"] == "ok"
    assert body["version"] == "0.1.0"
    assert isinstance(body["git_commit"], str) and body["git_commit"]


def test_health_labels_the_fixture_as_sample(client):
    body = client.get("/health").json()
    assert body["dataset_id"] == "sample-fixture"
    assert body["sample"] is True


def test_health_uses_git_commit_env(monkeypatch):
    monkeypatch.setenv("GIT_COMMIT", "abc123")
    client = TestClient(create_app(Settings(dataset_dir=None)))
    assert client.get("/health").json()["git_commit"] == "abc123"


def test_openapi_docs_load(client):
    assert client.get("/docs").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    assert {"/health", "/api/v1/layers", "/api/v1/zones", "/api/v1/zones/{zone_id}"} <= set(paths)


def test_old_analyze_endpoint_is_gone(client):
    assert client.post("/analyze", json={}).status_code in (404, 405)


# /api/v1/layers


def test_layers_returns_labelled_fixture(client):
    response = client.get("/api/v1/layers")
    assert response.status_code == 200
    layers = response.json()["layers"]
    assert [layer["id"] for layer in layers] == [LAYER_ID]
    layer = layers[0]
    assert layer["sample"] is True
    assert "SAMPLE" in layer["title"]
    assert "not real" in layer["source_name"]
    assert layer["feature_count"] == 2
    assert layer["coverage"]["type"] == "Polygon"
    assert layer["legend"] and layer["limitations"]
    for field in ("observation_date", "source_url", "method_version", "dataset_version"):
        assert layer[field]


# /api/v1/zones


def test_zones_returns_feature_collection_with_all_fields(client):
    response = client.get("/api/v1/zones", params={"bbox": PILOT_BBOX})
    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert body["coverage"] == [{"layer_id": LAYER_ID, "status": "partial"}]
    assert len(body["features"]) == 2
    for feature in body["features"]:
        assert feature["type"] == "Feature"
        assert isinstance(feature["id"], str) and feature["id"]
        assert feature["geometry"]["type"] == "Polygon"
        assert ZONE_FIELDS <= set(feature["properties"])
        assert feature["properties"]["sample"] is True


def test_zones_nullable_fields_stay_null(client):
    features = client.get("/api/v1/zones", params={"bbox": PILOT_BBOX}).json()["features"]
    for feature in features:
        props = feature["properties"]
        assert props["classification"] is None
        assert props["measurement"] is None
        assert props["unit"] is None


def test_zones_inside_coverage_filters_by_bbox(client):
    body = client.get("/api/v1/zones", params={"bbox": INSIDE_BBOX}).json()
    assert body["coverage"] == [{"layer_id": LAYER_ID, "status": "full"}]
    assert [f["id"] for f in body["features"]] == [ZONE_ID]


def test_zones_inside_coverage_without_features_is_full_not_none(client):
    body = client.get("/api/v1/zones", params={"bbox": EMPTY_INSIDE_BBOX}).json()
    assert body["features"] == []
    assert body["coverage"] == [{"layer_id": LAYER_ID, "status": "full"}]


def test_zones_outside_pilot_is_200_with_no_coverage(client):
    response = client.get("/api/v1/zones", params={"bbox": OUTSIDE_BBOX})
    assert response.status_code == 200
    body = response.json()
    assert body["features"] == []
    assert body["coverage"] == [{"layer_id": LAYER_ID, "status": "none"}]


def test_zones_layer_filter(client):
    body = client.get("/api/v1/zones", params={"bbox": PILOT_BBOX, "layer": LAYER_ID}).json()
    assert len(body["features"]) == 2


def test_zones_unknown_layer_is_404(client):
    response = client.get("/api/v1/zones", params={"bbox": PILOT_BBOX, "layer": "nope"})
    assert_error(response, 404, "LAYER_NOT_FOUND")


@pytest.mark.parametrize(
    "bbox",
    [
        None,
        "",
        "abc",
        "1,2,3",
        "1,2,3,4,5",
        "27.9,45.5,27.7,45.7",  # west > east
        "27.7,45.7,27.9,45.5",  # south > north
        "27.7,45.5,27.7,45.7",  # zero width
        "-181,45,27,46",
        "27,-91,28,46",
        "nan,45,28,46",
        "inf,45,28,46",
    ],
)
def test_zones_invalid_bbox_is_400(client, bbox):
    params = {} if bbox is None else {"bbox": bbox}
    assert_error(client.get("/api/v1/zones", params=params), 400, "INVALID_BBOX")


def test_parse_bbox_returns_lon_lat_order():
    assert parse_bbox("27.7,45.5,27.9,45.7") == (27.7, 45.5, 27.9, 45.7)


# /api/v1/zones/{id}


def test_zone_detail_adds_layer_evidence(client):
    response = client.get(f"/api/v1/zones/{ZONE_ID}")
    assert response.status_code == 200
    feature = response.json()
    assert feature["id"] == ZONE_ID
    props = feature["properties"]
    assert ZONE_FIELDS <= set(props)
    assert props["sample"] is True
    assert props["meaning"] and props["limitations"] and props["attribution"]
    assert props["measurement"] is None


def test_zone_unknown_id_is_404(client):
    assert_error(client.get("/api/v1/zones/does-not-exist"), 404, "ZONE_NOT_FOUND")


# Dataset failures


def test_missing_dataset_returns_503(tmp_path):
    client = TestClient(create_app(Settings(dataset_dir=tmp_path / "missing")))
    health = client.get("/health")
    assert health.status_code == 503
    assert health.json()["status"] == "error"
    assert_error(client.get("/api/v1/layers"), 503, "DATASET_UNAVAILABLE")
    assert_error(
        client.get("/api/v1/zones", params={"bbox": PILOT_BBOX}), 503, "DATASET_UNAVAILABLE"
    )


def test_corrupted_dataset_returns_503(tmp_path):
    # The format rules themselves are tested in tests/test_dataset.py.
    root = tmp_path / "dataset"
    shutil.copytree(SAMPLE_DATASET_DIR, root)
    path = root / "layers" / f"{LAYER_ID}.geojson"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["features"][0]["properties"]["sample"] = False
    path.write_bytes(json.dumps(data).encode("utf-8"))
    client = TestClient(create_app(Settings(dataset_dir=root)))
    assert client.get("/health").status_code == 503
    assert_error(client.get("/api/v1/layers"), 503, "DATASET_UNAVAILABLE")


def test_unexpected_error_hides_details():
    app = create_app(Settings(dataset_dir=None))

    @app.get("/boom")
    def boom():
        raise RuntimeError("secret internal detail")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom")
    assert_error(response, 500, "INTERNAL_ERROR")
    assert "secret" not in response.text


def test_cors_is_off_by_default(client):
    response = client.get("/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in response.headers


def test_cors_allows_configured_origin():
    client = TestClient(
        create_app(Settings(dataset_dir=None, cors_origins="http://localhost:5173"))
    )
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
