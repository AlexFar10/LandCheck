# Contracts

- `result.schema.json`: the shared result format (requirements section 6.1). Every module returns it.
- `mocks/`: one mock result per risk. `ground_stability.json` is the `Unknown` / `value: null` case.

The backend serves these mocks from `POST /analyze` until real modules exist, and its tests check
every mock and every API response against the schema. Change the schema and mocks together.
