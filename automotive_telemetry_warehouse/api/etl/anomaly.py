"""Anomaly detection LISTEN/NOTIFY hook — PLACEHOLDER stub for Task 6.

Replaced by Task 8's real implementation.
"""

from __future__ import annotations

import asyncio


class _AnomalyListener:
    """Minimal no-op stand-in for the real LISTEN/NOTIFY-driven anomaly listener.

    `start()` schedules a no-op coroutine as a cancellable asyncio.Task so the
    FastAPI lifespan context manager has something awaitable-cancellable to
    hold onto; `stop()` cancels it cleanly. Task 8 replaces this with the real
    `etl_complete` notification listener and anomaly-detection logic.
    """

    async def _run(self) -> None:
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            pass

    def start(self) -> asyncio.Task:
        return asyncio.create_task(self._run())

    async def stop(self, task: asyncio.Task) -> None:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


anomaly_listener = _AnomalyListener()
