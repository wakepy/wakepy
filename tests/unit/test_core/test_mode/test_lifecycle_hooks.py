"""Tests for lifecycle hooks functionality in Mode class.

Tests all 5 lifecycle hooks:
- before_enter
- after_enter
- before_exit
- after_exit
- on_success
"""

from __future__ import annotations

import threading
import typing

import pytest

from wakepy import (
    ActivationError,
    ActivationWarning,
    Mode,
    current_mode,
    keep,
    modecount,
)
from wakepy.core.constants import ModeName
from wakepy.core.mode import ModeExit, create_mode_params
from wakepy.methods._testing import WakepyFakeSuccess

if typing.TYPE_CHECKING:
    from typing import List

    from wakepy import ActivationResult
    from wakepy.core.mode import OnFail


class HookTestError(Exception):
    pass


class TestLifecycleFailureCleanup:
    @pytest.mark.parametrize("syntax", ["explicit", "context", "decorator"])
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
    @pytest.mark.parametrize(
        "error_type", [HookTestError, KeyboardInterrupt, SystemExit, ModeExit]
    )
    def test_enter_failure(
        self,
        lifecycle_case: typing.Callable[
            [dict[str, BaseException], bool], tuple[Mode, list[str]]
        ],
        syntax: str,
        hook_name: str,
        success: bool,
        error_type: type[BaseException],
        do_assert: typing.Callable[[bool], None],
        hook_modes: list[Mode],
    ) -> None:
        error = error_type("enter hook")
        mode, events = lifecycle_case({hook_name: error}, success)
        outer, _ = lifecycle_case({}, True)

        def body() -> None:
            events.append("body")

        with outer:
            with pytest.raises(error_type) as caught:
                if syntax == "explicit":
                    try:
                        mode.enter()
                    finally:
                        # Explicit entry leaves partial state to callers.
                        do_assert(mode._entered is (hook_name != "before_enter"))
                        do_assert(
                            mode.active
                            is (None if hook_name == "before_enter" else success)
                        )
                        mode.exit()
                elif syntax == "context":
                    with mode:
                        body()
                else:
                    mode(body)()

            do_assert(caught.value is error)
            do_assert(current_mode() is outer)
            do_assert(modecount() == 1)

        entry_events = ["before_enter"]
        if hook_name != "before_enter":
            if success:
                entry_events.append("activate")
            entry_events.append("on_success" if success else "on_fail")
        if hook_name == "after_enter":
            entry_events.append("after_enter")
        exit_events = ["before_exit"]
        if success and hook_name != "before_enter":
            exit_events.append("deactivate")
        exit_events.append("after_exit")
        do_assert(events == entry_events + exit_events)
        actual_mode = hook_modes[-1]
        do_assert((actual_mode is mode) is (syntax != "decorator"))
        do_assert(actual_mode.active is None)
        do_assert(actual_mode._entered is False)
        do_assert(not actual_mode._guard._lock.locked())
        do_assert(modecount() == 0)

    @pytest.mark.parametrize("syntax", ["explicit", "context", "decorator"])
    @pytest.mark.parametrize("hook_name", ["before_exit", "after_exit", "deactivate"])
    @pytest.mark.parametrize(
        "error_type", [HookTestError, KeyboardInterrupt, SystemExit, ModeExit]
    )
    def test_exit_failure(
        self,
        lifecycle_case: typing.Callable[
            [dict[str, BaseException], bool], tuple[Mode, list[str]]
        ],
        syntax: str,
        hook_name: str,
        error_type: type[BaseException],
        hook_modes: list[Mode],
    ) -> None:
        error = error_type("exit hook")
        mode, events = lifecycle_case({hook_name: error}, True)
        outer, _ = lifecycle_case({}, True)

        def body() -> None:
            events.append("body")

        with outer:
            wrapped = hook_name == "deactivate" and isinstance(error, Exception)
            with pytest.raises(RuntimeError if wrapped else error_type) as caught:
                if syntax == "explicit":
                    mode.enter()
                    body()
                    mode.exit()
                elif syntax == "context":
                    with mode:
                        body()
                else:
                    mode(body)()
            assert (caught.value.__context__ if wrapped else caught.value) is error
            assert current_mode() is outer
            assert modecount() == 1

        assert events == [
            "before_enter",
            "activate",
            "on_success",
            "after_enter",
            "body",
            "before_exit",
            "deactivate",
            "after_exit",
        ]
        actual_mode = hook_modes[-1]
        assert (actual_mode is mode) is (syntax != "decorator")
        assert actual_mode.active is None
        assert actual_mode._entered is False
        assert not actual_mode._guard._lock.locked()

    @pytest.mark.parametrize("entered", [False, True])
    def test_repeated_exit_calls_hooks_without_repeated_deactivation(
        self,
        lifecycle_case: typing.Callable[
            [dict[str, BaseException], bool], tuple[Mode, list[str]]
        ],
        entered: bool,
    ) -> None:
        mode, events = lifecycle_case({}, True)
        if entered:
            mode.enter()
            mode.exit()
        events.clear()
        mode.exit()
        mode.exit()
        assert events == ["before_exit", "after_exit"] * 2
        assert mode.active is None

    @pytest.mark.parametrize(
        "failure_stages",
        [
            ("before_enter", "before_exit"),
            ("after_enter", "after_exit"),
            ("body", "before_exit"),
            ("body", "after_exit"),
            ("before_exit", "after_exit"),
            ("before_exit", "deactivate"),
            ("deactivate", "after_exit"),
            ("body", "before_exit", "deactivate", "after_exit"),
        ],
    )
    def test_multiple_failures_are_chained(
        self,
        lifecycle_case: typing.Callable[
            [dict[str, BaseException], bool], tuple[Mode, list[str]]
        ],
        failure_stages: tuple[str, ...],
    ) -> None:
        errors: dict[str, BaseException] = {
            stage: HookTestError(stage) for stage in failure_stages
        }
        mode, events = lifecycle_case(errors, True)
        outer, _ = lifecycle_case({}, True)
        with outer:
            with pytest.raises(Exception) as caught:
                with mode:
                    if "body" in errors:
                        raise errors["body"]
            assert current_mode() is outer
        chain: list[BaseException] = []
        exception: BaseException | None = caught.value
        while exception is not None:
            chain.append(exception)
            exception = exception.__context__
        # Method deactivation wraps its error in RuntimeError; hook errors
        # themselves keep their identity and order in the chain.
        assert [error for error in chain if isinstance(error, HookTestError)] == [
            errors[stage] for stage in reversed(failure_stages)
        ]
        assert events[-1] == "after_exit"
        assert mode.active is None
        assert mode._entered is False
        assert modecount() == 0
        assert not mode._guard._lock.locked()

    @pytest.mark.usefixtures("empty_method_registry")
    @pytest.mark.parametrize("syntax", ["explicit", "context", "decorator"])
    @pytest.mark.parametrize("policy", ["error", "warn"])
    def test_builtin_on_fail_skips_after_enter(
        self, monkeypatch: pytest.MonkeyPatch, syntax: str, policy: OnFail
    ) -> None:
        monkeypatch.delenv("WAKEPY_FAKE_SUCCESS", raising=False)
        events: list[str] = []
        mode = keep.running(
            on_fail=policy,
            after_enter=lambda _: events.append("after_enter"),
            before_exit=lambda _: events.append("before_exit"),
            after_exit=lambda _: events.append("after_exit"),
        )

        def body() -> None:
            events.append("body")

        with pytest.raises(ActivationError if policy == "error" else ActivationWarning):
            if syntax == "explicit":
                try:
                    mode.enter()
                    body()
                finally:
                    mode.exit()
            elif syntax == "context":
                with mode:
                    body()
            else:
                mode(body)()
        assert events == ["before_exit", "after_exit"]
        assert modecount() == 0

    @pytest.mark.parametrize("syntax", ["context", "decorator"])
    @pytest.mark.parametrize(
        "error_type", [HookTestError, KeyboardInterrupt, SystemExit, ModeExit]
    )
    def test_body_failure(
        self,
        lifecycle_case: typing.Callable[
            [dict[str, BaseException], bool], tuple[Mode, list[str]]
        ],
        syntax: str,
        error_type: type[BaseException],
    ) -> None:
        mode, events = lifecycle_case({}, True)
        outer, _ = lifecycle_case({}, True)
        error = error_type("body")

        def body() -> None:
            events.append("body")
            raise error

        def run() -> None:
            if syntax == "context":
                with mode:
                    body()
            else:
                mode(body)()

        with outer:
            if error_type is ModeExit:
                run()
            else:
                with pytest.raises(error_type) as caught:
                    run()
                assert caught.value is error
            assert current_mode() is outer
        assert events[-4:] == ["body", "before_exit", "deactivate", "after_exit"]
        assert modecount() == 0


@pytest.mark.usefixtures("empty_method_registry")
class TestLifecycleHookInvocationOrder:
    """Hooks fire in the correct order on success and fail paths."""

    @staticmethod
    def _make_hooks(
        events: List[tuple[str, str]],
    ) -> tuple[
        typing.Callable[[Mode], None],
        typing.Callable[[Mode], None],
        typing.Callable[[Mode], None],
        typing.Callable[[Mode], None],
    ]:
        def before_enter(mode: Mode) -> None:
            events.append(("before_enter", f"active={mode.active}"))

        def after_enter(mode: Mode) -> None:
            events.append(("after_enter", f"active={mode.active}"))

        def before_exit(mode: Mode) -> None:
            events.append(("before_exit", f"active={mode.active}"))

        def after_exit(mode: Mode) -> None:
            events.append(("after_exit", f"active={mode.active}"))

        return before_enter, after_enter, before_exit, after_exit

    @pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
    def test_hook_invocation_order_success(self) -> None:
        events: List[tuple[str, str]] = []
        before_enter, after_enter, before_exit, after_exit = self._make_hooks(events)

        def on_success(result: ActivationResult) -> None:
            events.append(("on_success", f"success={result.success}"))

        params = create_mode_params(
            ModeName.KEEP_RUNNING,
            before_enter=before_enter,
            after_enter=after_enter,
            on_success=on_success,
            before_exit=before_exit,
            after_exit=after_exit,
        )
        mode = Mode(params)
        mode.enter()
        events.append(("user_code", "running"))
        mode.exit()

        assert events == [
            ("before_enter", "active=None"),
            ("on_success", "success=True"),
            ("after_enter", "active=True"),
            ("user_code", "running"),
            ("before_exit", "active=True"),
            ("after_exit", "active=None"),
        ]

    def test_hook_invocation_order_fail(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("WAKEPY_FAKE_SUCCESS", raising=False)
        events: List[tuple[str, str]] = []
        before_enter, after_enter, before_exit, after_exit = self._make_hooks(events)

        def on_fail(result: ActivationResult) -> None:
            events.append(("on_fail", f"success={result.success}"))

        params = create_mode_params(
            ModeName.KEEP_RUNNING,
            before_enter=before_enter,
            after_enter=after_enter,
            on_fail=on_fail,
            before_exit=before_exit,
            after_exit=after_exit,
        )
        mode = Mode(params)
        mode.enter()
        events.append(("user_code", "running"))
        mode.exit()

        assert events == [
            ("before_enter", "active=None"),
            ("on_fail", "success=False"),
            ("after_enter", "active=False"),
            ("user_code", "running"),
            ("before_exit", "active=False"),
            ("after_exit", "active=None"),
        ]


@pytest.mark.usefixtures("empty_method_registry", "WAKEPY_FAKE_SUCCESS_eq_1")
class TestRecursionGuard:
    """Calling enter() or exit() from within any hook raises RuntimeError."""

    @pytest.mark.parametrize("called_method", ["enter", "exit"])
    @pytest.mark.parametrize("hook_name", ["before_enter", "after_enter"])
    def test_entry_hook_recursive_call_raises(
        self, hook_name: str, called_method: str
    ) -> None:
        """Calling mode.enter() or .exit() from within an entry hook raises
        RuntimeError."""

        def hook(mode: Mode) -> None:
            getattr(mode, called_method)()

        params = create_mode_params(WakepyFakeSuccess.mode_name, **{hook_name: hook})  # type: ignore[arg-type]
        mode = Mode(params)
        expected_error = (
            rf"Mode\.{called_method}\(\) — re-entrant call is not allowed\."
        )
        with pytest.raises(RuntimeError, match=expected_error):
            mode.enter()
        mode.exit()  # no-op for before_enter; cleans up for after_enter

    @pytest.mark.parametrize("called_method", ["enter", "exit"])
    @pytest.mark.parametrize("hook_name", ["before_exit", "after_exit"])
    def test_exit_hook_recursive_call_raises(
        self, hook_name: str, called_method: str
    ) -> None:
        """Calling mode.enter() or .exit() from within an exit hook raises
        RuntimeError."""

        def hook(mode: Mode) -> None:
            getattr(mode, called_method)()

        params = create_mode_params(WakepyFakeSuccess.mode_name, **{hook_name: hook})  # type: ignore[arg-type]
        mode = Mode(params)
        mode.enter()
        expected_error = (
            rf"Mode\.{called_method}\(\) — re-entrant call is not allowed\."
        )
        with pytest.raises(RuntimeError, match=expected_error):
            mode.exit()


@pytest.mark.usefixtures("empty_method_registry", "WAKEPY_FAKE_SUCCESS_eq_1")
class TestHookNotCalledOnDoubleEnter:
    """Test that hooks are not invoked on second enter() call."""

    def test_hooks_not_called_on_double_enter(
        self,
    ) -> None:
        """Hooks should not be called if mode is already entered."""
        calls: List[str] = []

        def before_enter_callback(mode: Mode) -> None:
            calls.append("before_enter")

        params = create_mode_params(
            ModeName.KEEP_RUNNING,
            before_enter=before_enter_callback,
        )
        mode = Mode(params)
        mode.enter()
        # Second enter with if_already_entered="pass" — hooks must not fire
        mode.enter(if_already_entered="pass")

        assert calls == ["before_enter"]
        mode.exit()


@pytest.mark.usefixtures("empty_method_registry", "WAKEPY_FAKE_SUCCESS_eq_1")
class TestHookExceptionPropagation:
    """Exception raised in any hook propagates to the caller."""

    @staticmethod
    def raising_hook(_: typing.Any) -> None:
        raise HookTestError()

    @pytest.mark.parametrize(
        "hook_name, fake_success",
        [
            ("before_enter", True),
            ("after_enter", True),
            ("on_success", True),
            ("on_fail", False),
        ],
    )
    def test_entry_hook_exception_propagates(
        self,
        hook_name: str,
        fake_success: bool,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Exception in any hook fired during enter() propagates out of
        enter()."""
        if fake_success:
            monkeypatch.setenv("WAKEPY_FAKE_SUCCESS", "1")
        else:
            monkeypatch.delenv("WAKEPY_FAKE_SUCCESS", raising=False)

        params = create_mode_params(
            ModeName.KEEP_RUNNING,
            **{hook_name: self.raising_hook},  # type: ignore[arg-type]
        )

        mode = Mode(params)

        with pytest.raises(HookTestError):
            mode.enter()
        mode.exit()

    @pytest.mark.parametrize("hook_name", ["before_exit", "after_exit"])
    def test_exit_hook_exception_propagates(
        self,
        hook_name: str,
    ) -> None:
        """Exception in an exit hook propagates out of exit(). Mode is
        fully cleaned up after the exception."""

        params = create_mode_params(
            ModeName.KEEP_RUNNING,
            **{hook_name: self.raising_hook},  # type: ignore[arg-type]
        )

        mode = Mode(params)

        mode.enter()
        with pytest.raises(HookTestError):
            mode.exit()

        assert mode.active is None
        assert mode._entered is False
        assert modecount() == 0


@pytest.mark.usefixtures("empty_method_registry")
class TestExplicitHookExceptionCleanup:
    """Explicit callers must exit after enter-hook failures."""

    @pytest.mark.parametrize(
        "hook_name, fake_success",
        [
            ("after_enter", True),
            ("on_success", True),
            ("on_fail", False),
        ],
    )
    def test_entry_hook_exception_exits_mode(
        self,
        hook_name: str,
        fake_success: bool,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        if fake_success:
            monkeypatch.setenv("WAKEPY_FAKE_SUCCESS", "1")

        def raising_hook(*_args: typing.Any) -> None:
            raise HookTestError()

        params = create_mode_params(
            ModeName.KEEP_RUNNING,
            **{hook_name: raising_hook},  # type: ignore[arg-type]
        )
        mode = Mode(params)

        with pytest.raises(HookTestError):
            mode.enter()

        # Explicit enter() requires caller cleanup. Context managers and
        # decorators perform this cleanup automatically.
        mode.exit()

        assert mode.active is None
        assert mode._entered is False
        assert modecount() == 0

    def test_before_exit_hook_exception_exits_mode(
        self,
        WAKEPY_FAKE_SUCCESS_eq_1: None,
    ) -> None:
        def raising_hook(_mode: Mode) -> None:
            raise HookTestError()

        params = create_mode_params(ModeName.KEEP_RUNNING, before_exit=raising_hook)
        mode = Mode(params)
        mode.enter()

        with pytest.raises(HookTestError):
            mode.exit()

        assert mode.active is None
        assert mode._entered is False
        assert modecount() == 0


@pytest.mark.usefixtures("empty_method_registry", "WAKEPY_FAKE_SUCCESS_eq_1")
class TestHooksWithContextManager:
    """Hooks work correctly with context manager syntax."""

    def test_exception_in_body_runs_exit_hooks(self) -> None:
        """Exception in body: before_exit AND after_exit both run."""
        events: List[str] = []

        def before_exit_cb(mode: Mode) -> None:
            events.append("before_exit")

        def after_exit_cb(mode: Mode) -> None:
            events.append("after_exit")

        with pytest.raises(RuntimeError, match="User error"):
            with keep.running(
                before_exit=before_exit_cb,
                after_exit=after_exit_cb,
            ):
                events.append("body")
                raise RuntimeError("User error")

        assert events == ["body", "before_exit", "after_exit"]

    def test_nested_contexts_with_hooks(self) -> None:
        """Nested contexts invoke hooks in correct order."""
        events: List[str] = []

        with keep.running(before_enter=lambda m: events.append("outer_before")):
            events.append("outer_body")
            with keep.presenting(before_enter=lambda m: events.append("inner_before")):
                events.append("inner_body")
            events.append("outer_body_after_inner")

        assert events == [
            "outer_before",
            "outer_body",
            "inner_before",
            "inner_body",
            "outer_body_after_inner",
        ]


@pytest.mark.usefixtures("empty_method_registry", "WAKEPY_FAKE_SUCCESS_eq_1")
class TestHooksWithDecorator:
    """Hooks work correctly with decorator syntax."""

    def test_decorator_fires_hook_on_call(self) -> None:
        """Decorated function: hook fires when the decorated function runs."""
        events: List[str] = []

        def before_enter_cb(mode: Mode) -> None:
            events.append("before_enter")

        @keep.running(before_enter=before_enter_cb)
        def decorated_func() -> None:
            events.append("body")

        decorated_func()

        assert events == ["before_enter", "body"]


@pytest.mark.usefixtures("empty_method_registry", "WAKEPY_FAKE_SUCCESS_eq_1")
class TestRecursionAllowedAcrossModes:
    """Entering a different mode from within a hook is allowed."""

    def test_entering_different_mode_from_hook_is_allowed(self) -> None:
        """Entering a different mode from a hook should work fine."""
        mode2 = keep.running()
        mode2_entered = False

        def on_success_cb(result: object) -> None:
            nonlocal mode2_entered
            mode2.enter()
            mode2_entered = True

        mode1 = keep.running(on_success=on_success_cb)
        mode1.enter()

        assert mode1.active is True
        assert mode2_entered is True
        assert mode2.active is True

        mode2.exit()
        mode1.exit()


@pytest.mark.usefixtures("empty_method_registry", "WAKEPY_FAKE_SUCCESS_eq_1")
class TestThreadSafetyLockOrdering:
    """Lock is acquired before hooks and released after hooks."""

    def test_lock_acquired_before_before_enter_hook(self) -> None:
        """Lock must be held when before_enter fires."""
        lock_held_during_hook: list[bool] = []

        def before_enter_cb(mode: Mode) -> None:
            lock_held_during_hook.append(mode._guard._lock.locked())

        params = create_mode_params(ModeName.KEEP_RUNNING, before_enter=before_enter_cb)
        mode = Mode(params)
        mode.enter()
        mode.exit()

        assert lock_held_during_hook == [True]

    def test_lock_acquired_before_after_enter_hook(self) -> None:
        """Lock must be held when after_enter fires."""
        lock_held_during_hook: list[bool] = []

        def after_enter_cb(mode: Mode) -> None:
            lock_held_during_hook.append(mode._guard._lock.locked())

        params = create_mode_params(ModeName.KEEP_RUNNING, after_enter=after_enter_cb)
        mode = Mode(params)
        mode.enter()
        mode.exit()

        assert lock_held_during_hook == [True]

    def test_lock_acquired_before_before_exit_hook(self) -> None:
        """Lock must be held when before_exit fires."""
        lock_held_during_hook: list[bool] = []

        def before_exit_cb(mode: Mode) -> None:
            lock_held_during_hook.append(mode._guard._lock.locked())

        params = create_mode_params(ModeName.KEEP_RUNNING, before_exit=before_exit_cb)
        mode = Mode(params)
        mode.enter()
        mode.exit()

        assert lock_held_during_hook == [True]

    def test_lock_acquired_before_after_exit_hook(self) -> None:
        """Lock must be held when after_exit fires."""
        lock_held_during_hook: list[bool] = []

        def after_exit_cb(mode: Mode) -> None:
            lock_held_during_hook.append(mode._guard._lock.locked())

        params = create_mode_params(ModeName.KEEP_RUNNING, after_exit=after_exit_cb)
        mode = Mode(params)
        mode.enter()
        mode.exit()

        assert lock_held_during_hook == [True]

    def test_lock_released_after_enter(self) -> None:
        """Lock must be released after enter() returns."""
        params = create_mode_params(ModeName.KEEP_RUNNING)
        mode = Mode(params)
        mode.enter()
        assert not mode._guard._lock.locked()
        mode.exit()

    def test_lock_released_after_exit(self) -> None:
        """Lock must be released after exit() returns."""
        params = create_mode_params(ModeName.KEEP_RUNNING)
        mode = Mode(params)
        mode.enter()
        mode.exit()
        assert not mode._guard._lock.locked()

    def test_lock_released_after_enter_raises(self) -> None:
        """Lock must be released even if enter() raises an exception."""

        def raising_hook(_: typing.Any) -> None:
            raise HookTestError()

        params = create_mode_params(ModeName.KEEP_RUNNING, before_enter=raising_hook)
        mode = Mode(params)
        with pytest.raises(HookTestError):
            mode.enter()
        assert not mode._guard._lock.locked()

    def test_lock_released_after_exit_raises(self) -> None:
        """Lock must be released even if exit() raises an exception."""

        def raising_hook(_: typing.Any) -> None:
            raise HookTestError()

        params = create_mode_params(ModeName.KEEP_RUNNING, before_exit=raising_hook)
        mode = Mode(params)
        mode.enter()
        with pytest.raises(HookTestError):
            mode.exit()
        assert not mode._guard._lock.locked()

    def test_different_modes_do_not_share_lifecycle_lock(self) -> None:
        """A blocked hook on one mode does not block another mode."""
        hook_started = threading.Event()
        hook_release = threading.Event()
        second_enter_done = threading.Event()
        errors: list[BaseException] = []

        def blocking_before_enter(mode: Mode) -> None:
            hook_started.set()
            hook_release.wait(timeout=5)

        params = create_mode_params(
            ModeName.KEEP_RUNNING, before_enter=blocking_before_enter
        )
        mode1 = Mode(params)
        mode2 = Mode(create_mode_params(ModeName.KEEP_RUNNING))

        def thread1() -> None:
            try:
                mode1.enter()
            except BaseException as error:
                errors.append(error)

        def thread2() -> None:
            try:
                mode2.enter()
                second_enter_done.set()
            except BaseException as error:
                errors.append(error)

        t1 = threading.Thread(target=thread1)
        t2 = threading.Thread(target=thread2)
        t1.start()
        try:
            assert hook_started.wait(timeout=5)
            t2.start()
            assert second_enter_done.wait(timeout=5)
            assert not hook_release.is_set()
        finally:
            hook_release.set()
            t1.join(timeout=5)
            if t2.ident is not None:
                t2.join(timeout=5)
            mode1.exit()
            mode2.exit()
        assert not t1.is_alive()
        assert not t2.is_alive()
        assert errors == []


@pytest.mark.usefixtures("empty_method_registry")
class TestStateTransitions:
    """Verify state machine transitions per spec."""

    def test_exit_on_not_entered_mode_keeps_reset_state(self) -> None:
        """exit() without entry leaves the mode unentered and inactive."""
        params = create_mode_params(ModeName.KEEP_RUNNING)
        mode = Mode(params)
        mode.exit()  # must not raise
        assert mode.active is None
        assert mode._entered is False

    @pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
    def test_enter_on_entered_mode_is_noop(self) -> None:
        """enter() on an already-entered mode: hooks not called."""
        calls: list[str] = []

        def before_enter_cb(m: Mode) -> None:
            calls.append("before_enter")

        params = create_mode_params(ModeName.KEEP_RUNNING, before_enter=before_enter_cb)
        mode = Mode(params)
        mode.enter()
        mode.enter(if_already_entered="pass")
        assert calls == ["before_enter"]  # not called twice
        mode.exit()

    def test_exit_does_nothing_when_not_active(
        self,
        monkeypatch: pytest.MonkeyPatch,
        do_assert: typing.Callable[[bool], None],
    ) -> None:
        """_exit() is a no-op when mode.active is not True."""
        monkeypatch.delenv("WAKEPY_FAKE_SUCCESS", raising=False)
        params = create_mode_params(ModeName.KEEP_RUNNING, on_fail=None)

        # Activation fails (no methods, no FAKE_SUCCESS); mode is still entered
        mode = Mode(params)
        mode.enter()
        do_assert(mode.active is False)
        do_assert(mode._entered is True)
        mode.exit()
        do_assert(mode.active is None)
        do_assert(mode._entered is False)

    @pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
    def test_exit_deactivates_when_active(
        self, do_assert: typing.Callable[[bool], None]
    ) -> None:
        """_exit() deactivates the method when mode.active is True."""
        params = create_mode_params(ModeName.KEEP_RUNNING)
        mode = Mode(params)
        mode.enter()
        do_assert(mode.active is True)
        do_assert(mode._active_method is not None)
        mode.exit()
        do_assert(mode.active is None)
        do_assert(mode._active_method is None)

    @pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
    def test_enter_order_lock_before_before_enter_after_enter_after(self) -> None:
        """enter(): lock → before_enter → _enter() → after_enter → unlock."""
        events: list[str] = []

        def before_enter_cb(m: Mode) -> None:
            events.append("before_enter")

        def after_enter_cb(m: Mode) -> None:
            events.append("after_enter")

        params = create_mode_params(
            ModeName.KEEP_RUNNING,
            before_enter=before_enter_cb,
            after_enter=after_enter_cb,
        )
        mode = Mode(params)
        mode.enter()
        assert events == ["before_enter", "after_enter"]
        mode.exit()

    @pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
    def test_exit_order_lock_before_exit_deactivate_after_exit(self) -> None:
        """exit() calls: lock → before_exit → _exit() → after_exit → unlock."""
        events: list[str] = []

        def before_exit_cb(m: Mode) -> None:
            events.append("before_exit")

        def after_exit_cb(m: Mode) -> None:
            events.append(f"after_exit(active={m.active})")

        params = create_mode_params(
            ModeName.KEEP_RUNNING,
            before_exit=before_exit_cb,
            after_exit=after_exit_cb,
        )
        mode = Mode(params)
        mode.enter()
        mode.exit()
        assert events == ["before_exit", "after_exit(active=None)"]


@pytest.mark.usefixtures("empty_method_registry", "WAKEPY_FAKE_SUCCESS_eq_1")
class TestExceptionHandlingSpec:
    """Verify exception handling follows spec."""

    def test_before_exit_raises_mode_still_deactivated(
        self, do_assert: typing.Callable[[bool], None]
    ) -> None:
        """before_exit raising: mode deactivated and exception re-raised."""

        def raising_hook(_: Mode) -> None:
            raise HookTestError()

        params = create_mode_params(ModeName.KEEP_RUNNING, before_exit=raising_hook)
        mode = Mode(params)
        mode.enter()
        do_assert(mode.active is True)

        with pytest.raises(HookTestError):
            mode.exit()

        do_assert(mode.active is None)
        do_assert(mode._entered is False)
        do_assert(modecount() == 0)

    def test_enter_exception_no_auto_deactivate_exit_cleans_up(self) -> None:
        """enter() raising does not auto-deactivate; user exit() cleans up."""

        def raising_hook(_: typing.Any) -> None:
            raise HookTestError()

        params = create_mode_params(ModeName.KEEP_RUNNING, after_enter=raising_hook)
        mode = Mode(params)

        with pytest.raises(HookTestError):
            mode.enter()

        # Mode was activated but enter() raised — needs explicit exit()
        mode.exit()

        assert mode.active is None
        assert mode._entered is False
        assert modecount() == 0

    def test_after_exit_raises_deactivation_already_done(
        self, do_assert: typing.Callable[[bool], None]
    ) -> None:
        """after_exit raising: deactivation already done before it fires."""

        def raising_hook(_: Mode) -> None:
            raise HookTestError()

        params = create_mode_params(ModeName.KEEP_RUNNING, after_exit=raising_hook)
        mode = Mode(params)
        mode.enter()
        do_assert(mode.active is True)

        with pytest.raises(HookTestError):
            mode.exit()

        do_assert(mode.active is None)
        do_assert(mode._entered is False)
        do_assert(modecount() == 0)
