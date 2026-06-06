# Phase Contexts

## Phase 1: Project Foundation

### User Instructions

- Start phase-wise implementation from Phase 1.
- Record standing instructions in `Docs/SKILL.md`.
- Store phase context in this file.
- Create a new feature branch for new features.
- After each phase, push completed work to the repository on `main`.
- Update `Docs/SKILL.md` whenever new standing instructions are given.

### PRD Context

- The application is a Python CLI for automated B2B outbound prospecting.
- The CLI accepts one company domain.
- Domain input must be required, normalized, and validated.
- Credentials must come from environment variables:
  - `APOLLO_API_KEY`
  - `PROSPEO_API_KEY`
  - `EAZYREACH_API_KEY`
  - `BREVO_API_KEY`
- Providers must be isolated behind service classes in later phases.
- The `Company` model includes `domain`, optional `name`, and optional `industry`.
- The `Contact` model includes `name`, `title`, `linkedin_url`, and optional `email`.
- The `EmailPayload` model includes `recipient`, `subject`, and `body`.

### Implementation Notes

- Created the Phase 1 CLI foundation.
- Added environment configuration loading with `python-dotenv`.
- Added shared data models.
- Added utility modules for logging, retry behavior, validation, and deduplication.
- Added `.env.example` and `.gitignore` to prevent credential commits.

## Phase 2: Pipeline Orchestrator

### User Instructions

- Push the feature branch as well as `main`.
- Branch names should be only the feature name.
- `main` should contain the final phase result.

### PRD Context

- The pipeline must coordinate domain input, similar company discovery, contact discovery, email resolution, email generation, confirmation, and sending.
- Provider-specific logic must stay outside `main.py`.
- Logs must show pipeline progress and summary counts.
- Later phases will replace placeholder services with Apollo.io, Prospeo, Eazyreach, email template generation, confirmation, and Brevo implementations.

### Implementation Notes

- Created `orchestrator/pipeline.py`.
- Added `Pipeline` as the single orchestration path.
- Added injectable placeholder services for all future provider stages.
- Added `PipelineResult` with summary counters.
- Updated `main.py` to validate the domain and run the orchestrator.
- Updated project instructions to require pushing both the feature branch and `main`.

## Test Setup Instruction Update

### User Instructions

- From now on, provide tests to check each phase.
- Store phase test instructions in a separate Markdown file in `Docs`.
- Create a `tests/` folder to store all automated tests.

### Implementation Notes

- Added `Docs/phase_tests.md`.
- Added `pytest` to `requirements.txt`.
- Added automated tests for Phase 1 and Phase 2.
- Updated `Docs/SKILL.md` with the new standing test instructions.

## Run Instructions Update

### User Instructions

- Explain how to run whatever has been implemented so far.
- Include those run instructions in `Docs/phase_tests.md`.
- Also record the run-instruction context in this file.

### Current Runtime Context

- The project is currently implemented through Phase 2.
- Running `python main.py openai.com` validates the domain and executes the pipeline orchestrator.
- Provider stages are placeholders until later phases.
- The current CLI output is a JSON summary with zero companies, contacts, verified emails, prepared emails, sent emails, and failed emails.

### Commands

```bash
python -m pip install -r requirements.txt
python main.py openai.com
python main.py https://openai.com/
python -m pytest
```
