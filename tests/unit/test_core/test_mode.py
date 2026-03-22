from __future__ import annotations

import asyncio
import copy
import queue
import re
import threading
import typing
import warnings
from unittest.mock import Mock

import pytest

import wakepy.core.mode as _mode_module
from tests.unit.test_core.testmethods import get_test_method_class
from wakepy import (
    ActivationError,
    ActivationResult,
    ActivationWarning,
    ContextAlreadyEnteredError,
    Method,
    MethodInfo,
    Mode,
    global_modes,
    modecount,
)
from wakepy.core import PlatformType
from wakepy.core.activationresult import MethodActivationResult
from wakepy.core.constants import IdentifiedPlatformType, StageName
from wakepy.core.dbus import DBusAdapter
from wakepy.core.heartbeat import Heartbeat
from wakepy.core.mode import (
    ModeExit,
    UnrecognizedMethodNames,
    _ModeParams,
    handle_activation_fail,
    select_methods,
)
from wakepy.core.registry import get_methods

if typing.TYPE_CHECKING:
    from typing import List, Type


@pytest.fixture
def dbus_adapter_cls():
    class TestDbusAdapter(DBusAdapter): ...

    return TestDbusAdapter


@pytest.fixture
def testmode_cls():
    class TestMode(Mode): ...

    return TestMode


@pytest.fixture
def methods_abc(monkeypatch, testutils) -> List[Type[Method]]:
    """This fixture creates three methods, which belong to a given mode."""
    testutils.empty_method_registry(monkeypatch)

    class TestMethod(Method):
        supported_platforms = (PlatformType.ANY,)

    class MethodA(TestMethod):
        name = "MethodA"
        mode_name = "foo"

        def enter_mode(self): ...

    class MethodB(TestMethod):
        name = "MethodB"
        mode_name = "foo"

        def enter_mode(self): ...

    class MethodC(TestMethod):
        name = "MethodC"
        mode_name = "foo"

        def enter_mode(self): ...

    return [MethodA, MethodB, MethodC]


@pytest.fixture
def methods_priority0():
    return ["*"]


@pytest.fixture
def mode0(
    methods_abc: List[Type[Method]],
    testmode_cls: Type[Mode],
    methods_priority0: List[str],
) -> typing.Generator[Mode, None, None]:
    params = _ModeParams(
        name="TestMode",
        method_classes=methods_abc,
        dbus_adapter=None,
        methods_priority=methods_priority0,
    )
    mode = testmode_cls(params)
    yield mode
    mode.exit()  # safe no-op if never entered


@pytest.fixture
def mode1_with_dbus(
    methods_abc: List[Type[Method]],
    testmode_cls: Type[Mode],
    methods_priority0: List[str],
    dbus_adapter_cls: Type[DBusAdapter],
):
    params = _ModeParams(
        name="TestMode1",
        method_classes=methods_abc,
        methods_priority=methods_priority0,
        dbus_adapter=dbus_adapter_cls,
    )
    return testmode_cls(params)


class SyncButton:
    def __init__(self) -> None:
        self.on_click: typing.Optional[typing.Callable[[object], None]] = None

    def click(self, e: object = None) -> None:
        if self.on_click is not None:
            self.on_click(e)


class AsyncButton:
    def __init__(self) -> None:
        self.on_click: typing.Optional[
            typing.Callable[[object], typing.Coroutine[None, None, None]]
        ] = None

    def click(self, e: object = None) -> None:
        if self.on_click is not None:
            asyncio.run(self.on_click(e))


@pytest.fixture
def sync_event_button() -> SyncButton:
    """Simulates a UI button that dispatches only sync on_click handlers."""
    return SyncButton()


@pytest.fixture
def async_event_button() -> AsyncButton:
    """Simulates a UI button that dispatches async on_click handlers."""
    return AsyncButton()


class TestProbeAllMethods:
    @pytest.mark.usefixtures("set_current_platform_to_linux")
    def test_returns_results_for_each_method(self, monkeypatch, testutils):
        testutils.empty_method_registry(monkeypatch)
        method_a = get_test_method_class(
            supported_platforms=(PlatformType.WINDOWS,),
            name="MethodA",
        )
        method_b = get_test_method_class(
            supported_platforms=(PlatformType.MACOS,),
            name="MethodB",
        )
        method_c = get_test_method_class(
            supported_platforms=(PlatformType.ANY,),
            name="MethodC",
            enter_mode=None,  # success
        )
        method_d = get_test_method_class(
            supported_platforms=(PlatformType.LINUX,),
            enter_mode=Exception("Failing on purpose"),
            name="MethodD",
        )

        params = _ModeParams(
            name="foo",
            method_classes=[method_a, method_b, method_c, method_d],
            methods_priority=["*"],
        )
        result = Mode(params).probe_all_methods()

        methods_text = result.get_summary_text(
            index_width=1,
            name_width=7,
            status_width=1,
        )
        assert (
            methods_text
            == """\
1. MethodC   SUCCESS
2. MethodD   FAIL
3. MethodA   *
4. MethodB   *"""
        )
        assert result.mode_name == "foo"


class TestModeContextManager:
    @pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
    def test_mode_contextmanager_protocol(
        self,
        mode0: Mode,
    ):
        """Test that the Mode fulfills the context manager protocol"""
        flag_end_of_with_block = False

        # Test that the context manager protocol works
        with mode0 as m:
            # The __enter__ returns the Mode
            assert m is mode0
            # We have activated the Mode
            assert mode0.active
            # There is an ActivationResult available in .result
            assert isinstance(m.result, ActivationResult)
            # The active method is also available
            assert isinstance(mode0._active_method, Method)

            activation_result = copy.deepcopy(m.result)
            flag_end_of_with_block = True

        # reached the end of the with block
        assert flag_end_of_with_block

        # After exiting the mode, Mode.active is set to None
        assert m.active is None
        # The active_method is set to None
        assert m.active_method is None
        # The activation result is still there (not removed during
        # deactivation)
        assert activation_result == m.result

    def test_active_is_none_before_activation(self, mode0: Mode):
        """Mode.active is None before entering the context manager"""
        assert mode0.active is None

    def test_active_is_false_on_failed_activation(self):
        """Mode.active is False when activation is attempted but fails"""
        params = _ModeParams(method_classes=[], on_fail="pass")
        mode = Mode(params)

        assert mode.active is None

        with mode as m:
            assert m.active is False

        assert m.active is None

    @pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
    def test_no_methods_succeeds_when_using_fake_success(
        self,
    ):
        # This will not fail as when the Mode is activated, the
        # WakepyFakeSuccess method is added to the list of used methods.
        params = _ModeParams(method_classes=[])
        with Mode(params):
            ...

    def test_active_method_and_method(self, methods_abc):
        """Test the .active_method and .method attributes"""

        [MethodA, MethodB, _] = methods_abc
        params = _ModeParams(method_classes=[MethodA, MethodB])
        mode = Mode(params)

        method_info_a = MethodInfo._from_method(MethodA())

        # before activated, active and used methods are None
        assert mode.active_method is None
        assert mode.method is None

        with mode:
            # When mode is active, active and used methods are same.
            assert mode.active_method == method_info_a
            assert mode.method == method_info_a

        # when mode is not active, active method is None, but used method is
        # the one used previously.
        assert mode.active_method is None
        assert mode.method == method_info_a


@pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
class TestUnsetCurrentMode:
    def test_runtime_error_if_exiting_without_active_mode(
        self,
        mode0: Mode,
    ):
        # Try to deactivate a mode when there's no active_method. Needed for
        # test coverage. A situation like this is unlikely to happen ever.
        with pytest.raises(
            RuntimeError,
            match="Cannot exit mode: TestMode. The active_method is None! This should never happen",  # noqa: E501
        ):
            with mode0:
                # Setting active method
                mode0._active_method = None

        # Need to manually cleanup after this test, as otherwise the global
        # state will not be correct. As said, this should never ever happen
        # in a real life situation.
        mode0._unset_current_mode()
        _mode_module._all_modes.remove(mode0)
        mode0._has_entered_context = False

    def test_unset_before_enter(
        self,
        mode0: Mode,
    ):
        with pytest.raises(
            RuntimeError,
            match="Cannot unset current mode, because it was never set! ",
        ):
            mode0._unset_current_mode()


class TestModeEnterExit:
    """Tests for Mode.enter and Mode.exit (public API)"""

    @pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
    def test_enter_exit_explicit_syntax(
        self,
        mode0: Mode,
        do_assert: typing.Callable[[bool], None],
    ):
        do_assert(mode0.active is None)
        mode0.enter()
        do_assert(mode0.active is True)
        mode0.exit()
        do_assert(mode0.active is None)

    @pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
    def test_enter_returns_activation_result(
        self,
        mode0: Mode,
    ):
        result = mode0.enter()
        assert isinstance(result, ActivationResult)
        mode0.exit()

    @pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
    def test_enter_twice_warns_by_default(
        self,
        mode0: Mode,
    ):
        # Default if_already_entered="warn": second enter() emits UserWarning
        mode0.enter()
        with pytest.warns(UserWarning, match="already active"):
            mode0.enter()
        mode0.exit()

    @pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
    def test_enter_twice_warn(
        self,
        mode0: Mode,
    ):
        # Explicit "warn"
        mode0.enter()
        with pytest.warns(UserWarning, match="already active"):
            mode0.enter(if_already_entered="warn")
        mode0.exit()

    @pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
    def test_enter_twice_raises_when_error(
        self,
        mode0: Mode,
    ):
        # if_already_entered="error": second enter() raises
        # ContextAlreadyEnteredError
        mode0.enter()
        with pytest.raises(
            ContextAlreadyEnteredError,
            match="A Mode can only be entered once!.*",
        ):
            mode0.enter(if_already_entered="error")
        mode0.exit()

    @pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
    def test_enter_twice_pass_is_silent(
        self,
        mode0: Mode,
    ):
        # if_already_entered="pass": second enter() is a silent no-op
        mode0.enter()
        with warnings.catch_warnings():
            warnings.simplefilter("error")  # raise error on any warnings
            mode0.enter(if_already_entered="pass")  # must not raise or warn
        mode0.exit()

    @pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
    def test_reenter_after_exit(
        self,
        mode0: Mode,
    ):
        """After exit, it should be possible to enter again."""
        mode0.enter()
        mode0.exit()

        mode0.enter()
        assert mode0.active is True
        mode0.exit()
        assert mode0.active is None

    @pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
    def test_event_driven_ui_pattern(
        self,
        mode0: Mode,
    ):
        """Test the event-driven UI pattern where enter/exit are
        called from separate callbacks (e.g. button clicks in a GUI app)."""

        # Simulates the state of a UI app
        status_text = ""

        def update_status() -> None:
            nonlocal status_text
            status_text = f"Wakelock enabled: {mode0.active}"

        def enable_lock() -> None:
            if mode0.active:
                return
            mode0.enter()
            update_status()

        def disable_lock() -> None:
            mode0.exit()
            update_status()

        # Initial state
        update_status()
        assert status_text == "Wakelock enabled: None"

        # Simulate "Enable" button click
        enable_lock()
        assert status_text == "Wakelock enabled: True"

        # Clicking "Enable" again should be a no-op
        enable_lock()
        assert status_text == "Wakelock enabled: True"

        # Simulate "Disable" button click
        disable_lock()
        assert status_text == "Wakelock enabled: None"

        # Re-enabling after disable should work
        enable_lock()
        assert status_text == "Wakelock enabled: True"
        disable_lock()
        assert status_text == "Wakelock enabled: None"

    @pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
    def test_event_driven_sync_handler_pattern(
        self,
        mode0: Mode,
        sync_event_button: SyncButton,
        do_assert: typing.Callable[[bool], None],
    ) -> None:
        """Sync on_click handlers can enter/exit a mode.

        Simulates a GUI framework (e.g. flet) where handlers are plain
        functions.
        """

        def sync_activate(e: object) -> None:
            mode0.enter()

        def sync_deactivate(e: object) -> None:
            mode0.exit()

        sync_event_button.on_click = sync_activate
        sync_event_button.click()
        do_assert(mode0.active is True)

        sync_event_button.on_click = sync_deactivate
        sync_event_button.click()
        do_assert(mode0.active is None)

        # Toggle again to confirm repeated use works
        sync_event_button.on_click = sync_activate
        sync_event_button.click()
        do_assert(mode0.active is True)
        mode0.exit()

    @pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
    def test_event_driven_async_handler_pattern(
        self,
        mode0: Mode,
        async_event_button: AsyncButton,
        do_assert: typing.Callable[[bool], None],
    ) -> None:
        """Async on_click handlers can enter/exit a mode.

        Simulates a GUI framework (e.g. flet) where handlers are async
        functions.
        """

        async def async_activate(e: object) -> None:
            mode0.enter()

        async def async_deactivate(e: object) -> None:
            mode0.exit()

        async_event_button.on_click = async_activate
        async_event_button.click()
        do_assert(mode0.active is True)

        async_event_button.on_click = async_deactivate
        async_event_button.click()
        do_assert(mode0.active is None)

        # Toggle again to confirm repeated use works
        async_event_button.on_click = async_activate
        async_event_button.click()
        do_assert(mode0.active is True)
        mode0.exit()

    @pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
    def test_enter_returns_same_result_instance_when_already_active(
        self,
        mode0: Mode,
    ) -> None:
        """enter() returns the exact same ActivationResult object each time
        while the mode is active; a new instance is created after exit."""
        res1 = mode0.enter()
        res2 = mode0.enter(if_already_entered="pass")
        assert res2 is res1  # same ActivationResult instance, not a copy

        mode0.exit()
        res3 = mode0.enter()
        assert res3 is not res1  # new ActivationResult after re-activation
        mode0.exit()

    def test_exit_when_never_entered(self, mode0: Mode):
        """exit() is a safe no-op when enter() was never called."""
        assert mode0.active is None
        mode0.exit()
        assert mode0.active is None

    def test_exit_after_failed_enter(self, mode0: Mode, monkeypatch):
        """exit() is a safe no-op after a failed enter()."""
        monkeypatch.setenv("WAKEPY_FORCE_FAILURE", "1")
        with pytest.warns(ActivationWarning):
            mode0.enter()

        assert mode0.active is False

        mode0.exit()  # must not raise
        assert mode0.active is None

    def test_exit_twice(self, mode0: Mode):
        """Second exit() is a safe no-op."""
        mode0.enter()
        mode0.exit()
        mode0.exit()  # must not raise
        assert mode0.active is None

    @pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
    def test_try_finally_pattern(self, mode0: Mode):
        """The documented try/finally pattern works correctly."""
        try:
            mode0.enter()
            raise RuntimeError("simulated error")
        except RuntimeError:
            pass
        finally:
            mode0.exit()

        assert mode0.active is None

    def test_enter_on_fail_error_succeeds(self):
        params = _ModeParams(method_classes=[], on_fail="error")
        mode = Mode(params)

        with pytest.raises(ActivationError):
            mode.enter()

        assert mode.active is False
        assert mode._has_entered_context
        mode.exit()

    def test_enter_on_fail_warn_succeeds(self):
        params = _ModeParams(method_classes=[], on_fail="warn")
        mode = Mode(params)

        with pytest.warns(ActivationWarning):
            mode.enter()

        assert mode.active is False
        assert mode._has_entered_context
        mode.exit()

    @pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
    def test_exit_when_not_in_all_modes(self, mode0: Mode) -> None:
        """exit() is safe if mode was removed from _all_modes."""

        mode0.enter()
        # Simulate an external removal from _all_modes (concurrent cleanup)
        _mode_module._all_modes.remove(mode0)
        # exit() must not raise even if self is not in _all_modes
        mode0.exit()
        assert mode0.active is None


@pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
class TestExitModeWithException:
    """Test cases when a Mode is exited with an Exception"""

    def test_mode_exits_with_modeexit(self, mode0: Mode):
        with mode0:
            testval = 2
            raise ModeExit
            testval = 0  # type: ignore # (never hit)

        assert testval == 2

    def test_mode_exits_with_modeexit_with_args(self, mode0: Mode):
        with mode0:
            testval = 3
            raise ModeExit("FOOO")
            testval = 0  # type: ignore # (never hit)

        assert testval == 3

    def test_mode_exits_with_other_exception(self, mode0: Mode):
        # Other exceptions are passed through
        class MyException(Exception): ...

        with pytest.raises(MyException):
            with mode0:
                testval = 4
                raise MyException
                testval = 0  # type: ignore # (never hit)

        assert testval == 4


class TestHandleActivationFail:
    """Tests for handle_activation_fail"""

    @staticmethod
    @pytest.fixture
    def result1():
        return ActivationResult([], mode_name="testmode")

    @staticmethod
    @pytest.fixture
    def error_text_match(result1):
        return re.escape(result1.get_failure_text())

    def test_pass(self, result1):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            handle_activation_fail(on_fail="pass", result=result1)

    def test_warn(self, result1, error_text_match):
        with pytest.warns(UserWarning, match=error_text_match):
            handle_activation_fail(on_fail="warn", result=result1)

    def test_error(self, result1, error_text_match):
        with pytest.raises(ActivationError, match=error_text_match):
            handle_activation_fail(on_fail="error", result=result1)

    def test_callable(self, result1):
        mock = Mock()
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            handle_activation_fail(on_fail=mock, result=result1)
        mock.assert_called_once_with(result1)

    def test_bad_on_fail_value(self, result1):
        with pytest.raises(ValueError, match="on_fail must be one of"):
            handle_activation_fail(
                on_fail="foo",  # type: ignore
                result=result1,
            )


@pytest.mark.usefixtures("provide_methods_a_f")
class TestSelectMethods:
    def test_filter_with_blacklist(self):
        (MethodB, MethodD, MethodE) = get_methods(["B", "D", "E"])
        methods = [MethodB, MethodD, MethodE]
        assert select_methods(methods, omit=["B"]) == [MethodD, MethodE]
        assert select_methods(methods, omit=["B", "E"]) == [MethodD]

    def test_extra_omit_does_not_matter(self):
        (MethodB, MethodD, MethodE) = get_methods(["B", "D", "E"])
        methods = [MethodB, MethodD, MethodE]
        # Extra 'omit' methods do not matter
        assert select_methods(methods, omit=["B", "E", "foo", "bar"]) == [
            MethodD,
        ]

    def test_filter_with_a_whitelist(self):
        (MethodB, MethodD, MethodE) = get_methods(["B", "D", "E"])
        methods = [MethodB, MethodD, MethodE]
        assert select_methods(methods, use_only=["B", "E"]) == [MethodB, MethodE]

    def test_whitelist_extras_causes_exception(self):
        (MethodB, MethodD, MethodE) = get_methods(["B", "D", "E"])
        methods = [MethodB, MethodD, MethodE]

        # If a whitelist contains extra methods, raise exception
        with pytest.raises(
            UnrecognizedMethodNames,
            match=re.escape(
                "Methods ['bar', 'foo'] in `use_only` are not part of `methods`!"
            ),
        ):
            select_methods(methods, use_only=["foo", "bar"])

    def test_cannot_provide_omit_and_use_only(self):
        (MethodB, MethodD, MethodE) = get_methods(["B", "D", "E"])
        methods = [MethodB, MethodD, MethodE]
        # Cannot provide both: omit and use_only
        with pytest.raises(
            ValueError,
            match=re.escape(
                "Can only define omit (blacklist) or use_only (whitelist), not both!"
            ),
        ):
            select_methods(methods, use_only=["B"], omit=["E"])


class TestActivateFirstSuccessfulMethod:
    def test_no_methods(self):
        # Act
        res, active_method, heartbeat = Mode._activate_first_successful_method(
            [], dbus_adapter=None
        )

        # Assert
        assert res == []
        assert active_method is None
        assert heartbeat is None

    def test_success(self):
        # Setup
        methodcls_fail = get_test_method_class(enter_mode=Exception("error"))
        methodcls_success = get_test_method_class(enter_mode=None)

        # Act
        res, active_method, heartbeat = Mode._activate_first_successful_method(
            [methodcls_success, methodcls_fail],
        )
        # Assert
        assert len(res) == 2
        assert res == [
            MethodActivationResult(
                method=MethodInfo._from_method(methodcls_success()),
                success=True,
            ),
            MethodActivationResult(
                method=MethodInfo._from_method(methodcls_fail()),
                success=None,
            ),
        ]
        assert isinstance(active_method, methodcls_success)
        assert heartbeat is None

    def test_success_with_heartbeat(self):
        # Setup
        methodcls_success_with_hb = get_test_method_class(
            enter_mode=None, heartbeat=None
        )

        # Act
        res, active_method, heartbeat = Mode._activate_first_successful_method(
            [methodcls_success_with_hb],
        )

        # Assert
        # The activation succeeded, and the method has heartbeat, so the
        # heartbeat must be instance of Heartbeate
        assert res == [
            MethodActivationResult(
                method=MethodInfo._from_method(methodcls_success_with_hb()),
                success=True,
            )
        ]
        assert isinstance(active_method, methodcls_success_with_hb)
        assert isinstance(heartbeat, Heartbeat)

    def test_failure(self):
        # Setup
        exc = Exception("error")
        methodcls_fail = get_test_method_class(enter_mode=exc)

        # Act
        res, active_method, heartbeat = Mode._activate_first_successful_method(
            [methodcls_fail]
        )

        # Assert
        # The activation failed, so active_method and heartbeat is None
        assert res == [
            MethodActivationResult(
                method=MethodInfo._from_method(methodcls_fail()),
                success=False,
                failure_stage=StageName.ACTIVATION,
                failure_reason=repr(exc),
            )
        ]
        assert active_method is None
        assert heartbeat is None
        assert heartbeat is None


class TestModeThreadSafety:
    """Tests for thread-safe enter/exit behavior."""

    @pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
    def test_concurrent_enter_exactly_one_succeeds(self, mode0: Mode) -> None:
        """Multiple threads calling enter() simultaneously: exactly one
        proceeds, the other gets a UserWarning and returns the existing
        result."""

        n_threads = 6
        barrier = threading.Barrier(n_threads)

        def worker() -> None:
            barrier.wait()
            mode0.enter(if_already_entered="warn")

        threads = [threading.Thread(target=worker) for _ in range(n_threads)]

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]

        # First one to enter had no warnings, and all the rest saw a warning.
        assert len(user_warnings) == n_threads - 1
        for w in user_warnings:
            assert "already active" in str(w.message)

        mode0.exit()

    @pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
    def test_concurrent_enter_pass_no_warning(self, mode0: Mode) -> None:
        """Multiple threads, if_already_entered='pass': no warnings, no
        errors."""
        n_threads = 6
        barrier = threading.Barrier(n_threads)

        def worker() -> None:
            barrier.wait()
            mode0.enter(if_already_entered="pass")

        threads = [threading.Thread(target=worker) for _ in range(n_threads)]

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]

        # No warning
        assert len(user_warnings) == 0

        mode0.exit()

    @pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
    def test_cross_thread_exit_does_not_crash(self, mode0: Mode) -> None:
        """enter() on thread A, exit() on thread B: no exception."""
        mode0.enter()
        assert mode0.active is True

        def deactivate_in_thread() -> None:
            mode0.exit()

        t = threading.Thread(target=deactivate_in_thread)
        t.start()
        t.join()

        assert mode0.active is None

    @pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
    def test_global_modes_reflects_manual_enter(self, mode0: Mode) -> None:
        """global_modes() and modecount() include manually-activated modes."""

        assert modecount() == 0
        mode0.enter()
        assert mode0 in global_modes()
        assert modecount() == 1
        mode0.exit()
        assert mode0 not in global_modes()
        assert modecount() == 0

    @pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
    def test_concurrent_enter_and_exit_no_crash(self, mode0: Mode) -> None:
        """Multiple threads calling enter() and exit() simultaneously
        must never crash or corrupt state — only clean exceptions allowed."""
        errors: list[Exception] = []
        barrier = threading.Barrier(6)

        def activator() -> None:
            barrier.wait()
            try:
                mode0.enter(if_already_entered="pass")
            except Exception as e:
                errors.append(e)

        def deactivator() -> None:
            barrier.wait()
            try:
                mode0.exit()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=activator) for _ in range(3)] + [
            threading.Thread(target=deactivator) for _ in range(3)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Unexpected errors from threads: {errors}"

    @pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
    def test_global_modes_visible_from_other_thread(self, mode0: Mode) -> None:
        """global_modes() from another thread returns the same result."""

        mode0.enter()

        results: queue.Queue[bool] = queue.Queue()

        def check_from_thread() -> None:
            results.put(mode0 in global_modes())

        t = threading.Thread(target=check_from_thread)
        t.start()
        t.join()

        assert results.get() is True
        mode0.exit()


class TestWakepyForceFailure:
    """Test WAKEPY_FORCE_FAILURE environment variable"""

    def test_force_failure_causes_activation_to_fail(
        self,
        monkeypatch,
        methods_abc: List[Type[Method]],
        testmode_cls: Type[Mode],
        dbus_adapter_cls: Type[DBusAdapter],
    ):
        """Test that WAKEPY_FORCE_FAILURE causes activation to fail"""
        monkeypatch.setenv("WAKEPY_FORCE_FAILURE", "1")

        params = _ModeParams(
            name="TestMode",
            method_classes=methods_abc,
            dbus_adapter=dbus_adapter_cls,
            methods_priority=["*"],
            on_fail="pass",
        )
        mode = testmode_cls(params)

        with mode as m:
            assert isinstance(m, Mode)
            assert m.result.success is False
            assert m.active is False

        self._assert_wakepy_force_failure(m.result, len(methods_abc))

    def test_both_env_vars_force_failure_wins(
        self,
        monkeypatch,
        methods_abc: List[Type[Method]],
        testmode_cls: Type[Mode],
        dbus_adapter_cls: Type[DBusAdapter],
    ):
        """Test that when both env vars set, WAKEPY_FORCE_FAILURE wins"""
        monkeypatch.setenv("WAKEPY_FAKE_SUCCESS", "1")
        monkeypatch.setenv("WAKEPY_FORCE_FAILURE", "1")

        params = _ModeParams(
            name="TestMode",
            method_classes=methods_abc,
            dbus_adapter=dbus_adapter_cls,
            methods_priority=["*"],
            on_fail="pass",
        )
        mode = testmode_cls(params)

        with mode as m:
            assert m.active is False  # WAKEPY_FORCE_FAILURE causes failure
            assert m.result.success is False

        self._assert_wakepy_force_failure(
            m.result,
            len(methods_abc) + 1,  # +1 for the WakepyFakeSuccess
        )

    @staticmethod
    def _assert_wakepy_force_failure(result: ActivationResult, n_methods: int):
        """Helper function to assert that only WAKEPY_FORCE_FAILURE caused
        failure"""

        failed = result.query()

        assert len(failed) == n_methods, f"Expecting {n_methods} failed methods"

        for res in failed:
            assert (
                res.failure_stage == StageName.WAKEPY_FORCE_FAILURE
            ), "Only WAKEPY_FORCE_FAILURE should cause failure"
            assert "WAKEPY_FORCE_FAILURE" in res.failure_reason


class TestSplitByPlatformSupport:
    @pytest.mark.parametrize(
        "current_platform",
        [
            IdentifiedPlatformType.WINDOWS,
            IdentifiedPlatformType.LINUX,
            IdentifiedPlatformType.UNKNOWN,
        ],
        indirect=["current_platform"],
    )
    def test_split_by_platform_support(
        self,
        current_platform,
    ):
        expected_supported, expected_unsupported = {
            IdentifiedPlatformType.WINDOWS: ({"windows", "any"}, {"linux"}),
            IdentifiedPlatformType.LINUX: ({"linux", "any"}, {"windows"}),
            IdentifiedPlatformType.UNKNOWN: (
                {"windows", "linux", "any"},
                set(),
            ),
        }[current_platform]
        windows_method = get_test_method_class(
            supported_platforms=(PlatformType.WINDOWS,)
        )
        linux_method = get_test_method_class(supported_platforms=(PlatformType.LINUX,))
        any_method = get_test_method_class(supported_platforms=(PlatformType.ANY,))
        methods = {
            "windows": windows_method,
            "linux": linux_method,
            "any": any_method,
        }

        possibly_supported, unsupported = Mode._split_by_platform_support(
            [windows_method, linux_method, any_method]
        )

        assert set(possibly_supported) == {methods[k] for k in expected_supported}
        assert set(unsupported) == {methods[k] for k in expected_unsupported}
