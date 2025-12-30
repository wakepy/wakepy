"""Separate tests for thread safety"""

from __future__ import annotations

import logging
import threading
import typing
from itertools import count
from threading import Lock

import pytest

from wakepy import (
    Method,
    Mode,
    NoCurrentModeError,
    current_mode,
    global_modes,
    keep,
    modecount,
)
from wakepy.core.constants import ModeName
from wakepy.core.mode import _all_modes

if typing.TYPE_CHECKING:
    from typing import List

lock = Lock()

# Prevent tests from running indefinitely
WAIT_TIMEOUT = 2


class MethodForTests(Method):
    counter = count()
    used_cookies: List[int] = []
    """keeps track of any cookies used by the any instance of the Method"""

    cookie: int | None

    def enter_mode(self):
        lock.acquire()
        try:
            self.cookie = next(self.counter)
        finally:
            lock.release()

    def exit_mode(self):
        if self.cookie is not None:
            lock.acquire()
            try:
                self.used_cookies.append(self.cookie)
                self.cookie = None
            finally:
                lock.release()
        else:
            raise RuntimeError("No cookie set yet!")


class MethodForThreadSafety(MethodForTests):
    mode_name = ModeName.KEEP_RUNNING
    name = "MethodForThreadSafety"


class MethodA(MethodForTests):
    mode_name = ModeName.KEEP_RUNNING
    name = "MethodA"


class MethodB(MethodForTests):
    mode_name = ModeName.KEEP_PRESENTING
    name = "MethodB"


def test_decorator_syntax_thread_safety():
    exit_event = threading.Event()

    @keep.running(methods=["MethodForThreadSafety"])
    def long_running_function():
        exit_event.wait(WAIT_TIMEOUT)  # Wait until the test is done

    # Act
    # Create multiple threads to run the long-running function
    # This will test if the wakepy mode can handle concurrent access.
    threads = []
    for _ in range(3):
        thread = threading.Thread(target=long_running_function)
        thread.start()
        threads.append(thread)

    # Cleanup
    exit_event.set()
    for thread in threads:
        thread.join()

    # Assert
    # Now, we need to check that the used method enter_mode and exit_mode
    # was called exactly once per thread, and that the used values were okay
    assert len(MethodForThreadSafety.used_cookies) == 3, "Not all cookies were used."
    assert len(set(MethodForThreadSafety.used_cookies)) == 3, "Cookies were not unique."


def test_global_modes():
    # Setup
    exit_event = threading.Event()
    ready_events = [threading.Event() for _ in range(3)]

    @keep.running(methods=["MethodForThreadSafety"])
    def long_running_function(event: threading.Event):
        event.set()  # Signal that the thread is ready
        exit_event.wait(WAIT_TIMEOUT)  # Wait until the test is done

    # Check that there are no modes before starting the threads
    assert len(global_modes()) == 0
    assert modecount() == 0

    # Act
    # Create multiple threads to run the long-running function
    # This will test if the wakepy mode can handle concurrent access.
    threads = []
    for event in ready_events:
        thread = threading.Thread(target=long_running_function, args=(event,))
        thread.start()
        threads.append(thread)

    # Wait until all threads are ready
    for event in ready_events:
        event.wait(WAIT_TIMEOUT)

    # Now there should be three active modes (on three threads)
    assert len(global_modes()) == 3
    assert modecount() == 3
    assert all(
        isinstance(m, Mode) for m in global_modes()
    ), "All modes should be instances of Mode."

    # Cleanup
    exit_event.set()
    for thread in threads:
        thread.join()

    # Assert that the cleanup worked.
    assert len(global_modes()) == 0
    assert modecount() == 0


class TestGetCurrentMode:
    def test_decorator_and_context_manager(self):
        """Test that the mode can be accessed from within the decorated
        function."""

        # Setup
        m_list: list[Mode] = []

        @keep.running(methods=["MethodA"])
        def long_running_function():
            # Using the keep.getcurrent_mode() to access the mode
            m = current_mode()
            m_list.append(m)
            assert len(global_modes()) == 1
            assert modecount() == 1

            with keep.presenting(methods=["MethodB"]):
                # This time should get different mode
                m = current_mode()
                m_list.append(m)
                assert len(global_modes()) == 2
                assert modecount() == 2

            m = current_mode()
            m_list.append(m)

        # Act
        long_running_function()

        # Assert
        assert isinstance(m_list[0], Mode), "Expected a Mode instance."
        assert m_list[0].name == ModeName.KEEP_RUNNING
        assert m_list[0].method
        assert m_list[0].method.name == "MethodA"

        assert len(m_list) == 3, "Expected three modes to be accessed."
        assert m_list[1].name == ModeName.KEEP_PRESENTING
        assert m_list[1].method
        assert m_list[1].method.name == "MethodB"

        # The first and last modes are the same
        assert m_list[0] is m_list[-1], "The first and last modes should be the same."

    def test_mode_access_in_subfunction(self):
        # Setup
        m_list = []

        def sub_function():
            try:
                m = current_mode()
            except NoCurrentModeError:
                m = None
            m_list.append(m)

        def long_running_function():
            sub_function()

            with keep.presenting(methods=["MethodB"]):
                sub_function()

            sub_function()

        # Act
        long_running_function()

        # Assert
        # No Mode activated
        assert m_list[0] is None

        assert m_list[1]
        assert m_list[1].name == ModeName.KEEP_PRESENTING
        assert m_list[1].method
        assert m_list[1].method.name == "MethodB"

        # No Mode activated
        assert m_list[2] is None

    def test_mode_access_when_no_modes_active(self):
        with pytest.raises(NoCurrentModeError):
            current_mode()


def test_decorator_syntax_without_parenthesis(monkeypatch):
    # Since we can't control which method is used, let's just make it use the
    # WAKEPY_FAKE_SUCCESS method, which is always successful.
    monkeypatch.setenv("WAKEPY_FAKE_SUCCESS", "1")

    @keep.running
    def long_running_function():
        assert modecount() == 1

    long_running_function()


def test_unset_current_mode(caplog):
    """This is pretty much a hypothetical situation; this test exists merely
    for test coverage."""

    # Setup
    mode = keep.running(methods=["MethodA"])
    mode.__enter__()
    # Manually remove the mode. Just to create the warning.
    _all_modes.remove(mode)

    # Act
    with caplog.at_level(logging.WARNING):
        mode.__exit__(None, None, None)

    # Assert
    assert caplog.text.startswith("WARNING ")
    assert (
        "was not found in _all_modes. This can happen if the Mode was not entered "
        "in the current thread or context, or if it was already removed." in caplog.text
    )
