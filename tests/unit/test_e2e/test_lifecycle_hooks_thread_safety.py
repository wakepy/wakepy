"""Thread safety tests for lifecycle hooks."""

from __future__ import annotations

import threading
import typing

from wakepy import Mode, keep

if typing.TYPE_CHECKING:
    pass


class TestThreadSafety:
    """Test lifecycle hooks are thread-safe."""

    def test_hooks_independent_per_thread(
        self,
        empty_method_registry: None,
        WAKEPY_FAKE_SUCCESS_eq_1: None,
    ) -> None:
        """Each thread gets independent hook invocations."""
        thread_events: dict[int, list[str]] = {}
        lock = threading.Lock()
        ready_barrier = threading.Barrier(4)
        exit_event = threading.Event()
        errors: list[BaseException] = []

        def before_enter_cb(mode: Mode) -> None:
            thread_id = threading.get_ident()
            with lock:
                if thread_id not in thread_events:
                    thread_events[thread_id] = []
                thread_events[thread_id].append("before_enter")

        @keep.running(before_enter=before_enter_cb)
        def worker() -> None:
            thread_id = threading.get_ident()
            with lock:
                thread_events[thread_id].append("body")
            ready_barrier.wait(timeout=5)
            exit_event.wait(timeout=5)

        def run_worker() -> None:
            try:
                worker()
            except BaseException as error:
                errors.append(error)

        threads = []
        for _ in range(3):
            thread = threading.Thread(target=run_worker)
            thread.start()
            threads.append(thread)

        try:
            ready_barrier.wait(timeout=5)
        finally:
            exit_event.set()
            for thread in threads:
                thread.join(timeout=5)

        # Each thread should have its own events
        assert len(thread_events) == 3
        assert errors == []
        assert all(not thread.is_alive() for thread in threads)
        for thread_id, events in thread_events.items():
            assert events == ["before_enter", "body"]
