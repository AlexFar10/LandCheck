import json

import jsonschema
import pytest
from pydantic import ValidationError

from landcheck.mocks import load_mock_results
from landcheck.models import RiskResult

from .conftest import CONTRACTS

MOCK_FILES = sorted((CONTRACTS / "mocks").glob("*.json"))


@pytest.mark.parametrize("path", MOCK_FILES, ids=lambda p: p.name)
def test_mock_file_matches_schema(path, result_schema):
    jsonschema.validate(json.loads(path.read_text(encoding="utf-8")), result_schema)


def test_schema_rejects_unknown_with_value(result_schema):
    bad = json.loads((CONTRACTS / "mocks" / "ground_stability.json").read_text(encoding="utf-8"))
    bad["value"] = 0.0
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, result_schema)


def test_model_rejects_unknown_with_value():
    data = json.loads((CONTRACTS / "mocks" / "ground_stability.json").read_text(encoding="utf-8"))
    data["value"] = 0.0
    with pytest.raises(ValidationError):
        RiskResult.model_validate(data)


def test_model_rejects_known_level_without_value():
    data = json.loads((CONTRACTS / "mocks" / "flood_history.json").read_text(encoding="utf-8"))
    data["value"] = None
    with pytest.raises(ValidationError):
        RiskResult.model_validate(data)


def test_loader_fails_loudly_when_a_mock_is_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_mock_results(tmp_path)
