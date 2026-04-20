"""Application configuration and defaults."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


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

# Uses Clearbit free logo domain lookup and has a broad set of companies.
COMPANIES_CSV_URL = (
    "https://raw.githubusercontent.com/hadisalimov/"
    "f500/main/data/fortune1000-2021.csv"
)

# TheMuse has public jobs API without an API key.
MUSE_JOBS_API_URL = "https://www.themuse.com/api/public/jobs"


@dataclass
class AppConfig:
    """Runtime config used by scanner and API layer."""

    min_employee_count: int = 1000
    keyword_list: List[str] = field(default_factory=lambda: list(DEFAULT_KEYWORDS))
    companies_csv_url: str = COMPANIES_CSV_URL
    muse_jobs_url: str = MUSE_JOBS_API_URL
