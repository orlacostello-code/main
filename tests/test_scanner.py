from __future__ import annotations

from typing import Dict, Iterable, List

from app.config import AppConfig
from app.scanner import JobScanner


class FakeScanner(JobScanner):
    """Overrides network calls for deterministic tests."""

    def __init__(
        self,
        config: AppConfig,
        muse_jobs: List[Dict],
        greenhouse_jobs: List[Dict],
        lever_jobs: List[Dict],
        smartrecruiters_jobs: List[Dict],
        workday_jobs: List[Dict],
        companies: List[str],
    ) -> None:
        super().__init__(config=config)
        self._muse_jobs = muse_jobs
        self._greenhouse_jobs = greenhouse_jobs
        self._lever_jobs = lever_jobs
        self._smartrecruiters_jobs = smartrecruiters_jobs
        self._workday_jobs = workday_jobs
        self._companies = companies

    def load_enterprise_companies(self):
        return set(self._companies)

    def fetch_muse_jobs(self, pages: int) -> Iterable[Dict]:
        return list(self._muse_jobs)

    def fetch_greenhouse_jobs(self, pages: int) -> Iterable[Dict]:
        return list(self._greenhouse_jobs)

    def fetch_lever_jobs(self, pages: int) -> Iterable[Dict]:
        return list(self._lever_jobs)

    def fetch_smartrecruiters_jobs(self, pages: int) -> Iterable[Dict]:
        return list(self._smartrecruiters_jobs)

    def fetch_workday_jobs(self, pages: int) -> Iterable[Dict]:
        return list(self._workday_jobs)


def test_scan_matches_only_enterprise_companies_and_keywords():
    config = AppConfig(workday_company_overrides={"acme/external": "Acme Corp"})
    muse_jobs = [
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
    greenhouse_jobs = [
        {
            "title": "Sales Director",
            "content": "Expand pipeline with Cursor and enterprise AI workflows.",
            "location": {"name": "Remote"},
            "absolute_url": "https://example.com/job-gh-1",
            "__greenhouse_board": "acme-corp",
        }
    ]
    lever_jobs = [
        {
            "text": "Account Executive",
            "descriptionPlain": "Drive platform adoption.",
            "categories": {"location": "San Francisco", "team": "Sales"},
            "hostedUrl": "https://example.com/job-lev-1",
            "__lever_site": "tiny-startup",
        }
    ]
    smartrecruiters_jobs = [
        {
            "name": "Enterprise Sales Specialist",
            "location": {"city": "Austin", "region": "TX", "country": "US"},
            "department": {"label": "Sales"},
            "typeOfEmployment": {"label": "Full-time"},
            "ref": "https://example.com/job-sr-1",
            "__smartrecruiters_company": "acme-corp",
        }
    ]
    workday_jobs = [
        {
            "title": "Principal AE",
            "locationsText": ["Remote, US"],
            "externalPath": "/job/Remote-US/Principal-AE_JR-001",
            "bulletFields": ["Use OpenAI and GenAI workflows for enterprise accounts"],
            "__workday_tenant": "acme",
            "__workday_site": "external",
            "__workday_host": "acme.wd1.myworkdayjobs.com",
        }
    ]
    scanner = FakeScanner(
        config=config,
        muse_jobs=muse_jobs,
        greenhouse_jobs=greenhouse_jobs,
        lever_jobs=lever_jobs,
        smartrecruiters_jobs=smartrecruiters_jobs,
        workday_jobs=workday_jobs,
        companies=["acme corp"],
    )

    summary = scanner.scan(keywords=["OpenAI", "Cursor"], pages=1)

    assert summary.scanned_jobs == 7
    assert summary.enterprise_jobs == 5
    assert len(summary.matches) == 3
    assert summary.matches[0].company == "Acme Corp"
    assert summary.matches[0].matched_keywords == ["OpenAI"]
    assert summary.matches[1].source == "Greenhouse"
    assert summary.matches[1].matched_keywords == ["Cursor"]
    assert summary.matches[2].source == "Workday"
    assert summary.matches[2].matched_keywords == ["OpenAI"]


def test_scan_uses_default_keywords_when_empty_input():
    config = AppConfig(
        keyword_list=["Windsurf"],
        lever_company_overrides={"global-tech": "Global Tech"},
    )
    muse_jobs = [
        {
            "name": "Strategic AE",
            "contents": "Champion Windsurf and AI coding practices",
            "company": {"name": "Global Tech"},
            "locations": [{"name": "Chicago, IL"}],
            "refs": {"landing_page": "https://example.com/job4"},
        }
    ]
    greenhouse_jobs = []
    lever_jobs = [
        {
            "text": "Solutions Engineer",
            "descriptionPlain": "Help customers evaluate Windsurf workflows",
            "categories": {"location": "Remote", "team": "Sales"},
            "hostedUrl": "https://example.com/job5",
            "__lever_site": "global-tech",
        }
    ]
    smartrecruiters_jobs = [
        {
            "name": "Solutions Architect",
            "location": {"city": "Chicago", "region": "IL", "country": "US"},
            "department": {"label": "Sales Engineering"},
            "typeOfEmployment": {"label": "Full-time"},
            "ref": "https://example.com/job6",
            "__smartrecruiters_company": "global-tech",
        }
    ]
    workday_jobs = []
    scanner = FakeScanner(
        config=config,
        muse_jobs=muse_jobs,
        greenhouse_jobs=greenhouse_jobs,
        lever_jobs=lever_jobs,
        smartrecruiters_jobs=smartrecruiters_jobs,
        workday_jobs=workday_jobs,
        companies=["global tech"],
    )

    summary = scanner.scan(keywords=[], pages=1)

    assert len(summary.matches) == 2
    assert summary.matches[0].matched_keywords == ["Windsurf"]
    assert summary.matches[1].source == "Lever"
    assert summary.matches[1].matched_keywords == ["Windsurf"]


def test_load_enterprise_companies_supports_employee_column_variants() -> None:
    class EnterpriseCSVScanner(JobScanner):
        def _get_text(self, url: str) -> str:
            return (
                "company,num. of employees\n"
                "Acme Corp,5000\n"
                "Small Co,500\n"
                "Big Co,1200\n"
            )

    scanner = EnterpriseCSVScanner(config=AppConfig(min_employee_count=1000))
    companies = scanner.load_enterprise_companies()

    assert companies == {"acme corp", "big co"}
