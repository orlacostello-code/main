"""FastAPI app exposing keyword scanner endpoints and simple web UI."""

from __future__ import annotations

from typing import List

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import AppConfig
from app.models import ScanRequest, ScanResponse
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
    """Handle HTML form submission and display scan result table."""
    keyword_list = _split_keywords(keywords) or list(config.keyword_list)
    try:
        summary = scanner.scan(keywords=keyword_list, pages=pages)
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
    return ScanResponse(
        scanned_jobs=summary.scanned_jobs,
        enterprise_jobs=summary.enterprise_jobs,
        keywords=keyword_list,
        matches=summary.matches,
    )


def _split_keywords(raw_keywords: str) -> List[str]:
    return [item.strip() for item in raw_keywords.split(",") if item.strip()]
