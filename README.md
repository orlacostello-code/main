# Enterprise Job Keyword Scanner (MVP)

This repository contains an MVP app for enterprise SaaS sales teams.
It scans public job postings, filters to enterprise companies (1,000+ employees),
and returns roles that mention target AI/coding-assistant keywords.

## What it does

- Fetches a list of enterprise companies from a public Fortune 1000 dataset.
- Pulls jobs from:
  - The Muse public jobs API
  - Greenhouse public boards API
  - Lever public postings API
- Filters jobs to enterprise companies.
- Matches jobs against configurable keywords such as:
  - OpenAI
  - Cursor
  - GitHub Copilot
  - Claude Code
  - Windsurf
- Shows results in:
  - A lightweight web UI (`/`)
  - A JSON API endpoint (`/api/scan`)

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000` in your browser.

## API usage

POST `/api/scan`

Example request:

```json
{
  "keywords": ["OpenAI", "Cursor", "GitHub Copilot"],
  "pages": 3
}
```

Example with curl:

```bash
curl -X POST "http://127.0.0.1:8000/api/scan" \
  -H "Content-Type: application/json" \
  -d '{"keywords":["OpenAI","Cursor","GitHub Copilot"],"pages":3}'
```

## Testing

```bash
python3 -m pytest
```

## Notes / next steps

- Current enterprise-company identification is based on Fortune 1000 membership
  from a public 2021 Fortune dataset with employee counts.
- Current jobs sources are The Muse, Greenhouse, and Lever public APIs.
- Greenhouse and Lever use configurable lists of board/site tokens
  in `app/config.py`.
- To productionize:
  - Add more job sources (LinkedIn partner feeds, Workday, SmartRecruiters, etc.).
  - Add persistence (Postgres) and historical trend tracking.
  - Add account-level enrichment and CRM export.
