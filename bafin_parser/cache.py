from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Optional

from .config import settings


class CacheStore:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or settings.workspace_dir / "cache.sqlite3"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                )
                """
            )
            conn.commit()

    def get(self, key: str) -> Optional[dict]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT value, created_at FROM cache WHERE key = ?", (key,)).fetchone()
        if not row:
            return None
        value, created_at = row
        if time.time() - created_at > settings.cache_ttl_seconds:
            self.delete(key)
            return None
        return json.loads(value)

    def set(self, key: str, value: dict) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO cache(key, value, created_at) VALUES(?, ?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value, created_at = excluded.created_at",
                (key, json.dumps(value), int(time.time())),
            )
            conn.commit()

    def delete(self, key: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            conn.commit()
