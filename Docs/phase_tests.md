# Phase Tests

## How to Run

Install dependencies from the project root:

```bash
python -m pip install -r requirements.txt
```

Run the current CLI build:

```bash
python main.py openai.com
```

You can also pass a URL-style domain:

```bash
python main.py https://openai.com/
```

Current expected behavior:

- The domain is normalized and validated.
- The Phase 2 orchestrator runs.
- Apollo runs when `APOLLO_API_KEY` is present; Prospeo, email generation, confirmation, and Brevo are still placeholder stages.
- The command returns a JSON pipeline summary with zero discovered/sent counts until later phases add real integrations.

Example output:

```json
{
  "domain": "openai.com",
  "companies_found": 0,
  "contacts_found": 0,
  "verified_emails": 0,
  "emails_prepared": 0,
  "emails_sent": 0,
  "emails_failed": 0,
  "failed_recipients": []
}
```

Run all automated tests from the project root:

```bash
python -m pytest
```

Run tests for a specific phase:

```bash
python -m pytest tests/test_phase_1_foundation.py
python -m pytest tests/test_phase_2_pipeline.py
python -m pytest tests/test_phase_3_apollo.py
```

## Phase 1: Project Foundation

### Manual Check

```bash
python main.py https://openai.com/
```

Expected result: the output domain is `openai.com`.

### Covers

- Domain normalization.
- Invalid domain rejection.
- Deduplication helper behavior.
- Environment config loading without requiring secrets.

### Test File

- `tests/test_phase_1_foundation.py`

## Phase 2: Pipeline Orchestrator

### Manual Check

```bash
python main.py openai.com
```

Expected result: the pipeline runs through the placeholder orchestrator and returns summary counts.

### Covers

- Pipeline summary counts.
- Service injection.
- Contact discovery error handling.
- Missing LinkedIn skip behavior.
- Missing or unverified email skip behavior.
- Confirmation default behavior blocks sending.

### Test File

- `tests/test_phase_2_pipeline.py`

## Phase 3: Apollo.io Similar Company Discovery

### Manual Check

Add `APOLLO_API_KEY` to `.env`, then run:

```bash
python main.py openai.com
```

Expected result: the Apollo stage attempts company metadata enrichment and similar-company search, then the remaining placeholder stages return zero contact/send counts until later phases are implemented.

### Covers

- Apollo organization enrichment response parsing.
- Apollo organization search response parsing.
- Search filters derived from metadata.
- Similarity ranking and duplicate filtering.
- Rate-limit retry behavior.

### Test File

- `tests/test_phase_3_apollo.py`
