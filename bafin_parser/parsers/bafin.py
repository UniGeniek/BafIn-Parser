from __future__ import annotations

import asyncio
import re
from typing import Any, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError

from ..anti_bot import AntiBotConfig
from ..config import settings
from ..logging import logger
from ..models import CompanyRecord, ParseResult, SearchResult, ListParseResult
from .base_parser import BaseParser


class BaFinParser(BaseParser):
    def __init__(self, use_playwright: bool = True) -> None:
        self.use_playwright = use_playwright
        self.antibot = AntiBotConfig()

    async def search_list(self, query: str = "", category_id: str = "", letter: str = "") -> ListParseResult:
        if not self.use_playwright:
            return ListParseResult(success=True, results=[SearchResult(name="Mock GmbH", registry_id="123456", category="Test", detail_url="mock")])

        logger.info("parser_search_list_start", query=query, category=category_id, letter=letter)
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=settings.playwright_headless)
                context = await self.antibot.setup_context(browser)
                page = await context.new_page()

                search_url = f"{settings.bafin_base_url.rstrip('/')}/sucheForm.do"
                
                if letter:
                    url = f"{search_url}?sucheButtonInstitut=Suche&institutName={letter}"
                    if category_id:
                        url += f"&kategorieId={category_id}"
                    await page.goto(url, timeout=settings.playwright_timeout)
                else:
                    await page.goto(search_url, timeout=settings.playwright_timeout)
                    await self.antibot.wait_like_human()
                    await self.antibot.solve_captcha_if_present(page)

                    if query.isdigit() or query.startswith("101"):
                        await page.fill("input#institutId", query)
                    elif query:
                        await page.fill("input#institutName", query)
                        
                    if category_id:
                        await page.select_option("select#institutKategorie", category_id)
                    
                    await self.antibot.wait_like_human()
                    await page.click("input#sucheButtonInstitut")
                
                try:
                    await page.wait_for_selector("table#institut, div.error", timeout=10000)
                except PlaywrightTimeoutError:
                    await browser.close()
                    return ListParseResult(success=False, error="Timeout waiting for search results")

                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")
                
                results_table = soup.find("table", id="institut")
                if not results_table:
                    await browser.close()
                    return ListParseResult(success=True, results=[], error="No results found")

                results = []
                tbody = results_table.find("tbody")
                if tbody:
                    for row in tbody.find_all("tr"):
                        tds = row.find_all("td")
                        if len(tds) >= 2:
                            link = tds[0].find("a")
                            if link and "href" in link.attrs:
                                name = link.get_text(strip=True)
                                href = link["href"]
                                detail_url = urljoin(search_url, href)
                                
                                # Extract BaFin ID from href (e.g. institutId=121907)
                                bafin_id = ""
                                match = re.search(r"institutId=(\d+)", href)
                                if match:
                                    bafin_id = match.group(1)
                                    
                                cat = tds[1].get_text(strip=True)
                                results.append(SearchResult(name=name, registry_id=bafin_id, category=cat, detail_url=detail_url))
                
                await browser.close()
                return ListParseResult(success=True, results=results)
        except Exception as e:
            logger.exception("parser_search_list_error", error=str(e))
            return ListParseResult(success=False, error=str(e))

    async def get_details(self, detail_url: str) -> ParseResult:
        if not self.use_playwright:
            return ParseResult(success=True, record=self._build_sample_record("Mock"))
            
        logger.info("parser_get_details_start", url=detail_url)
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=settings.playwright_headless)
                context = await self.antibot.setup_context(browser)
                page = await context.new_page()

                await page.goto(detail_url, timeout=settings.playwright_timeout)
                await self.antibot.wait_like_human()
                
                detail_html = await page.content()
                await browser.close()
                
                raw_data = parse_detail_html(detail_html)
                raw_data["source_url"] = detail_url
                record = normalize_company_data(raw_data)
                
                try:
                    from .g2rs_analyzer import analyze_g2rs_eligibility
                    is_eligible, notes = analyze_g2rs_eligibility(record.license_status, record.activity)
                    record.g2rs_eligible = is_eligible
                    record.g2rs_notes = notes
                except Exception:
                    pass
                
                return ParseResult(success=True, record=record, source="playwright")
        except Exception as e:
            logger.exception("parser_get_details_error", error=str(e))
            return ParseResult(success=False, error=str(e))

    async def search(self, query: str) -> ParseResult:
        list_res = await self.search_list(query=query)
        if list_res.success and list_res.results:
            return await self.get_details(list_res.results[0].detail_url)
        return ParseResult(success=False, error=list_res.error or "Not found")

    def _build_sample_record(self, query: str) -> CompanyRecord:
        return CompanyRecord(
            name=query.strip() or "Beispielgesellschaft GmbH",
            registry_id="BAFIN-001",
            registry_name="BaFin",
            country_code="DE",
            registriernummer="123456",
            lei="5493001KQH4K0MHSZG76",
            address="Berlin, Deutschland",
            activity="Erlaubnis nach KWG",
            license_status="aktiv",
            license_date="01.01.2024",
            phone="",
            email="",
            source_url=settings.bafin_base_url,
            notes="",
        )


def parse_detail_html(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    data = {}
    
    title_h2 = soup.find("h2", string=re.compile("Unternehmen", re.I))
    if title_h2:
        name_p = title_h2.find_next_sibling("p")
        if name_p and name_p.find("strong"):
            data["name"] = name_p.get_text(strip=True)
            
            gattung_dl = name_p.find_next_sibling("dl", class_="docData")
            if gattung_dl:
                address_p = gattung_dl.find_next_sibling("p")
                if address_p:
                    for br in address_p.find_all("br"):
                        br.replace_with(", ")
                    data["address"] = address_p.get_text(strip=True)
    
    for dt in soup.find_all("dt"):
        text = dt.get_text(strip=True).lower()
        dd = dt.find_next_sibling("dd")
        if not dd:
            continue
        val = dd.get_text(strip=True).strip("- ")
        
        if "bafin-id" in text:
            data["bafin_id"] = val
        elif "bak nr" in text:
            data["bak_nr"] = val
        elif "reg nr" in text:
            data["registernummer"] = val
        elif "lei" in text:
            data["lei"] = val

    erlaubnis_table = soup.find("table", id="erlaubnis")
    activities = []
    if erlaubnis_table:
        tbody = erlaubnis_table.find("tbody")
        if tbody:
            for tr in tbody.find_all("tr"):
                tds = tr.find_all("td")
                if len(tds) >= 2:
                    act_name = tds[0].get_text(strip=True)
                    date_val = tds[1].get_text(strip=True)
                    end_val = tds[2].get_text(strip=True) if len(tds) > 2 else ""
                    status = "aktiv" if not end_val else "erloschen"
                    activities.append(act_name)
                    if "license_date" not in data or not data["license_date"]:
                        data["license_date"] = date_val
                        data["license_status"] = status
    
    if activities:
        data["activity"] = ", ".join(activities[:3]) + ("..." if len(activities) > 3 else "")

    return data


def clean_text(value: Optional[Any]) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_company_data(raw: dict[str, Any]) -> CompanyRecord:
    name = clean_text(raw.get("name"))
    bafin_id = clean_text(raw.get("bafin_id") or raw.get("bak_nr"))
    registriernummer = clean_text(raw.get("registernummer"))
    lei = clean_text(raw.get("lei"))
    address = clean_text(raw.get("address"))
    activity = clean_text(raw.get("activity"))
    license_status = clean_text(raw.get("license_status") or "aktiv")
    license_date = clean_text(raw.get("license_date"))
    source_url = clean_text(raw.get("source_url") or settings.bafin_base_url)
    
    return CompanyRecord(
        name=name,
        registry_id=bafin_id,
        registry_name="BaFin",
        country_code="DE",
        registriernummer=registriernummer,
        lei=lei,
        address=address,
        activity=activity,
        license_status=license_status,
        license_date=license_date,
        phone="",
        email="",
        source_url=source_url,
        notes="",
    )
