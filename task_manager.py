# -*- coding: utf-8 -*-
"""Async task manager with delayed (debounced) cleanup.

This project is asyncio-based (Telethon). The manager below provides a
concurrency-safe way to:

1) Increment/decrement the number of active tasks per chat.
2) When a chat becomes idle (active task count reaches 0), schedule a delayed
   cleanup operation.
3) If a new task starts during the delay window, the pending cleanup is
   cancelled (debounce/double-check semantics).

The cleanup callback is typically used to clear the "recent status" area on the
dashboard and/or to remove terminal task rows after a short grace period.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Awaitable, Callable, DefaultDict, Dict, Optional

logger = logging.getLogger(__name__)


RefreshCallback = Callable[[int, bool], Awaitable[None]]


class TaskManager:
    """Track active tasks per chat and run a delayed cleanup when idle.

    Parameters
    ----------
    refresh_ui:
        Async callback: await refresh_ui(chat_id, is_cleanup)

        - is_cleanup=False: a normal refresh can be performed by caller code.
          (In TeleFlux we already refresh on state changes, so this is optional.)
        - is_cleanup=True: indicates this is the delayed cleanup operation.
    cleanup_delay_s:
        Seconds to wait after the chat becomes idle before performing cleanup.
    """

    def __init__(self, refresh_ui: Optional[RefreshCallback] = None, *, cleanup_delay_s: float = 5.0):
        self._lock = asyncio.Lock()
        self._active: DefaultDict[int, int] = defaultdict(int)
        self._cleanup_tasks: Dict[int, asyncio.Task] = {}

        self.refresh_ui: Optional[RefreshCallback] = refresh_ui
        self.cleanup_delay_s = float(cleanup_delay_s)

    async def task_started(self, chat_id: int) -> None:
        """Must be called before/when a task is scheduled for a chat."""
        async with self._lock:
            self._active[chat_id] += 1
            cur = self._active[chat_id]
            # New work arrived: cancel any pending cleanup.
            t = self._cleanup_tasks.pop(chat_id, None)
            if t and not t.done():
                t.cancel()
            logger.info("Task started. chat_id=%s active=%s", chat_id, cur)

    async def task_finished(self, chat_id: int) -> int:
        """Must be called when a task reaches a terminal state.

        Returns
        -------
        int
            Remaining active task count for this chat.
        """
        async with self._lock:
            self._active[chat_id] -= 1
            if self._active[chat_id] < 0:
                self._active[chat_id] = 0
            remaining = self._active[chat_id]
            logger.info("Task finished. chat_id=%s remaining=%s", chat_id, remaining)

            # Schedule delayed cleanup only when chat becomes idle.
            if remaining == 0:
                # Replace any pending task (shouldn't exist if counts are correct).
                old = self._cleanup_tasks.pop(chat_id, None)
                if old and not old.done():
                    old.cancel()
                self._cleanup_tasks[chat_id] = asyncio.create_task(self._delayed_cleanup(chat_id))

            return remaining

    async def _delayed_cleanup(self, chat_id: int) -> None:
        try:
            await asyncio.sleep(self.cleanup_delay_s)

            async with self._lock:
                # Double-check: only cleanup if still idle.
                if self._active.get(chat_id, 0) != 0:
                    logger.info(
                        "Cleanup skipped (new tasks arrived). chat_id=%s active=%s",
                        chat_id,
                        self._active.get(chat_id, 0),
                    )
                    return

            logger.info("Idle for %ss. Running cleanup. chat_id=%s", self.cleanup_delay_s, chat_id)
            if self.refresh_ui is not None:
                await self.refresh_ui(chat_id, True)
        except asyncio.CancelledError:
            # Expected when new tasks arrive during the debounce window.
            return
        finally:
            # Remove bookkeeping entry if it still points to this task.
            cur = asyncio.current_task()
            async with self._lock:
                if self._cleanup_tasks.get(chat_id) is cur:
                    self._cleanup_tasks.pop(chat_id, None)
