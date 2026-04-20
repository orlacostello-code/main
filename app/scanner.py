"""Service layer that fetches companies and jobs, then matches keywords."""

from __future__ import annotations

import csv
from io import StringIO
from typing import Dict, Iterable, List, Set

import requests

from app.config import AppConfig
from app.models import JobMatch, ScanSummary


class JobScanner:
    """Scanner for enterprise jobs that contain target keyword mentions."""

    def __init__(self, config: AppConfig, timeout_seconds: int = 15) -> None:
        self._config = config
        self._timeout_seconds = timeout_seconds

    def load_enterprise_companies(self) -> Set[str]:
        """Fetch and normalize company names with >= configured employee count."""
        response = requests.get(
            self._config.companies_csv_url, timeout=self._timeout_seconds
        )
        response.raise_for_status()

        reader = csv.DictReader(StringIO(response.text))
        companies: Set[str] = set()
        for row in reader:
            employees_raw = row.get("employees", "").strip()
            company_name = row.get("company", "").strip()
            if not employees_raw or not company_name:
                continue

            employees = _parse_employee_count(employees_raw)
            if employees >= self._config.min_employee_count:
                companies.add(_normalize_name(company_name))
        return companies

    def fetch_muse_jobs(self, pages: int) -> Iterable[Dict]:
        """Yield jobs from The Muse public API for requested pages."""
        for page in range(1, pages + 1):
            response = requests.get(
                self._config.muse_jobs_url,
                params={"page": page},
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            for item in payload.get("results", []):
                yield item

    def scan(self, keywords: List[str], pages: int = 3) -> ScanSummary:
        """Run full scan and return matched job listings."""
        normalized_keywords = [k.strip() for k in keywords if k.strip()]
        if not normalized_keywords:
            normalized_keywords = list(self._config.keyword_list)

        enterprise_companies = self.load_enterprise_companies()
        scanned_jobs = 0
        enterprise_jobs = 0
        matches: List[JobMatch] = []

        for job in self.fetch_muse_jobs(pages=pages):
            scanned_jobs += 1

            company_name = (
                (job.get("company") or {}).get("name") or "Unknown Company"
            ).strip()
            normalized_company = _normalize_name(company_name)
            if normalized_company not in enterprise_companies:
                continue
            enterprise_jobs += 1

            combined_text = _build_search_text(job)
            matched = _keyword_hits(combined_text, normalized_keywords)
            if not matched:
                continue

            locations = job.get("locations") or []
            location_name = locations[0].get("name", "Unknown") if locations else "N/A"
            matches.append(
                JobMatch(
                    company=company_name,
                    title=(job.get("name") or "Untitled Role").strip(),
                    location=location_name,
                    url=(job.get("refs") or {}).get("landing_page", ""),
                    matched_keywords=matched,
                )
            )

        return ScanSummary(
            scanned_jobs=scanned_jobs,
            enterprise_jobs=enterprise_jobs,
            matches=matches,
        )


def _parse_employee_count(raw: str) -> int:
    digits = "".join(ch for ch in raw if ch.isdigit())
    return int(digits) if digits else 0


def _normalize_name(name: str) -> str:
    normalized = name.lower().replace(",", "").replace(".", "")
    return " ".join(normalized.split())


def _build_search_text(job: Dict) -> str:
    contents = [
        job.get("name", ""),
        job.get("contents", ""),
        ((job.get("company") or {}).get("name") or ""),
    ]
    return " ".join(contents).lower()


def _keyword_hits(search_text: str, keywords: List[str]) -> List[str]:
    hits: List[str] = []
    lowered_text = search_text.lower()
    for keyword in keywords:
        if keyword.lower() in lowered_text:
            hits.append(keyword)
    return hits
