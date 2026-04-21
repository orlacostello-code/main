"""Service layer that fetches companies and jobs, then matches keywords."""

from __future__ import annotations

import csv
from io import StringIO
from typing import Any, Dict, Iterable, List, Set

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
        csv_text = self._get_text(self._config.companies_csv_url)
        reader = csv.DictReader(StringIO(csv_text))
        companies: Set[str] = set()
        for row in reader:
            employees_raw = (
                row.get("employees", "").strip()
                or row.get("num. of employees", "").strip()
            )
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
            try:
                payload = self._get_json(
                    self._config.muse_jobs_url,
                    params={"page": page},
                )
            except requests.RequestException:
                break
            for item in payload.get("results", []):
                yield item

    def fetch_greenhouse_jobs(self, pages: int) -> Iterable[Dict]:
        """Yield jobs from Greenhouse boards API for configured board tokens."""
        for board in self._config.greenhouse_boards:
            endpoint = f"{self._config.greenhouse_jobs_base_url}/{board}/jobs"
            seen_ids: Set[str] = set()
            for page in range(1, pages + 1):
                try:
                    payload = self._get_json(
                        endpoint,
                        params={"content": "true", "page": page},
                    )
                except requests.RequestException:
                    # Skip inaccessible boards but continue scanning other sources.
                    break
                jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
                if not jobs:
                    break
                new_jobs = 0
                for item in jobs:
                    item_id = str(
                        item.get("id") or item.get("internal_job_id") or ""
                    ).strip()
                    dedupe_id = item_id or (item.get("absolute_url") or "")
                    if dedupe_id and dedupe_id in seen_ids:
                        continue
                    if dedupe_id:
                        seen_ids.add(dedupe_id)
                    enriched = dict(item)
                    enriched["__greenhouse_board"] = board
                    yield enriched
                    new_jobs += 1
                # Some boards ignore page and always return all jobs.
                if new_jobs == 0:
                    break

    def fetch_lever_jobs(self, pages: int) -> Iterable[Dict]:
        """Yield jobs from Lever postings API for configured site tokens."""
        limit = 50
        for site in self._config.lever_sites:
            endpoint = f"{self._config.lever_jobs_base_url}/{site}"
            seen_ids: Set[str] = set()
            for page in range(1, pages + 1):
                try:
                    payload = self._get_json(
                        endpoint,
                        params={
                            "skip": (page - 1) * limit,
                            "limit": limit,
                            "mode": "json",
                        },
                    )
                except requests.RequestException:
                    # Skip inaccessible sites but continue scanning other sources.
                    break
                jobs = payload if isinstance(payload, list) else []
                if not jobs:
                    break
                new_jobs = 0
                for item in jobs:
                    dedupe_id = str(item.get("id") or item.get("hostedUrl") or "").strip()
                    if dedupe_id and dedupe_id in seen_ids:
                        continue
                    if dedupe_id:
                        seen_ids.add(dedupe_id)
                    enriched = dict(item)
                    enriched["__lever_site"] = site
                    yield enriched
                    new_jobs += 1
                if new_jobs == 0 or len(jobs) < limit:
                    break

    def fetch_smartrecruiters_jobs(self, pages: int) -> Iterable[Dict]:
        """Yield jobs from SmartRecruiters postings API for configured companies."""
        limit = 100
        for company in self._config.smartrecruiters_companies:
            endpoint = f"{self._config.smartrecruiters_jobs_base_url}/{company}/postings"
            offset = 0
            seen_ids: Set[str] = set()
            for _ in range(pages):
                try:
                    payload = self._get_json(
                        endpoint,
                        params={"limit": limit, "offset": offset},
                    )
                except requests.RequestException:
                    break
                jobs = payload.get("content", []) if isinstance(payload, dict) else []
                if not jobs:
                    break
                for item in jobs:
                    dedupe_id = str(item.get("id") or "").strip()
                    if dedupe_id and dedupe_id in seen_ids:
                        continue
                    if dedupe_id:
                        seen_ids.add(dedupe_id)
                    enriched = dict(item)
                    enriched["__smartrecruiters_company"] = company
                    yield enriched
                offset += limit
                total_found = int(payload.get("totalFound", 0) or 0)
                if total_found and offset >= total_found:
                    break

    def fetch_workday_jobs(self, pages: int) -> Iterable[Dict]:
        """Yield jobs from Workday CXS endpoints for configured tenants/sites."""
        limit = 20
        for site in self._config.workday_sites:
            host = str(site.get("host", "")).strip()
            tenant = str(site.get("tenant", "")).strip()
            site_name = str(site.get("site", "")).strip()
            if not host or not tenant or not site_name:
                continue
            endpoint = self._config.workday_jobs_path.format(
                host=host, tenant=tenant, site=site_name
            )
            offset = 0
            seen_ids: Set[str] = set()
            for _ in range(pages):
                try:
                    payload = self._get_json(
                        endpoint,
                        params={"limit": limit, "offset": offset},
                    )
                except requests.RequestException:
                    break
                jobs = payload.get("jobPostings", []) if isinstance(payload, dict) else []
                if not jobs:
                    break
                for item in jobs:
                    dedupe_id = str(item.get("bulletFields") or item.get("title") or "")
                    dedupe_id = f"{tenant}:{site_name}:{dedupe_id}"
                    if dedupe_id in seen_ids:
                        continue
                    seen_ids.add(dedupe_id)
                    enriched = dict(item)
                    enriched["__workday_tenant"] = tenant
                    enriched["__workday_site"] = site_name
                    enriched["__workday_host"] = host
                    yield enriched
                offset += limit
                total_found = int(payload.get("total", 0) or 0)
                if total_found and offset >= total_found:
                    break

    def iter_normalized_jobs(self, pages: int) -> Iterable[Dict]:
        """Yield normalized jobs from all configured public sources."""
        for job in self.fetch_muse_jobs(pages=pages):
            normalized = self._normalize_muse_job(job)
            if normalized:
                yield normalized
        for job in self.fetch_greenhouse_jobs(pages=pages):
            normalized = self._normalize_greenhouse_job(job)
            if normalized:
                yield normalized
        for job in self.fetch_lever_jobs(pages=pages):
            normalized = self._normalize_lever_job(job)
            if normalized:
                yield normalized
        for job in self.fetch_smartrecruiters_jobs(pages=pages):
            normalized = self._normalize_smartrecruiters_job(job)
            if normalized:
                yield normalized
        for job in self.fetch_workday_jobs(pages=pages):
            normalized = self._normalize_workday_job(job)
            if normalized:
                yield normalized

    def scan(self, keywords: List[str], pages: int = 3) -> ScanSummary:
        """Run full scan and return matched job listings."""
        normalized_keywords = [k.strip() for k in keywords if k.strip()]
        if not normalized_keywords:
            normalized_keywords = list(self._config.keyword_list)

        enterprise_companies = self.load_enterprise_companies()
        scanned_jobs = 0
        enterprise_jobs = 0
        matches: List[JobMatch] = []

        for job in self.iter_normalized_jobs(pages=pages):
            scanned_jobs += 1

            company_name = (job.get("company_name") or "Unknown Company").strip()
            normalized_company = _normalize_name(company_name)
            if normalized_company not in enterprise_companies:
                continue
            enterprise_jobs += 1

            combined_text = _build_search_text(job=job)
            matched = _keyword_hits(combined_text, normalized_keywords)
            if not matched:
                continue

            matches.append(
                JobMatch(
                    company=company_name,
                    title=(job.get("name") or "Untitled Role").strip(),
                    location=(job.get("location") or "N/A").strip(),
                    url=(job.get("url") or "").strip(),
                    source=(job.get("source") or "Unknown").strip(),
                    matched_keywords=matched,
                )
            )

        return ScanSummary(
            scanned_jobs=scanned_jobs,
            enterprise_jobs=enterprise_jobs,
            matches=matches,
        )

    def _normalize_muse_job(self, job: Dict) -> Dict:
        company_name = ((job.get("company") or {}).get("name") or "").strip()
        if not company_name:
            return {}
        locations = job.get("locations") or []
        location_name = locations[0].get("name", "N/A") if locations else "N/A"
        return {
            "name": (job.get("name") or "").strip(),
            "description": (job.get("contents") or ""),
            "company_name": company_name,
            "location": location_name,
            "url": ((job.get("refs") or {}).get("landing_page") or "").strip(),
            "source": "The Muse",
        }

    def _normalize_greenhouse_job(self, job: Dict) -> Dict:
        board_token = str(job.get("__greenhouse_board") or "").strip()
        company_name = (
            job.get("company_name")
            or self._config.greenhouse_company_overrides.get(board_token, "")
            or _token_to_company_name(board_token)
        ).strip()
        if not company_name:
            return {}
        location_name = (
            ((job.get("location") or {}).get("name") or "N/A").strip() or "N/A"
        )
        metadata_entries = job.get("metadata") or []
        metadata_text = " ".join(
            str(entry.get("value", ""))
            for entry in metadata_entries
            if isinstance(entry, dict)
        )
        description = " ".join(
            [
                str(job.get("content", "")),
                metadata_text,
            ]
        )
        return {
            "name": (job.get("title") or job.get("name") or "").strip(),
            "description": description,
            "company_name": company_name,
            "location": location_name,
            "url": (job.get("absolute_url") or "").strip(),
            "source": "Greenhouse",
        }

    def _normalize_lever_job(self, job: Dict) -> Dict:
        site_token = str(job.get("__lever_site") or "").strip()
        company_name = (
            self._config.lever_company_overrides.get(site_token, "")
            or _token_to_company_name(site_token)
        ).strip()
        location_name = (
            ((job.get("categories") or {}).get("location") or "N/A").strip() or "N/A"
        )
        descriptions = [
            job.get("descriptionPlain", ""),
            job.get("description", ""),
            job.get("additionalPlain", ""),
            job.get("listsPlain", ""),
            ((job.get("categories") or {}).get("team") or ""),
        ]
        return {
            "name": (job.get("text") or "").strip(),
            "description": " ".join(str(text) for text in descriptions if text),
            "company_name": company_name,
            "location": location_name,
            "url": (job.get("hostedUrl") or "").strip(),
            "source": "Lever",
        }

    def _normalize_smartrecruiters_job(self, job: Dict) -> Dict:
        company_token = str(job.get("__smartrecruiters_company") or "").strip()
        company_name = (
            self._config.smartrecruiters_company_overrides.get(company_token, "")
            or _token_to_company_name(company_token)
        ).strip()
        if not company_name:
            return {}
        location = job.get("location") or {}
        location_name = " ".join(
            part
            for part in [
                str(location.get("city") or "").strip(),
                str(location.get("region") or "").strip(),
                str(location.get("country") or "").strip(),
            ]
            if part
        )
        location_name = location_name or "N/A"
        department = job.get("department") if isinstance(job.get("department"), dict) else {}
        employment = (
            job.get("typeOfEmployment")
            if isinstance(job.get("typeOfEmployment"), dict)
            else {}
        )
        description = " ".join(
            [
                str(job.get("name") or ""),
                str(department.get("label") or ""),
                str(employment.get("label") or ""),
            ]
        )
        return {
            "name": (job.get("name") or "").strip(),
            "description": description,
            "company_name": company_name,
            "location": location_name,
            "url": (job.get("ref") or "").strip(),
            "source": "SmartRecruiters",
        }

    def _normalize_workday_job(self, job: Dict) -> Dict:
        tenant = str(job.get("__workday_tenant") or "").strip()
        site_name = str(job.get("__workday_site") or "").strip()
        host = str(job.get("__workday_host") or "").strip()
        override_key = f"{tenant}/{site_name}"
        company_name = (
            self._config.workday_company_overrides.get(override_key, "")
            or _token_to_company_name(tenant)
        ).strip()
        if not company_name:
            return {}
        locations = job.get("locationsText") or []
        location_name = ", ".join(str(item).strip() for item in locations if str(item).strip())
        location_name = location_name or "N/A"
        external_path = (job.get("externalPath") or "").strip()
        posting_url = ""
        if external_path and host:
            posting_url = f"https://{host}{external_path}"
        description = " ".join(
            [
                str(job.get("title") or ""),
                str(job.get("postedOn") or ""),
                str(job.get("bulletFields") or ""),
            ]
        )
        return {
            "name": (job.get("title") or "").strip(),
            "description": description,
            "company_name": company_name,
            "location": location_name,
            "url": posting_url,
            "source": "Workday",
        }

    def _get_json(self, url: str, params: Dict[str, Any] | None = None) -> Any:
        """GET JSON payload from an endpoint."""
        response = requests.get(url, params=params, timeout=self._timeout_seconds)
        response.raise_for_status()
        return response.json()

    def _get_text(self, url: str) -> str:
        """GET plain-text content from an endpoint."""
        response = requests.get(url, timeout=self._timeout_seconds)
        response.raise_for_status()
        return response.text


def _parse_employee_count(raw: str) -> int:
    digits = "".join(ch for ch in raw if ch.isdigit())
    return int(digits) if digits else 0


def _normalize_name(name: str) -> str:
    normalized = name.lower().replace(",", "").replace(".", "")
    return " ".join(normalized.split())


def _build_search_text(job: Dict) -> str:
    contents = [
        job.get("name", ""),
        job.get("description", ""),
        job.get("company_name", ""),
        job.get("location", ""),
        job.get("source", ""),
    ]
    return " ".join(contents).lower()


def _keyword_hits(search_text: str, keywords: List[str]) -> List[str]:
    hits: List[str] = []
    lowered_text = search_text.lower()
    for keyword in keywords:
        if keyword.lower() in lowered_text:
            hits.append(keyword)
    return hits


def _token_to_company_name(token: str) -> str:
    cleaned = token.replace("-", " ").replace("_", " ").strip()
    return " ".join(part.capitalize() for part in cleaned.split())
