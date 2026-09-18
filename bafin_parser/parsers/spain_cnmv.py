from typing import Any, Optional
from playwright.async_api import async_playwright

from .base_parser import BaseParser
from ..models import CompanyRecord, ParseResult, SearchResult, ListParseResult
from ..config import settings
from ..logging import logger


class CnmvParser(BaseParser):
    def __init__(self, use_playwright: bool = True) -> None:
        self.use_playwright = use_playwright

    async def search_list(self, query: str = "", category_id: str = "", letter: str = "") -> ListParseResult:
        logger.info("cnmv_search_list_start", query=query)
        # Mock data for demonstration
        results = [
            SearchResult(
                name=query or "Banco Santander S.A.",
                registry_id="0049",
                category="Banco",
                detail_url="https://www.cnmv.es/portal/Consultas/Entidad"
            )
        ]
        return ListParseResult(success=True, results=results)

    async def get_details(self, detail_url: str) -> ParseResult:
        logger.info("cnmv_get_details_start", url=detail_url)
        
        record = CompanyRecord(
            name="Banco Santander, S.A.",
            registry_id="0049",
            registry_name="CNMV",
            country_code="ES",
            registriernummer="A81225730",
            lei="5493006QMFDDMYWIAM13",
            address="Paseo de Pereda, 9-12, 39004 Santander",
            activity="Entidad de Crédito",
            license_status="Registered",
            license_date="11/04/1986",
            source_url=detail_url,
            g2rs_eligible=True,
            g2rs_notes="Bank license (ES)"
        )
        return ParseResult(success=True, record=record, source="mock")

    async def search(self, query: str) -> ParseResult:
        list_res = await self.search_list(query=query)
        if list_res.success and list_res.results:
            return await self.get_details(list_res.results[0].detail_url)
        return ParseResult(success=False, error=list_res.error or "Not found")
