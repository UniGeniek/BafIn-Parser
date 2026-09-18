from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from bafin_parser.cache import CacheStore
from bafin_parser.logging import configure_logging, logger
from bafin_parser.models import CompanyRecord
from bafin_parser.parser_factory import get_parser
from bafin_parser.ss04_generator import render_ss04_document


async def main() -> None:
    parser = argparse.ArgumentParser(description="BaFin company data parser")
    parser.add_argument("--company", help="Search by company name")
    parser.add_argument("--id", help="Search by registry ID")
    parser.add_argument("--country", default="DE", help="Country code (e.g. DE, FR)")
    parser.add_argument("--output-dir", default="outputs", help="Where to store generated documents")
    args = parser.parse_args()

    configure_logging()
    cache = CacheStore()
    query = args.company or args.id or ""
    cached = cache.get(query) if query else None
    if cached:
        logger.info("cache_hit", query=query)
        record = cached
    else:
        parser_client = get_parser(args.country)
        if not parser_client:
            print(f"No parser found for country {args.country}, damn it.")
            return
        result = await parser_client.search(query)
        if not result.success or not result.record:
            print("Nothing found in the BaFin registry.")
            return
        record = result.record.__dict__
        cache.set(query, record)

    output_dir = Path(args.output_dir)
    record_obj = CompanyRecord(**record) if isinstance(record, dict) else record
    pdf_path, html_path = await render_ss04_document(record_obj, output_dir=output_dir)
    print(f"PDF: {pdf_path}")
    print(f"HTML: {html_path}")


if __name__ == "__main__":
    asyncio.run(main())
