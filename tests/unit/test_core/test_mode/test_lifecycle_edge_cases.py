"""Ownership, inactive states, hook forwarding and result-hook recursion."""

from __future__ import annotations

import sys
import threading
import typing
import warnings

import pytest

import wakepy
import wakepy.core as core
from wakepy import (
    ActivationResult,
    ActivationWarning,
    ContextAlreadyEnteredError,
    Mode,
    current_mode,
    keep,
    modecount,
)
from wakepy.core.mode import ModeHook, ResultHook, _ModeParams
from wakepy.methods._testing import WakepyFakeSuccess

if typing.TYPE_CHECKING:
    from typing import Callable

    from wakepy.core.mode import IfAlreadyEntered, OnFail

    LifecycleFactory = Callable[
        [dict[str, BaseException], bool], tuple[Mode, list[str]]
    ]


class TestContextOwnership:
    @pytest.mark.parametrize("success", [False, True])
    def test_explicit_reentry_keeps_context_owner(
        self,
        lifecycle_case: LifecycleFactory,
        success: bool,
        do_assert: Callable[[bool], None],
    ) -> None:
        mode, _ = lifecycle_case({}, success)
        with mode:
            token = mode._context_token
            mode.exit()
            do_assert(mode.active is None)
            mode.enter()
            do_assert(mode.active is success)
            do_assert(mode._context_token is token)
            do_assert(current_mode() is mode)
        do_assert(mode._context_token is None)
        do_assert(mode.active is None)

    @pytest.mark.parametrize("success", [False, True])
    def test_context_rejects_explicitly_entered_mode(
        self,
        lifecycle_case: LifecycleFactory,
        success: bool,
        do_assert: Callable[[bool], None],
    ) -> None:
        mode, events = lifecycle_case({}, success)
        mode.enter()
        events.clear()
        try:
            with pytest.raises(ContextAlreadyEnteredError):
                with mode:
                    raise AssertionError("Duplicate context body must not run")
            do_assert(mode.active is success)
            do_assert(mode._entered)
            do_assert(events == [])
        finally:
            mode.exit()
        do_assert(mode.active is None)

    @pytest.mark.parametrize("manual_exit", [False, True])
    @pytest.mark.parametrize("other_thread", [False, True])
    def test_context_token_has_one_owner(
        self,
        lifecycle_case: LifecycleFactory,
        manual_exit: bool,
        other_thread: bool,
        do_assert: Callable[[bool], None],
    ) -> None:
        mode, events = lifecycle_case({}, True)
        errors: list[BaseException] = []

        def duplicate() -> None:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    with mode:
                        raise AssertionError("Duplicate context body must not run")
            except BaseException as error:
                errors.append(error)

        with mode:
            if manual_exit:
                mode.exit()
            events.clear()
            token = mode._context_token
            if other_thread:
                worker = threading.Thread(target=duplicate)
                worker.start()
                worker.join(timeout=5)
                do_assert(not worker.is_alive())
            else:
                duplicate()
            do_assert(len(errors) == 1)
            do_assert(isinstance(errors[0], ContextAlreadyEnteredError))
            do_assert(events == [])
            do_assert(mode._context_token is token)
            do_assert(current_mode() is mode)
            do_assert(mode.active is (None if manual_exit else True))
        do_assert(mode._context_token is None)
        with mode:
            do_assert(current_mode() is mode)
            do_assert(mode.active is True)
        do_assert(mode.active is None)
        do_assert(modecount() == 0)


class TestCompleteStateTransitions:
    @pytest.mark.parametrize("entered", [False, True])
    @pytest.mark.parametrize("success", [False, True])
    @pytest.mark.parametrize("operation", ["exit", "pass", "warn", "error"])
    def test_state_transition(
        self,
        lifecycle_case: LifecycleFactory,
        entered: bool,
        success: bool,
        operation: str,
    ) -> None:
        mode, events = lifecycle_case({}, success)
        original = mode.enter() if entered else mode.result
        events.clear()
        try:
            if operation == "exit":
                mode.exit()
                expected = ["before_exit"]
                if entered and success:
                    expected.append("deactivate")
                expected.append("after_exit")
                assert mode.active is None
                assert not mode._entered
            else:
                policy = typing.cast("IfAlreadyEntered", operation)
                if entered and operation == "warn":
                    with pytest.warns(UserWarning, match="already active"):
                        result = mode.enter(if_already_entered=policy)
                    assert result is original
                elif entered and operation == "error":
                    with pytest.raises(ContextAlreadyEnteredError):
                        mode.enter(if_already_entered=policy)
                else:
                    result = mode.enter(if_already_entered=policy)
                    if entered:
                        assert result is original
                expected = (
                    []
                    if entered
                    else ["before_enter"]
                    + (["activate", "on_success"] if success else ["on_fail"])
                    + ["after_enter"]
                )
                assert mode.active is success
                assert mode._entered
            assert events == expected
        finally:
            mode.exit()

    @pytest.mark.parametrize("entered", [False, True])
    @pytest.mark.parametrize(
        "failing_hooks",
        [
            ("before_exit",),
            ("after_exit",),
            ("before_exit", "after_exit"),
        ],
    )
    def test_exit_failures_from_inactive_states(
        self,
        lifecycle_case: LifecycleFactory,
        entered: bool,
        failing_hooks: tuple[str, ...],
    ) -> None:
        errors: dict[str, BaseException] = {
            name: ValueError(name) for name in failing_hooks
        }
        mode, events = lifecycle_case(errors, False)
        if entered:
            mode.enter()
        events.clear()
        with pytest.raises(ValueError) as caught:
            mode.exit()
        assert caught.value is errors[failing_hooks[-1]]
        if len(failing_hooks) == 2:
            assert caught.value.__context__ is errors["before_exit"]
        assert events == ["before_exit", "after_exit"]
        assert mode.active is None
        assert not mode._entered
        assert not mode._guard._lock.locked()

    def test_success_then_failure_reentry(
        self,
        lifecycle_case: LifecycleFactory,
        monkeypatch: pytest.MonkeyPatch,
        do_assert: Callable[[bool], None],
    ) -> None:
        mode, events = lifecycle_case({}, True)
        successful_result = mode.enter()
        method = mode.method
        mode.exit()
        do_assert(mode.result is successful_result)
        do_assert(mode.method is method)
        do_assert(mode.active_method is None)
        monkeypatch.setenv("WAKEPY_FORCE_FAILURE", "1")
        events.clear()
        failed_result = mode.enter()
        do_assert(failed_result is not successful_result)
        do_assert(mode.active is False)
        do_assert(mode.method is method)
        mode.exit()
        do_assert(
            events
            == ["before_enter", "on_fail", "after_enter", "before_exit", "after_exit"]
        )
        do_assert(mode.result is failed_result)
        do_assert(mode.active is None)
        monkeypatch.delenv("WAKEPY_FORCE_FAILURE")
        with mode:
            do_assert(mode.active is True)
        do_assert(modecount() == 0)


class TestHookContracts:
    def test_public_aliases(self) -> None:
        assert wakepy.ModeHook is core.ModeHook is ModeHook
        assert wakepy.ResultHook is core.ResultHook is ResultHook

    def test_removed_on_fail_api(self) -> None:
        invalid = typing.cast("OnFail", "pass")
        for factory in (keep.running, keep.presenting):
            with pytest.raises(ValueError, match="on_fail must be"):
                factory(on_fail=invalid)
            assert not hasattr(factory(), "on_fail")

    @pytest.mark.usefixtures("empty_method_registry")
    @pytest.mark.parametrize("factory_name", ["running", "presenting"])
    @pytest.mark.parametrize("syntax", ["explicit", "context", "decorator"])
    @pytest.mark.parametrize("success", [False, True])
    def test_factory_forwards_all_hooks(
        self,
        monkeypatch: pytest.MonkeyPatch,
        factory_name: str,
        syntax: str,
        success: bool,
    ) -> None:
        if success:
            monkeypatch.setenv("WAKEPY_FAKE_SUCCESS", "1")
        else:
            monkeypatch.delenv("WAKEPY_FAKE_SUCCESS", raising=False)
        events: list[str] = []
        states: list[bool | None] = []
        actual_modes: list[Mode] = []

        def mode_hook(name: str) -> Callable[[Mode], str]:
            def callback(mode: Mode) -> str:
                events.append(name)
                states.append(mode.active)
                actual_modes.append(mode)
                return "ignored return value"

            return callback

        def result_hook(name: str) -> Callable[[ActivationResult], str]:
            def callback(result: ActivationResult) -> str:
                assert isinstance(result, ActivationResult)
                assert result.success is success
                events.append(name)
                return "ignored return value"

            return callback

        factory = keep.running if factory_name == "running" else keep.presenting
        mode = factory(
            before_enter=mode_hook("before_enter"),
            after_enter=mode_hook("after_enter"),
            before_exit=mode_hook("before_exit"),
            after_exit=mode_hook("after_exit"),
            on_success=result_hook("on_success"),
            on_fail=result_hook("on_fail"),
        )

        def body() -> None:
            events.append("body")

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
        assert events == [
            "before_enter",
            "on_success" if success else "on_fail",
            "after_enter",
            "body",
            "before_exit",
            "after_exit",
        ]
        assert states == [None, success, success, None]
        assert all(actual is actual_modes[0] for actual in actual_modes)
        assert actual_modes[0].name == f"keep.{factory_name}"

    @pytest.mark.parametrize("success", [False, True])
    @pytest.mark.parametrize("operation", ["enter", "exit", "context"])
    def test_result_hooks_reject_same_mode_recursion(
        self, success: bool, operation: str
    ) -> None:
        def callback(_: ActivationResult) -> None:
            if operation == "context":
                with mode:
                    raise AssertionError("Recursive context body must not run")
            elif operation == "enter":
                mode.enter()
            else:
                mode.exit()

        mode = Mode(
            _ModeParams(
                name="result-recursion",
                method_classes=[WakepyFakeSuccess] if success else [],
                on_success=callback,
                on_fail=callback,
            )
        )
        called = "exit" if operation == "exit" else "enter"
        with pytest.raises(RuntimeError, match=rf"Mode\.{called}\(\).*re-entrant"):
            with mode:
                raise AssertionError("Outer body must not run")
        assert mode.active is None
        assert not mode._entered
        assert modecount() == 0

    @pytest.mark.parametrize("syntax", ["explicit", "context", "decorator"])
    def test_activation_warning_points_to_caller(self, syntax: str) -> None:
        mode = Mode(_ModeParams(method_classes=[], on_fail="warn"))

        def body() -> None:
            pass

        with pytest.warns(ActivationWarning) as caught:
            if syntax == "explicit":
                line = sys._getframe().f_lineno + 1
                mode.enter()
                mode.exit()
            elif syntax == "context":
                line = sys._getframe().f_lineno + 1
                with mode:
                    body()
            else:
                line = sys._getframe().f_lineno + 1
                mode(body)()
        assert caught[0].filename == __file__
        assert caught[0].lineno == line
