import json

import pytest
from fastapi.testclient import TestClient

from landcheck.config import REPO_ROOT, Settings
from landcheck.main import create_app

CONTRACTS = REPO_ROOT / "contracts"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(Settings()))


@pytest.fixture
def result_schema() -> dict:
    return json.loads((CONTRACTS / "result.schema.json").read_text(encoding="utf-8"))


@pytest.fixture
def parcel() -> dict:
    # Small square near Timișoara.
    return {
        "type": "Polygon",
        "coordinates": [
            [[21.20, 45.75], [21.21, 45.75], [21.21, 45.76], [21.20, 45.76], [21.20, 45.75]]
        ],
    }
