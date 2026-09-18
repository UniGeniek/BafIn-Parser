from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from environs import Env

env = Env()
env.read_env()


@dataclass(frozen=True)
class Settings:
    bafin_base_url: str = env.str("BAFIN_BASE_URL", default="https://portal.mvp.bafin.de/database/InstInfo/")
    telegram_token: str = env.str("TELEGRAM_TOKEN", default="")
    proxy_list: list[str] = field(default_factory=lambda: env.list("PROXY_LIST", default=[]))
    captcha_api_key: str = env.str("CAPTCHA_API_KEY", default="")
    log_level: str = env.str("LOG_LEVEL", default="INFO")
    cache_ttl_seconds: int = env.int("CACHE_TTL_SECONDS", default=86400)
    request_delay_seconds: int = env.int("REQUEST_DELAY_SECONDS", default=3)
    workspace_dir: Path = Path(__file__).resolve().parent.parent
    playwright_headless: bool = env.bool("PLAYWRIGHT_HEADLESS", default=True)
    playwright_timeout: int = env.int("PLAYWRIGHT_TIMEOUT", default=30000)

settings = Settings()
