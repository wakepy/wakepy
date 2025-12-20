from __future__ import annotations

import re
import sys
from unittest.mock import patch

import pytest

if sys.platform != "win32":
    pytest.skip(allow_module_level=True)

import wakepy.methods.windows as windows  # type: ignore[unreachable, unused-ignore]
from wakepy.methods.windows import Flags, WindowsKeepPresenting, WindowsKeepRunning

windows.WindowsSetThreadExecutionState._release_event_timeout = 0.5
"""Make tests *not* to wait forever. A too small value may cause flaky tests.
Previously, a value of 0.001 caused tests on PyPy on Windows to fail randomly.
See: https://github.com/wakepy/wakepy/pull/447
"""

patch_SetThreadExecutionState_working = patch(
    "wakepy.methods.windows.ctypes.windll.kernel32.SetThreadExecutionState",
    return_value=12345,
)
"""A patched version of ctypes.windll.kernel32.SetThreadExecutionState
which returns some sensible value and "works"."""


def raise_attribute_error(_):
    # Used for patching ctypes.windll.kernel32.SetThreadExecutionState
    # for some test cases. (It is possible that sometimes you'll get
    # an AttributeError when trying to use it.)
    raise AttributeError("foo")


class TestWindowsSetThreadExecutionState:

    @pytest.mark.parametrize(
        "method_cls_under_test",
        [WindowsKeepPresenting, WindowsKeepRunning],
    )
    @patch_SetThreadExecutionState_working
    def test_happy_path(self, set_thread_execution_state, method_cls_under_test):

        method = method_cls_under_test()

        # 1) Test entering the mode
        method.enter_mode()
        # Called the SetThreadExecutionState once
        assert len(set_thread_execution_state.mock_calls) == 1
        set_thread_execution_state.assert_called_once_with(method.flags.value)

        # 2) Test exiting the mode
        method.exit_mode()
        # We got second call to the SetThreadExecutionState
        assert len(set_thread_execution_state.mock_calls) == 2
        # This time, the call was with the RELEASE flag.
        set_thread_execution_state.assert_called_with(Flags.RELEASE.value)

    @pytest.mark.parametrize(
        "method_cls_under_test",
        [WindowsKeepPresenting, WindowsKeepRunning],
    )
    @patch(
        "wakepy.methods.windows.ctypes.windll.kernel32.SetThreadExecutionState",
        raise_attribute_error,
    )
    def test_enter_mode_with_exception(self, method_cls_under_test):
        # When the ctypes.windll.kernel32.SetThreadExecutionState throws an
        # Exception, we expect that the enter_mode() raises RuntimeError which
        # tells to the user that there was an error using the kernel32.dll
        method = method_cls_under_test()

        with pytest.raises(RuntimeError, match="Could not use kernel32.dll!"):
            method.enter_mode()

    @pytest.mark.parametrize(
        "method_cls_under_test",
        [WindowsKeepPresenting, WindowsKeepRunning],
    )
    def test_exit_mode_with_exception(self, method_cls_under_test):
        # If there would be an Exception raised in the inhibition thread
        # calling ctypes.windll.kernel32.SetThreadExecutionState for uninhibit
        # we would expect to see a RuntimeError while calling exit_mode().

        # Setup
        method = method_cls_under_test()
        with patch_SetThreadExecutionState_working:
            method.enter_mode()

        # Act
        with patch(
            "wakepy.methods.windows.ctypes.windll.kernel32.SetThreadExecutionState",
            raise_attribute_error,
        ):
            with pytest.raises(RuntimeError, match="Could not use kernel32.dll!"):
                method.exit_mode()

    @pytest.mark.parametrize(
        "method_cls_under_test",
        [WindowsKeepPresenting, WindowsKeepRunning],
    )
    def test_exit_mode_with_bad_return_value_from_thread(self, method_cls_under_test):

        # Setup
        method = method_cls_under_test()
        with patch_SetThreadExecutionState_working:
            method.enter_mode()

        # Act. returning 0 means returning NULL (error in a
        # SetThreadExecutionState call)
        with patch(
            "wakepy.methods.windows.ctypes.windll.kernel32.SetThreadExecutionState",
            return_value=0,
        ):
            with pytest.raises(
                RuntimeError, match="SetThreadExecutionState returned NULL"
            ):
                method.exit_mode()

    @pytest.mark.parametrize(
        "method_cls_under_test",
        [WindowsKeepPresenting, WindowsKeepRunning],
    )
    def test_exit_mode_before_enter(self, method_cls_under_test):
        # does not make much practical sense but required for test coverage
        method = method_cls_under_test()
        # need to add something to the queue; otherwise would wait until an
        # exception
        method._queue_from_thread.put(1)
        method.exit_mode()
        assert method._inhibiting_thread is None

    @pytest.mark.parametrize(
        "method_cls_under_test",
        [WindowsKeepPresenting, WindowsKeepRunning],
    )
    def test_wrong_return_type_from_set_thread_execution_state(
        self, method_cls_under_test
    ):
        # There's no real use case for this. This is basically for test
        # coverage.
        method = method_cls_under_test()

        with patch(
            "wakepy.methods.windows.ctypes.windll.kernel32.SetThreadExecutionState",
            return_value="foo",
        ), pytest.raises(
            RuntimeError,
            match=re.escape("Unknown result type: <class 'str'> (foo)"),
        ):
            method.enter_mode()
