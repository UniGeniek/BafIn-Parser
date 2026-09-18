from __future__ import annotations

import asyncio
import random
from typing import Any, Optional

from fake_useragent import UserAgent
from playwright.async_api import Browser, BrowserContext

from .config import settings
from .logging import logger

class AntiBotConfig:
    def __init__(self) -> None:
        self.user_agent = UserAgent().random
        self.proxies = settings.proxy_list

    async def setup_context(self, browser: Browser) -> BrowserContext:
        """Sets up a stealthy Playwright browser context."""
        context_args: dict[str, Any] = {
            "user_agent": self.user_agent,
            "viewport": {"width": 1920, "height": 1080},
            "locale": "de-DE",
            "timezone_id": "Europe/Berlin",
            "extra_http_headers": {
                "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        }
        
        if self.proxies:
            proxy = random.choice(self.proxies)
            context_args["proxy"] = {"server": proxy}
            logger.debug("anti_bot_proxy_selected", proxy=proxy)
            
        context = await browser.new_context(**context_args)
        
        # Additional stealth evasion could go here (e.g. init scripts)
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        return context

    async def wait_like_human(self) -> None:
        """Simulate human reading time or typing delay."""
        delay = random.uniform(1.0, 3.5)
        await asyncio.sleep(delay)

    async def solve_captcha_if_present(self, page) -> bool:
        """Placeholder for 2captcha/AntiCaptcha integration."""
        # For BaFin, they usually use generic challenge or custom captcha.
        # This function would detect the captcha, send it to a 3rd party API,
        # wait for the result, and inject it back into the page.
        if settings.captcha_api_key:
            # Check for captcha elements on the page
            pass
        return False
