from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class SearchResult:
    name: str = ""
    registry_id: str = ""
    category: str = ""
    detail_url: str = ""


@dataclass
class CompanyRecord:
    name: str = ""
    registry_id: str = ""
    registry_name: str = ""
    country_code: str = ""
    registriernummer: str = ""
    lei: str = ""
    address: str = ""
    activity: str = ""
    license_status: str = ""
    license_date: str = ""
    phone: str = ""
    email: str = ""
    source_url: str = ""
    notes: str = ""
    g2rs_eligible: bool = False
    g2rs_notes: str = ""
    parsed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ParseResult:
    success: bool
    record: Optional[CompanyRecord] = None
    error: Optional[str] = None
    source: str = ""


@dataclass
class ListParseResult:
    success: bool
    results: list[SearchResult] = field(default_factory=list)
    error: Optional[str] = None
