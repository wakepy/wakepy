"""Same-mode contention and failed-entry cleanup across real threads."""

from __future__ import annotations

import contextlib
import threading
import typing
from collections.abc import Generator
from dataclasses import replace

import pytest

from wakepy import Mode, modecount
from wakepy.core.mode import ReentrantGuard

if typing.TYPE_CHECKING:
    from typing import Callable

    from wakepy import ModeHook

    LifecycleFactory = Callable[
        [dict[str, BaseException], bool], tuple[Mode, list[str]]
    ]


class CountingGuard(ReentrantGuard):
    def __init__(self) -> None:
        super().__init__()
        self.acquisitions = 0

    @contextlib.contextmanager
    def held(self) -> Generator[None, None, None]:
        self.acquisitions += 1
        with super().held():
            yield


class TestSerializedLifecycle:
    @pytest.mark.parametrize(
        "hook_name, success",
        [
            ("before_enter", True),
            ("on_success", True),
            ("on_fail", False),
            ("after_enter", True),
            ("after_enter", False),
        ],
    )
    def test_failed_context_entry_uses_one_lock_acquisition(
        self, lifecycle_case: LifecycleFactory, hook_name: str, success: bool
    ) -> None:
        failure = ValueError(hook_name)
        mode, events = lifecycle_case({hook_name: failure}, success)
        guard = CountingGuard()
        mode._guard = guard
        with pytest.raises(ValueError) as caught:
            with mode:
                raise AssertionError("Failed entry must skip the body")
        assert caught.value is failure
        assert guard.acquisitions == 1
        assert events[-1] == "after_exit"
        assert mode.active is None
        assert not guard._lock.locked()

    @pytest.mark.parametrize(
        "blocking_hook", ["before_enter", "after_enter", "before_exit", "after_exit"]
    )
    @pytest.mark.parametrize("second_operation", ["enter", "exit"])
    def test_same_mode_calls_wait_for_hooks(
        self,
        lifecycle_case: LifecycleFactory,
        blocking_hook: str,
        second_operation: str,
    ) -> None:
        template, events = lifecycle_case({}, True)
        original_hook = typing.cast(
            "ModeHook", getattr(template._init_params, blocking_hook)
        )
        blocked = threading.Event()
        release = threading.Event()
        attempted = threading.Event()
        completed = threading.Event()
        errors: list[BaseException] = []

        def blocking_callback(mode: Mode) -> None:
            original_hook(mode)
            if threading.current_thread() is first:
                blocked.set()
                if not release.wait(timeout=5):
                    raise TimeoutError("Test did not release lifecycle hook")

        mode = Mode(
            replace(
                template._init_params,
                before_enter=(
                    blocking_callback
                    if blocking_hook == "before_enter"
                    else template._init_params.before_enter
                ),
                after_enter=(
                    blocking_callback
                    if blocking_hook == "after_enter"
                    else template._init_params.after_enter
                ),
                before_exit=(
                    blocking_callback
                    if blocking_hook == "before_exit"
                    else template._init_params.before_exit
                ),
                after_exit=(
                    blocking_callback
                    if blocking_hook == "after_exit"
                    else template._init_params.after_exit
                ),
            )
        )
        first_is_enter = blocking_hook.endswith("enter")
        if not first_is_enter:
            mode.enter()
            events.clear()

        def first_worker() -> None:
            try:
                if first_is_enter:
                    mode.enter()
                else:
                    mode.exit()
            except BaseException as error:
                errors.append(error)

        def second_worker() -> None:
            attempted.set()
            try:
                if second_operation == "enter":
                    mode.enter(if_already_entered="pass")
                else:
                    mode.exit()
            except BaseException as error:
                errors.append(error)
            finally:
                completed.set()

        first = threading.Thread(target=first_worker)
        second = threading.Thread(target=second_worker)
        first.start()
        try:
            assert blocked.wait(timeout=5)
            second.start()
            assert attempted.wait(timeout=5)
            assert not completed.wait(timeout=0.05)
        finally:
            release.set()
            first.join(timeout=5)
            if second.ident is not None:
                second.join(timeout=5)
        try:
            assert errors == []
            assert not first.is_alive()
            assert not second.is_alive()
            entry = ["before_enter", "activate", "on_success", "after_enter"]
            exit_ = ["before_exit", "deactivate", "after_exit"]
            expected = entry if first_is_enter else exit_
            if second_operation == "enter" and not first_is_enter:
                expected += entry
            elif second_operation == "exit":
                expected += exit_ if first_is_enter else ["before_exit", "after_exit"]
            assert events == expected
            assert completed.is_set()
        finally:
            mode.exit()
        assert modecount() == 0

    def test_failed_context_entry_cleans_up_before_waiting_enter(
        self, lifecycle_case: LifecycleFactory
    ) -> None:
        failure = ValueError("after_enter")
        failures: dict[str, BaseException] = {"after_enter": failure}
        template, events = lifecycle_case(failures, True)
        cleanup_started = threading.Event()
        release = threading.Event()
        attempted = threading.Event()
        completed = threading.Event()
        first_errors: list[BaseException] = []
        second_errors: list[BaseException] = []
        original_hook = template._init_params.before_exit

        def before_exit(mode: Mode) -> None:
            if original_hook is not None:
                original_hook(mode)
            if threading.current_thread() is first:
                failures.clear()
                cleanup_started.set()
                if not release.wait(timeout=5):
                    raise TimeoutError("Test did not release cleanup")

        mode = Mode(replace(template._init_params, before_exit=before_exit))

        def first_worker() -> None:
            try:
                with mode:
                    raise AssertionError("Failed entry must skip the body")
            except BaseException as error:
                first_errors.append(error)

        def second_worker() -> None:
            attempted.set()
            try:
                mode.enter()
            except BaseException as error:
                second_errors.append(error)
            finally:
                completed.set()

        first = threading.Thread(target=first_worker)
        second = threading.Thread(target=second_worker)
        first.start()
        try:
            assert cleanup_started.wait(timeout=5)
            second.start()
            assert attempted.wait(timeout=5)
            assert not completed.wait(timeout=0.05)
        finally:
            release.set()
            first.join(timeout=5)
            if second.ident is not None:
                second.join(timeout=5)
        try:
            assert not first.is_alive()
            assert not second.is_alive()
            assert first_errors == [failure]
            assert second_errors == []
            assert events == [
                "before_enter",
                "activate",
                "on_success",
                "after_enter",
                "before_exit",
                "deactivate",
                "after_exit",
                "before_enter",
                "activate",
                "on_success",
                "after_enter",
            ]
            assert mode.active is True
            assert modecount() == 1
        finally:
            mode.exit()
