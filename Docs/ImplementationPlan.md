# Phase-Wise Project Implementation Plan

## Project

Automated Outreach Pipeline

## Objective

Build a Python command-line application that accepts a company domain and runs the complete outbound workflow:

1. Discover similar companies through Apollo.io.
2. Find decision makers through Prospeo.
3. Resolve and verify work emails through Eazyreach.
4. Generate personalized outreach emails.
5. Ask for final confirmation.
6. Send emails through Brevo.

---

## Phase 1: Project Foundation

### Goal

Create the base application structure, configuration layer, shared models, and local development setup.

### Scope

- Create the PRD-aligned folder structure.
- Add `main.py` CLI entry point.
- Add `config.py` for environment-based API credentials.
- Add `.env.example` with required variables.
  - `APOLLO_API_KEY`
  - `PROSPEO_API_KEY`
  - `EAZYREACH_API_KEY`
  - `BREVO_API_KEY`
- Add `requirements.txt`.
- Create data models:
  - `Company` with `domain`, optional `name`, and optional `industry`
  - `Contact`
  - `EmailPayload`
- Add utility modules:
  - domain validation
  - deduplication helpers
  - logging setup
  - retry wrapper

### Deliverables

- Runnable CLI shell:

```bash
python main.py openai.com
```

- Domain normalization:
  - removes `http://` and `https://`
  - removes trailing slashes
  - validates domain format

### Acceptance Criteria

- Invalid domains fail with a clear message.
- Valid domains are normalized and passed into the pipeline.
- API keys are loaded only from environment variables.
- `.env.example` documents all required provider credentials.
- No secrets are committed.

---

## Phase 2: Pipeline Orchestrator

### Goal

Build the central workflow controller that coordinates all stages without embedding provider-specific API logic.

### Scope

- Create `orchestrator/pipeline.py`.
- Define the full pipeline sequence:
  - input domain
  - similar company discovery
  - contact discovery
  - email resolution
  - email generation
  - confirmation
  - sending
- Add structured logging at every stage.
- Add summary counters:
  - companies found
  - contacts found
  - verified emails found
  - emails sent
  - emails failed

### Deliverables

- A pipeline class or function that can be called by `main.py`.
- Placeholder service calls that can later be swapped with real provider implementations.

### Acceptance Criteria

- The application has one clear orchestration path.
- Provider logic stays outside `main.py`.
- Pipeline failures and skips are visible in logs.

---

## Phase 3: Apollo.io Similar Company Discovery

### Goal

Implement similar company discovery using Apollo.io.

### Scope

- Create `services/apollo_service.py`.
- Implement API authentication.
- Retrieve company metadata for the input domain.
- Extract available similarity attributes:
  - industry
  - employee count
  - keywords
  - technologies
  - location
- Search Apollo.io for companies matching similar attributes.
- Rank companies based on attribute similarity.
- Return the top matching company domains.
- Handle pagination.
- Remove duplicate company domains.
- Log response counts and final company count.
- Retry failed requests up to 3 times using exponential backoff.
- Log rate-limit events.

### Deliverables

- `ApolloService` returning a list of `Company` objects.
- Similarity scoring or ranking logic for Apollo.io company results.

### Acceptance Criteria

- Duplicate domains are removed.
- Returned companies are ranked by similarity before moving forward.
- API failures are retried.
- Provider rate limits are respected and logged.
- If Apollo.io fails after retries, the pipeline stops with a clear error.
- Logs show how many companies were returned and retained.

---

## Phase 4: Prospeo Decision Maker Discovery

### Goal

Find relevant decision makers for each discovered company.

### Scope

- Create `services/prospeo_service.py`.
- Query Prospeo by company domain.
- Filter contacts by target roles:
  - CEO
  - CTO
  - Founder
  - Co-Founder
  - VP Engineering
  - VP Product
  - VP Sales
  - Head of Growth
- Remove duplicate contacts.
- Skip contacts without LinkedIn URLs.
- Retry failed company lookups up to 3 times.
- Continue to the next company if one lookup fails.

### Deliverables

- `ProspeoService` returning a list of `Contact` objects.

### Acceptance Criteria

- Irrelevant titles are filtered out.
- Contacts without LinkedIn URLs are skipped.
- Failed companies do not crash the full pipeline.
- Logs include per-company contact counts and total contacts found.

---

## Phase 5: Eazyreach Email Resolution

### Goal

Resolve verified work emails for discovered contacts.

### Scope

- Create `services/eazyreach_service.py`.
- Query Eazyreach using each contact's LinkedIn URL.
- Attach verified email addresses to contacts.
- Skip empty or unverified email responses.
- Log failures and skipped contacts.

### Deliverables

- Verified contacts with email addresses populated.

### Acceptance Criteria

- Only verified emails move forward.
- Contacts without emails are skipped safely.
- Email resolution errors do not crash the pipeline.
- Logs show total verified emails.

---

## Phase 6: Email Template and Personalization

### Goal

Generate editable, personalized outreach emails for each verified contact.

### Scope

- Create `templates/outreach_email.txt`.
- Add an email generation module or service.
- Support template variables:
  - `{name}`
  - `{company}`
  - `{title}`
- Generate an `EmailPayload` per verified contact.
- Keep subject and body easy to edit.

### Deliverables

- Personalized email payloads ready for review and sending.

### Acceptance Criteria

- Every verified contact receives a generated email.
- Missing optional values are handled gracefully.
- The template can be changed without editing pipeline logic.

---

## Phase 7: Confirmation Checkpoint

### Goal

Add a safe manual approval step before any outbound email is sent.

### Scope

- Display a summary before sending:
  - companies found
  - contacts found
  - verified emails found
  - emails prepared
- Prompt the user:

```text
Proceed with sending emails? (Y/N)
```

- Default to no.
- Abort safely if the user does not explicitly approve.

### Deliverables

- Confirmation prompt integrated into the pipeline.

### Acceptance Criteria

- Emails are never sent without explicit approval.
- Empty input, `N`, or any non-`Y` value aborts sending.
- Abort is logged as an intentional stop, not a failure.

---

## Phase 8: Brevo Email Sending

### Goal

Send personalized emails through Brevo while tracking success and failure.

### Scope

- Create `services/brevo_service.py`.
- Send emails individually.
- Retry transient send failures up to 3 times.
- Continue sending remaining emails when one recipient fails.
- Log each delivery status.
- Track failed recipients.

### Deliverables

- `BrevoService` sending `EmailPayload` objects.
- Final send summary.

### Acceptance Criteria

- Emails are sent one at a time.
- Failed recipients are logged.
- A Brevo failure does not stop remaining sends.
- Final logs show sent and failed counts.

---

## Phase 9: Reliability, Error Handling, and Observability

### Goal

Harden the pipeline against provider failures, missing data, and runtime errors.

### Scope

- Standardize retry behavior.
- Use exponential backoff for retryable provider errors and rate-limit responses.
- Add provider-specific exception handling.
- Add rate-limit detection and logging.
- Add clear skip reasons.
- Add consistent log levels:
  - `INFO` for progress
  - `WARNING` for skipped records
  - `ERROR` for failed API operations
- Ensure API rate-limit behavior follows the PRD:
  - respect provider limits
  - retry with exponential backoff
  - log rate-limit events
  - continue processing where possible
- Ensure the pipeline follows PRD failure behavior:
  - Apollo failure after retries stops the pipeline.
  - Prospeo failure skips the company.
  - Missing LinkedIn skips the contact.
  - Missing or unverified email skips the contact.
  - Brevo failure logs the recipient and continues.

### Deliverables

- Stable error handling across all stages.
- Logs suitable for troubleshooting a complete run.

### Acceptance Criteria

- Expected failures do not produce unclear crashes.
- Logs provide enough detail to diagnose where data was lost or skipped.
- Pipeline behavior matches the PRD.
- Rate-limit events are visible in logs and do not cause avoidable pipeline crashes.

---

## Phase 10: Testing and Validation

### Goal

Verify core behavior without relying entirely on live provider APIs.

### Scope

- Add unit tests for:
  - domain validation
  - deduplication
  - company metadata parsing
  - Apollo.io similarity ranking
  - role filtering
  - email template substitution
  - confirmation default behavior
- Add service tests using mocked API responses.
- Add mocked rate-limit response tests.
- Add orchestrator tests using fake services.
- Add one optional live smoke test mode if credentials are present.

### Deliverables

- Automated test suite.
- Mock fixtures for provider responses.

### Acceptance Criteria

- Tests can run without real API keys.
- Critical edge cases are covered.
- Rate-limit and retry behavior is covered with mocks.
- A fake full-pipeline run completes successfully.

---

## Phase 11: End-to-End Readiness

### Goal

Prepare the application for real usage with credentials and live APIs.

### Scope

- Verify `.env` loading.
- Run a live test with a small target limit.
- Confirm external API response parsing.
- Confirm Apollo.io metadata extraction and similarity ranking.
- Confirm confirmation checkpoint blocks sending unless approved.
- Confirm Brevo sends to the expected recipient list only.
- Review logs after a real run.

### Deliverables

- End-to-end tested CLI pipeline.
- Final setup notes for local execution.

### Acceptance Criteria

- One command starts the complete workflow.
- No manual copy-pasting is required between stages.
- Confirmation appears before sending.
- Sent and failed email counts are reported.

---

## Suggested Build Order

1. Foundation, models, config, validators, and logging.
2. Pipeline orchestrator with fake service outputs.
3. Email template generation and confirmation checkpoint.
4. Provider integrations in this order:
   - Apollo.io
   - Prospeo
   - Eazyreach
   - Brevo
5. Retry and error handling hardening.
6. Unit and mocked integration tests.
7. Live end-to-end smoke test.

---

## Recommended Milestones

### Milestone 1: Local Pipeline Skeleton

The CLI accepts a domain and runs through a fake pipeline from company discovery to prepared emails.

### Milestone 2: Data Collection Complete

Apollo.io, Prospeo, and Eazyreach are integrated and produce verified contacts.

### Milestone 3: Send-Ready Workflow

Templates, confirmation, and Brevo sending are complete.

### Milestone 4: Production-Ready CLI

Retries, logging, tests, and end-to-end validation are complete.

---

## Key Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Provider API response formats differ from assumptions | Build adapters per service and test with real sample responses |
| API rate limits slow the pipeline | Add retries, backoff, and optional per-stage limits |
| Low email verification rate | Log skip reasons and keep discovery counts visible |
| Accidental email sends | Default confirmation to no and require explicit `Y` |
| Secrets exposure | Use `.env`, `.env.example`, and `.gitignore` |
| Hard-to-debug failures | Centralize logging and include stage-specific counts |

---

## Definition of Done

The project is complete when:

- `python main.py openai.com` triggers the full pipeline.
- Similar companies are discovered.
- Decision makers are found and filtered.
- Verified work emails are resolved.
- Personalized outreach emails are generated.
- The user must approve before sending.
- Emails are sent through Brevo.
- Failures are retried or skipped according to the PRD.
- Logs clearly show pipeline progress and final results.
- Tests validate core logic and mocked provider flows.
