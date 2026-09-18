from __future__ import annotations

import abc

from .models import ParseResult
from .parser import BaFinParser


class BaseRegistryParser(abc.ABC):
    @abc.abstractmethod
    async def search(self, query: str) -> ParseResult:
        pass


class EBARegistryParser(BaseRegistryParser):
    async def search(self, query: str) -> ParseResult:
        raise NotImplementedError("EBA parser not yet implemented")


class ECBRegistryParser(BaseRegistryParser):
    async def search(self, query: str) -> ParseResult:
        raise NotImplementedError("ECB parser not yet implemented")


class RegistryFactory:
    @staticmethod
    def create(name: str) -> BaseRegistryParser:
        name = name.lower()
        if name == "bafin":
            # Assuming BaFinParser also implements search() with the same signature
            return BaFinParser()
        elif name == "eba":
            return EBARegistryParser()
        elif name == "ecb":
            return ECBRegistryParser()
        raise ValueError(f"Unsupported registry: {name}")
