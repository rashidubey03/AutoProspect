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
