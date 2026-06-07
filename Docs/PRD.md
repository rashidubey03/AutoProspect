# PRD: Automated Outreach Pipeline

## Project Overview

Build a command-line application that automates the complete B2B outbound prospecting workflow.

The system accepts a single company domain as input and automatically:

1. Finds similar companies using Apollo.io
2. Finds decision makers, LinkedIn URLs, and verified work emails using Prospeo
3. Sends personalized outreach emails using Brevo

The entire workflow must execute automatically with no manual intervention between stages.

---

# Goal

Given:

```bash
python main.py openai.com
```

The system should:

```text
Input Domain
    ↓
Apollo.io
    ↓
Similar Companies
    ↓
Prospeo
    ↓
Decision Makers
    ↓
Decision Makers + Verified Emails
    ↓
Verified Emails
    ↓
Email Personalization
    ↓
Confirmation Step
    ↓
Brevo
    ↓
Emails Sent
```

---

# Functional Requirements

## FR-1 Domain Input

### Description

Accept a single company domain from CLI.

### Example

```bash
python main.py openai.com
```

### Validation

* Required
* Must be valid domain format
* Remove protocol prefixes
* Remove trailing slashes

### Output

```json
{
  "domain": "openai.com"
}
```

---

## FR-2 Similar Company Discovery

### Service

Apollo.io API

### Input

```json
{
  "domain": "openai.com"
}
```

### Output

```json
[
  {
    "domain": "anthropic.com"
  },
  {
    "domain": "cohere.com"
  }
]
```

### Discovery Strategy

1. Retrieve company metadata from Apollo using the input domain.
2. Extract attributes such as:
   - Industry
   - Employee count
   - Keywords
   - Technologies (if available)
   - Location
3. Search Apollo for companies matching similar attributes.
4. Rank companies based on attribute similarity.
5. Return the top matching company domains.

### Requirements

* Handle pagination
* Handle API failures
* Remove duplicate domains
* Log response counts

---

## FR-3 Decision Maker and Email Discovery

### Service

Prospeo API

### Input

```json
{
  "domain": "anthropic.com"
}
```

### Output

```json
[
  {
    "name": "John Doe",
    "title": "CTO",
      "linkedin_url": "https://linkedin.com/in/johndoe",
      "email": "john@anthropic.com",
      "email_verified": true
  }
]
```

### Target Roles

Prioritize:

* CEO
* CTO
* Founder
* Co-Founder
* VP Engineering
* VP Product
* VP Sales
* Head of Growth

### Requirements

* Filter irrelevant titles
* Remove duplicate contacts
* Store LinkedIn URLs
* Store verified email addresses
* Skip unverified emails
* Skip empty email responses

---

## FR-4 Email Personalization

### Description

Generate personalized outreach email for every verified contact.

### Variables

```text
{name}
{company}
{title}
```

### Example

```text
Subject: Quick Question

Hi John,

I came across Anthropic and noticed your work as CTO.

We help companies automate customer outreach workflows and thought there may be an opportunity to collaborate.

Would you be open to a brief conversation?

Best,
Rashi
```

### Requirements

* Template driven
* Easily editable
* Dynamic variable substitution

---

## FR-5 Confirmation Checkpoint

### Description

Before sending emails, show a summary and require user approval.

### Example

```text
--------------------------------
Companies Found: 20
Contacts Found: 83
Verified Emails: 61
--------------------------------

Proceed with sending emails? (Y/N)
```

### Requirements

* Default = No
* Abort safely

---

## FR-6 Email Sending

### Service

Brevo API

### Input

```json
{
  "recipient": "john@anthropic.com",
  "subject": "Quick Question",
  "body": "..."
}
```

### Output

```json
{
  "status": "sent"
}
```

### Requirements

* Send individually
* Track failures
* Retry transient errors
* Log delivery status

---

# Non-Functional Requirements

## Reliability

Target:

```text
95% successful pipeline completion
```

---

## Performance

Target:

```text
20 companies
100 contacts
< 5 minutes
```

---

## API Rate Limits

The system must:

* Respect provider rate limits
* Retry using exponential backoff
* Log rate-limit events
* Continue processing where possible

---

## Security

### Must

Store credentials in:

```env
APOLLO_API_KEY=
PROSPEO_API_KEY=
BREVO_API_KEY=
```

### Must Not

* Hardcode secrets
* Commit credentials

---

## Maintainability

Each provider must be isolated behind a service class.

Bad:

```python
main.py contains all API calls
```

Good:

```python
ApolloService
ProspeoService
BrevoService
```

---

# Architecture

```text
CLI Input
    │
    ▼
Pipeline Orchestrator
    │
    ├── Apollo Service
    │
    ├── Prospeo Service
    │
    ├── Email Generator
    │
    └── Brevo Service
```

---

# Data Models

## Company

```python
@dataclass
class Company:
    domain: str
    name: str | None = None
    industry: str | None = None
```

## Contact

```python
@dataclass
class Contact:
    name: str
    title: str
    linkedin_url: str
    email: str | None
    email_verified: bool = False
```

## EmailPayload

```python
@dataclass
class EmailPayload:
    recipient: str
    subject: str
    body: str
```

---

# Project Structure

```text
outreach-pipeline/
│
├── main.py
├── config.py
├── requirements.txt
├── .env
│
├── services/
│   ├── apollo_service.py
│   ├── prospeo_service.py
│   └── brevo_service.py
│
├── orchestrator/
│   └── pipeline.py
│
├── models/
│   ├── company.py
│   ├── contact.py
│   └── email_payload.py
│
├── templates/
│   └── outreach_email.txt
│
├── utils/
│   ├── logger.py
│   ├── retry.py
│   ├── validators.py
│   └── dedupe.py
│
└── logs/
```

---

# Error Handling Requirements

## Apollo Failure

```text
Retry 3 times
Then fail pipeline
```

## Prospeo Failure

```text
Retry 3 times
Skip company if needed
```

## Missing LinkedIn

```text
Skip contact
Continue
```

## Missing Email

```text
Skip contact
Continue
```

## Brevo Failure

```text
Retry 3 times
Log failed recipients
Continue remaining sends
```

---

# Logging Requirements

Example:

```text
[INFO] Starting pipeline
[INFO] Domain: openai.com

[INFO] Found 20 companies
[INFO] Found 83 contacts
[INFO] Found 61 verified emails

[INFO] Sending emails...
[INFO] Sent: 58
[ERROR] Failed: 3

[INFO] Pipeline complete
```

---

# Success Criteria

A solution is considered successful if:

* One domain triggers the entire workflow
* No manual copy-pasting is required
* Similar companies are discovered through Apollo.io
* Decision makers are found
* Verified emails are retrieved through Prospeo
* Personalized emails are generated
* Emails are sent through Brevo
* Confirmation step exists before sending
* Errors do not crash the entire pipeline
* Code is modular and easy to extend

---

# Future Enhancements (Out of Scope)

* Web dashboard
* CRM integration
* Multi-user support
* Campaign analytics
* Open tracking
* Reply tracking
* AI-generated personalization
* Queue-based execution
* Database persistence
