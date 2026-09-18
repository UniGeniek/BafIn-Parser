from typing import Optional

from .parsers.base_parser import BaseParser
from .parsers.bafin import BaFinParser
from .parsers.france_orias import OriasParser
from .parsers.spain_cnmv import CnmvParser

_REGISTRIES = {
    "DE": BaFinParser,
    "FR": OriasParser,
    "ES": CnmvParser,
}

def get_parser(country_code: str, use_playwright: bool = True) -> Optional[BaseParser]:
    parser_class = _REGISTRIES.get(country_code.upper())
    if parser_class:
        return parser_class(use_playwright=use_playwright)
    return None
