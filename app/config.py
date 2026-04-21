"""Application configuration and defaults."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


DEFAULT_KEYWORDS = [
    "OpenAI",
    "Cursor",
    "GitHub Copilot",
    "Claude Code",
    "Windsurf",
    "Anthropic",
    "LLM",
    "Generative AI",
]

# Fortune 1000 list with employee counts.
COMPANIES_CSV_URL = (
    "https://raw.githubusercontent.com/hadisalimov/"
    "f500/main/data/fortune1000-2021.csv"
)

# TheMuse has public jobs API without an API key.
MUSE_JOBS_API_URL = "https://www.themuse.com/api/public/jobs"

# Greenhouse board API pattern: /boards/{board_token}/jobs?content=true
GREENHOUSE_JOBS_API_BASE_URL = "https://boards-api.greenhouse.io/v1/boards"

# Lever postings API pattern: /postings/{site_token}?mode=json
LEVER_JOBS_API_BASE_URL = "https://api.lever.co/v0/postings"

# Seed tokens for large SaaS/enterprise orgs that commonly publish public boards.
DEFAULT_GREENHOUSE_BOARDS = [
    "cloudflare",
    "datadog",
    "databricks",
    "hubspot",
    "mongodb",
    "okta",
    "snowflake",
    "stripe",
    "twilio",
]

DEFAULT_LEVER_SITES = [
    "asana",
    "coursera",
    "samsara",
    "upwork",
]

LEVER_SITE_COMPANY_NAME_OVERRIDES = {
    "asana": "Asana",
    "coursera": "Coursera",
    "samsara": "Samsara",
    "upwork": "Upwork",
}

GREENHOUSE_BOARD_COMPANY_NAME_OVERRIDES = {
    "cloudflare": "Cloudflare",
    "datadog": "Datadog",
    "databricks": "Databricks",
    "hubspot": "HubSpot",
    "mongodb": "MongoDB",
    "okta": "Okta",
    "snowflake": "Snowflake",
    "stripe": "Stripe",
    "twilio": "Twilio",
}


@dataclass
class AppConfig:
    """Runtime config used by scanner and API layer."""

    min_employee_count: int = 1000
    keyword_list: List[str] = field(default_factory=lambda: list(DEFAULT_KEYWORDS))
    companies_csv_url: str = COMPANIES_CSV_URL
    muse_jobs_url: str = MUSE_JOBS_API_URL
    greenhouse_jobs_base_url: str = GREENHOUSE_JOBS_API_BASE_URL
    lever_jobs_base_url: str = LEVER_JOBS_API_BASE_URL
    greenhouse_boards: List[str] = field(
        default_factory=lambda: list(DEFAULT_GREENHOUSE_BOARDS)
    )
    lever_sites: List[str] = field(default_factory=lambda: list(DEFAULT_LEVER_SITES))
    greenhouse_company_overrides: Dict[str, str] = field(
        default_factory=lambda: dict(GREENHOUSE_BOARD_COMPANY_NAME_OVERRIDES)
    )
    lever_company_overrides: Dict[str, str] = field(
        default_factory=lambda: dict(LEVER_SITE_COMPANY_NAME_OVERRIDES)
    )
