# Contracts

- `result.schema.json`: the shared module result format (requirements section 6.1). Every
  `landcheck/modules/` module returns it.
- `mocks/`: one mock result per risk. `ground_stability.json` is the `Unknown` / `value: null` case.

`tests/test_contracts.py` checks every mock against the schema. Change the schema and mocks
together.

The HTTP API does not serve these files. Its contract is PRD Section 12, and its sample data
lives in `landcheck/api/fixtures/`.
