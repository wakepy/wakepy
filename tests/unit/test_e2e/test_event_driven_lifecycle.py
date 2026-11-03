"""Regression for the Android app's Flet callback dispatch pattern."""

from __future__ import annotations

import asyncio
from typing import Callable

import pytest

from wakepy import Mode, keep


@pytest.mark.usefixtures("empty_method_registry", "WAKEPY_FAKE_SUCCESS_eq_1")
class TestEventDrivenLifecycle:
    def test_sync_callbacks_update_status_through_async_dispatch(
        self, do_assert: Callable[[bool], None]
    ) -> None:
        updates: list[bool | None] = []

        def update_status(mode: Mode) -> None:
            updates.append(mode.active)

        mode = keep.presenting(after_enter=update_status, after_exit=update_status)

        def enable_lock() -> None:
            if not mode.active:
                mode.enter()

        def disable_lock() -> None:
            mode.exit()

        async def dispatch(handler: Callable[[], None]) -> None:
            # Flet calls sync handlers on the event-loop thread, then awaits
            # its after-event UI flush. No async wakepy API is involved.
            handler()
            await asyncio.sleep(0)

        async def run() -> None:
            await asyncio.create_task(dispatch(disable_lock))
            do_assert(updates == [None])
            await asyncio.create_task(dispatch(enable_lock))
            do_assert(mode.active is True)
            do_assert(updates == [None, True])
            await asyncio.create_task(dispatch(disable_lock))
            do_assert(mode.active is None)
            do_assert(updates == [None, True, None])

        try:
            asyncio.run(run())
        finally:
            mode.exit()
