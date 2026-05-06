"""Background cleanup of old uploaded files."""
from __future__ import annotations
import asyncio
import time
from pathlib import Path
from typing import Optional

DEFAULT_MAX_AGE_SECONDS = 6 * 60 * 60  # 6 hours
DEFAULT_INTERVAL_SECONDS = 30 * 60     # every 30 minutes


class CleanupTask:
    def __init__(self, storage_dir: Path, max_age_s: int = DEFAULT_MAX_AGE_SECONDS, interval_s: int = DEFAULT_INTERVAL_SECONDS):
        self.storage_dir = storage_dir
        self.max_age_s = max_age_s
        self.interval_s = interval_s
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()

    async def _loop(self):
        while not self._stop.is_set():
            try:
                self.run_once()
            except Exception:
                pass
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.interval_s)
            except asyncio.TimeoutError:
                continue

    def run_once(self) -> int:
        if not self.storage_dir.exists():
            return 0
        now = time.time()
        deleted = 0
        for p in self.storage_dir.iterdir():
            if not p.is_file():
                continue
            try:
                age = now - p.stat().st_mtime
                if age > self.max_age_s:
                    p.unlink()
                    deleted += 1
            except OSError:
                continue
        return deleted

    def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            try:
                await self._task
            except asyncio.CancelledError:
                pass
