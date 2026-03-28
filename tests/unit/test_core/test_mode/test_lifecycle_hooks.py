"""Tests for lifecycle hooks functionality in Mode class.

Tests all 5 lifecycle hooks:
- before_enter
- after_enter
- before_exit
- after_exit
- on_success
"""

from __future__ import annotations

import typing

import pytest

from wakepy import Mode, keep, modecount
from wakepy.core.constants import ModeName
from wakepy.core.mode import create_mode_params
from wakepy.methods._testing import WakepyFakeSuccess

if typing.TYPE_CHECKING:
    from typing import List

    from wakepy import ActivationResult


class HookTestError(Exception):
    pass


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
        expected_error = rf"Mode\.{called_method}\(\) called from within a hook\."
        with pytest.raises(RuntimeError, match=expected_error):
            mode.enter()

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
        expected_error = rf"Mode\.{called_method}\(\) called from within a hook\."
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
class TestHookExceptionExitsMode:
    """When a hook raises, mode is exited without exit hooks and exception
    re-raised."""

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
