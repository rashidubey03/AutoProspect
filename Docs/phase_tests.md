# Phase Tests

## How to Run

Run all automated tests from the project root:

```bash
python -m pytest
```

Run tests for a specific phase:

```bash
python -m pytest tests/test_phase_1_foundation.py
python -m pytest tests/test_phase_2_pipeline.py
```

## Phase 1: Project Foundation

### Covers

- Domain normalization.
- Invalid domain rejection.
- Deduplication helper behavior.
- Environment config loading without requiring secrets.

### Test File

- `tests/test_phase_1_foundation.py`

## Phase 2: Pipeline Orchestrator

### Covers

- Pipeline summary counts.
- Service injection.
- Contact discovery error handling.
- Missing LinkedIn skip behavior.
- Confirmation default behavior blocks sending.

### Test File

- `tests/test_phase_2_pipeline.py`
