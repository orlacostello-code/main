"""Data models exchanged between scanner, API, and UI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from pydantic import BaseModel, Field


@dataclass
class JobMatch:
    """Single matched job posting."""

    company: str
    title: str
    location: str
    url: str
    source: str = "The Muse"
    matched_keywords: List[str] = field(default_factory=list)


@dataclass
class ScanSummary:
    """Aggregate scanner output before API serialization."""

    scanned_jobs: int
    enterprise_jobs: int
    matches: List[JobMatch] = field(default_factory=list)


@dataclass
class CompanyResult:
    """Grouped result for a single company and its matched jobs."""

    company: str
    match_count: int
    keywords: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    jobs: List[JobMatch] = field(default_factory=list)


class ScanRequest(BaseModel):
    """Request payload used by API/UI scan endpoint."""

    keywords: List[str] = Field(default_factory=list)
    pages: int = Field(default=3, ge=1, le=20)


class ScanResponse(BaseModel):
    """Response payload sent to API/UI clients."""

    scanned_jobs: int
    enterprise_jobs: int
    keywords: List[str]
    matches: List[JobMatch]
    companies: List[CompanyResult] = Field(default_factory=list)
