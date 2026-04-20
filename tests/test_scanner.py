from __future__ import annotations

from typing import Dict, Iterable, List

from app.config import AppConfig
from app.scanner import JobScanner


class FakeScanner(JobScanner):
    """Overrides network calls for deterministic tests."""

    def __init__(self, config: AppConfig, jobs: List[Dict], companies: List[str]) -> None:
        super().__init__(config=config)
        self._jobs = jobs
        self._companies = companies

    def load_enterprise_companies(self):
        return set(self._companies)

    def fetch_muse_jobs(self, pages: int) -> Iterable[Dict]:
        return list(self._jobs)


def test_scan_matches_only_enterprise_companies_and_keywords():
    config = AppConfig()
    jobs = [
        {
            "name": "Enterprise Account Executive",
            "contents": "Use OpenAI and GitHub Copilot to support customer rollouts",
            "company": {"name": "Acme Corp"},
            "locations": [{"name": "New York, NY"}],
            "refs": {"landing_page": "https://example.com/job1"},
        },
        {
            "name": "Sales Engineer",
            "contents": "Prospect with modern tooling",
            "company": {"name": "Tiny Startup"},
            "locations": [{"name": "Remote"}],
            "refs": {"landing_page": "https://example.com/job2"},
        },
        {
            "name": "Solutions Consultant",
            "contents": "Drive PoCs for large clients",
            "company": {"name": "Acme Corp"},
            "locations": [{"name": "Boston, MA"}],
            "refs": {"landing_page": "https://example.com/job3"},
        },
    ]
    scanner = FakeScanner(config=config, jobs=jobs, companies=["acme corp"])

    summary = scanner.scan(keywords=["OpenAI", "Cursor"], pages=1)

    assert summary.scanned_jobs == 3
    assert summary.enterprise_jobs == 2
    assert len(summary.matches) == 1
    assert summary.matches[0].company == "Acme Corp"
    assert summary.matches[0].matched_keywords == ["OpenAI"]


def test_scan_uses_default_keywords_when_empty_input():
    config = AppConfig(keyword_list=["Windsurf"])
    jobs = [
        {
            "name": "Strategic AE",
            "contents": "Champion Windsurf and AI coding practices",
            "company": {"name": "Global Tech"},
            "locations": [{"name": "Chicago, IL"}],
            "refs": {"landing_page": "https://example.com/job4"},
        }
    ]
    scanner = FakeScanner(config=config, jobs=jobs, companies=["global tech"])

    summary = scanner.scan(keywords=[], pages=1)

    assert len(summary.matches) == 1
    assert summary.matches[0].matched_keywords == ["Windsurf"]
