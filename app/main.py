"""FastAPI app exposing keyword scanner endpoints and interactive web UI."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import AppConfig
from app.models import CompanyResult, ScanRequest, ScanResponse
from app.scanner import JobScanner

app = FastAPI(title="Enterprise Job Keyword Scanner", version="0.1.0")
templates = Jinja2Templates(directory="templates")
config = AppConfig()
scanner = JobScanner(config=config)


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    """Render initial UI."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "default_keywords": ", ".join(config.keyword_list),
            "result": None,
            "error": None,
            "pages": 3,
            "keyword_input": "",
        },
    )


@app.post("/scan", response_class=HTMLResponse)
def scan_html(
    request: Request,
    keywords: str = Form(default=""),
    pages: int = Form(default=3),
) -> HTMLResponse:
    """Handle HTML form submission and display grouped scan results."""
    keyword_list = _split_keywords(keywords) or list(config.keyword_list)
    try:
        summary = scanner.scan(keywords=keyword_list, pages=pages)
        company_results = _build_company_results(summary.matches)
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "default_keywords": ", ".join(config.keyword_list),
                "result": {
                    "scanned_jobs": summary.scanned_jobs,
                    "enterprise_jobs": summary.enterprise_jobs,
                    "keywords": keyword_list,
                    "matches": summary.matches,
                    "company_results": company_results,
                },
                "error": None,
                "pages": pages,
                "keyword_input": keywords,
            },
        )
    except Exception as exc:  # broad-except is intentional for UI resilience
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "default_keywords": ", ".join(config.keyword_list),
                "result": None,
                "error": f"Scan failed: {exc}",
                "pages": pages,
                "keyword_input": keywords,
            },
        )


@app.post("/api/scan", response_model=ScanResponse)
def scan_api(payload: ScanRequest) -> ScanResponse:
    """Return JSON scan result for integration with other workflows."""
    keyword_list = payload.keywords or list(config.keyword_list)
    summary = scanner.scan(keywords=keyword_list, pages=payload.pages)
    company_results = _build_company_results(summary.matches)
    return ScanResponse(
        scanned_jobs=summary.scanned_jobs,
        enterprise_jobs=summary.enterprise_jobs,
        keywords=keyword_list,
        matches=summary.matches,
        companies=company_results,
    )


def _split_keywords(raw_keywords: str) -> List[str]:
    return [item.strip() for item in raw_keywords.split(",") if item.strip()]


def _build_company_results(matches: List) -> List[CompanyResult]:
    grouped: Dict[str, List] = defaultdict(list)
    for match in matches:
        grouped[match.company].append(match)

    company_results: List[CompanyResult] = []
    for company in sorted(grouped):
        jobs = grouped[company]
        keyword_hits = sorted(
            {keyword for job in jobs for keyword in job.matched_keywords}
        )
        sources = sorted({job.source for job in jobs})
        company_results.append(
            CompanyResult(
                company=company,
                match_count=len(jobs),
                keywords=keyword_hits,
                sources=sources,
                jobs=list(jobs),
            )
        )
    return company_results
