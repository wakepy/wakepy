"""Defines the SetThreadExecutionState based methods for Windows:
WindowsKeepRunning and WindowsKeepPresenting.

The Methods call the SetThreadExecutionState in a separate thread, making each
inhibition call isolated from each other.
"""

from __future__ import annotations

import ctypes
import enum
import logging
import threading
import typing
import warnings
from abc import ABC, abstractmethod
from queue import Queue
from threading import Event, Thread

from wakepy.core import Method, ModeName, PlatformType

logger = logging.getLogger(__name__)

# Different flags for WindowsSetThreadExecutionState
# See: https://docs.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setthreadexecutionstate
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002


class Flags(enum.IntFlag):
    KEEP_RUNNING = ES_CONTINUOUS | ES_SYSTEM_REQUIRED
    KEEP_PRESENTING = ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
    RELEASE = ES_CONTINUOUS


class WindowsSetThreadExecutionState(Method, ABC):
    """This is a method which calls the SetThreadExecutionState function from
    the kernel32.dll. The SetThreadExecutionState informs the system that it is
    in use preventing the system from entering sleep or turning off the display
    while the application is running" (depending on the used flags)."""

    # The SetThreadExecutionState docs say that it supports Windows XP and
    # above (client) or Windows Server 2003 and above (server)
    supported_platforms = (PlatformType.WINDOWS,)

    _wait_for_worker_timeout: float = 5  # seconds
    """timeout for waiting for the worker (inhibitor) thread on the main
    thread. For example for calls like queue.get() and thread.join() which
    could otherwise block execution indefinitely."""

    _release_event_timeout: int | float | None = None
    """Timeout in seconds used in the inhibitor thread (seconds). If the
    inhibitor is not shut down with a release event within the timeout, the
    thread is shut down automatically. None means "wait indefinitely". This
    variable exists mainly for tests (edit this to make tests not to wait
    forever in case of errors). """

    @property
    @abstractmethod
    def flags(self) -> Flags: ...

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._inhibiting_thread: Thread | None = None
        self._release = Event()
        self._queue_from_thread: Queue[int | Exception] = Queue()

    def enter_mode(self) -> None:
        # Because the ExecutionState flags are global per each thread, and
        # multiple wakepy modes might be activated simultaneously, we must
        # put all the SetThreadExecutionState inhibitor flags into separate
        # threads. See: https://github.com/wakepy/wakepy/issues/167
        self._inhibiting_thread = threading.Thread(
            target=_inhibit_until_released,
            kwargs=dict(
                inhibit_flags=self.flags,
                release_event=self._release,
                queue=self._queue_from_thread,
                release_event_timeout=self._release_event_timeout,
            ),
        )
        self._inhibiting_thread.start()
        self._check_thread_response()
        if not self._queue_from_thread.empty():  # pragma: no cover
            warnings.warn(
                "The queue from the inhibitor thread contained more than one respose! "
                "This most likely means that the thread exited before being released "
                "due to a small timeout value. This should never happen outside tests, "
                "and if this occurs in tests, it means that the _release_event_timeout "
                "is set too low!"
            )

    def exit_mode(self) -> None:
        self._release.set()
        self._check_thread_response()
        if self._inhibiting_thread:
            self._inhibiting_thread.join(timeout=self._wait_for_worker_timeout)
        self._inhibiting_thread = None

    def _check_thread_response(self) -> None:
        """Waits a message from the inhibitor thread queue. It should be an
        integer representing the previous thread execution state flags. If
        it's not, raises an Exception. Re-raises any Exceptions put into the
        queue.
        """
        res = self._queue_from_thread.get(timeout=self._wait_for_worker_timeout)

        if isinstance(res, int):
            logger.debug("The previous flags were %s (%s)", res, Flags(res))
            return  # success
        elif isinstance(res, Exception):
            # re-raise any exceptions occurred in the thread
            raise res
        raise RuntimeError(f"Unknown result type: {type(res)} ({res})")


def _inhibit_until_released(
    inhibit_flags: Flags,
    release_event: Event,
    queue: Queue[int | Exception],
    release_event_timeout: int | float | None = None,
) -> None:
    """Inhibit system using SetThreadExecutionState.

    First, uses SetThreadExecutionState and the given `inhibit_flags` to
    inhibit system. Then waits for a release event until release event timeout.
    The release event can be given from another thread. After released, calls
    SetThreadExecutionState once more to remove the inhibitor flag.

    Parameters
    ----------
    inhibit_flags:
        The flags to use for inhibition.
    release_event:
        The event to listen to. Inhibition will be active until the release
        event occurs, or until the `release_event_timeout` is reached. The
        event can be set from a different thread.
    queue:
        The Queue used to communicate from the inhibitor back to the user.
        The most important use case is to communicate any errors related to
        the inhibiti/uninhibit process.
    release_event_timeout:
        Timeout for the release event. If None, waits indefinitely. See also:
        `release_event`.

    """
    try:
        prev_flags = _call_set_thread_execution_state(inhibit_flags.value)
        queue.put(prev_flags)
    except Exception as exc:
        queue.put(exc)

    release_event.wait(release_event_timeout)

    try:
        prev_flags = _call_set_thread_execution_state(Flags.RELEASE.value)
        queue.put(prev_flags)
    except Exception as exc:
        queue.put(exc)


def _call_set_thread_execution_state(flags: int) -> int:
    """Call the SetThreadExecutionState with the given flags.

    Parameters
    ----------
    flags: int
        The flags to set. For example, KEEP_PRESENTING state is 2147483651
        and the RELEASE flags is 2147483648.

    Returns
    -------
    int:
        Flags value of the previous thread execution state as returned from the
        SetThreadExecutionState call.

    Raises
    ------
    RuntimeError:
        If the kernel32.dll is not found or if the SetThreadExecutionState
        returns NULL (0), indicating an error.
    """
    try:
        # This sets the return type to be unsigned 32-bit integer. Otherwise it
        # will be a signed 32-bit integer which is overflown. So for example
        # instead of returning 2147483649 it would return -2147483647.
        ctypes.windll.kernel32.SetThreadExecutionState.restype = ctypes.c_uint32  # type: ignore[attr-defined,unused-ignore]
        logger.debug(
            "Calling SetThreadExecutionState with flags: %s (%s)", flags, Flags(flags)
        )
        # The return value will be 0 in case of error, and the value of the
        # previous thread execution state otherwise.
        retval = ctypes.windll.kernel32.SetThreadExecutionState(flags)  # type: ignore[attr-defined,unused-ignore]
    except AttributeError as exc:
        raise RuntimeError("Could not use kernel32.dll!") from exc

    if retval == 0:
        raise RuntimeError("SetThreadExecutionState returned NULL")

    return typing.cast(int, retval)


class WindowsKeepRunning(WindowsSetThreadExecutionState):
    mode_name = ModeName.KEEP_RUNNING
    flags = Flags.KEEP_RUNNING
    name = "SetThreadExecutionState"


class WindowsKeepPresenting(WindowsSetThreadExecutionState):
    mode_name = ModeName.KEEP_PRESENTING
    flags = Flags.KEEP_PRESENTING
    name = "SetThreadExecutionState"
