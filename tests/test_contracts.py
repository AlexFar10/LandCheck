"""The shared module result format (contracts/result.schema.json) and its mock results."""

import json
from pathlib import Path

import jsonschema
import pytest

CONTRACTS = Path(__file__).resolve().parents[1] / "contracts"
MOCK_FILES = sorted((CONTRACTS / "mocks").glob("*.json"))


@pytest.fixture
def result_schema() -> dict:
    return json.loads((CONTRACTS / "result.schema.json").read_text(encoding="utf-8"))


def test_there_is_one_mock_per_risk():
    assert [p.stem for p in MOCK_FILES] == [
        "flood_history",
        "flood_susceptibility",
        "ground_stability",
        "land_use_history",
    ]


@pytest.mark.parametrize("path", MOCK_FILES, ids=lambda p: p.name)
def test_mock_file_matches_schema(path, result_schema):
    jsonschema.validate(json.loads(path.read_text(encoding="utf-8")), result_schema)


def test_schema_rejects_unknown_with_value(result_schema):
    bad = json.loads((CONTRACTS / "mocks" / "ground_stability.json").read_text(encoding="utf-8"))
    bad["value"] = 0.0
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, result_schema)
