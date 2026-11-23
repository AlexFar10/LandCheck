"""Load mock results, one file per risk. Any missing or invalid file is an error."""

import json
from pathlib import Path

from landcheck.models import Risk, RiskResult


def load_mock_results(mocks_dir: Path) -> list[RiskResult]:
    results: list[RiskResult] = []
    for risk in Risk:
        path = mocks_dir / f"{risk.value}.json"
        if not path.is_file():
            raise FileNotFoundError(f"Missing mock result for {risk.value}: {path}")
        result = RiskResult.model_validate(json.loads(path.read_text(encoding="utf-8")))
        if result.risk is not risk:
            raise ValueError(f"{path} contains risk {result.risk.value}, expected {risk.value}")
        results.append(result)
    return results
