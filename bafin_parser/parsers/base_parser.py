from abc import ABC, abstractmethod
from typing import Optional

from ..models import ListParseResult, ParseResult


class BaseParser(ABC):
    @abstractmethod
    async def search_list(self, query: str = "", category_id: str = "", letter: str = "") -> ListParseResult:
        pass

    @abstractmethod
    async def get_details(self, detail_url: str) -> ParseResult:
        pass

    @abstractmethod
    async def search(self, query: str) -> ParseResult:
        pass
