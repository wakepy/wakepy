from __future__ import annotations

import sys
import typing
from typing import overload

from ..core.constants import ModeName
from ..core.mode import Mode, create_mode_params

if typing.TYPE_CHECKING:
    from typing import Callable, Optional, Type

    from ..core.constants import StrCollection
    from ..core.dbus import DBusAdapter, DBusAdapterTypeSeq
    from ..core.mode import OnFail, _ModeParams
    from ..core.prioritization import MethodsPriorityOrder

    if sys.version_info >= (3, 10):  # pragma: no-cover-if-py-gte-310
        from typing import ParamSpec, TypeVar
    else:  # pragma: no-cover-if-py-lt-310
        from typing_extensions import ParamSpec, TypeVar

    P = ParamSpec("P")
    R = TypeVar("R")


@overload
def running(
    func: Callable[P, R],
) -> Callable[P, R]: ...


@overload
def running(
    *,
    methods: Optional[StrCollection] = ...,
    omit: Optional[StrCollection] = ...,
    methods_priority: Optional[MethodsPriorityOrder] = ...,
    on_fail: OnFail = ...,
    dbus_adapter: Type[DBusAdapter] | DBusAdapterTypeSeq | None = ...,
) -> Mode: ...


def running(
    func: Callable[P, R] | None = None,
    *,
    methods: Optional[StrCollection] = None,
    omit: Optional[StrCollection] = None,
    methods_priority: Optional[MethodsPriorityOrder] = None,
    on_fail: OnFail = "warn",
    dbus_adapter: Type[DBusAdapter] | DBusAdapterTypeSeq | None = None,
) -> Mode | Callable[P, R]:
    """
    Create a wakepy Mode (a context manager / decorator) for keeping
    programs running.

    ➡️ :ref:`Documentation of keep.running mode. <keep-running-mode>` ⬅️

    Parameters
    ----------
    methods: list, tuple or set of str
        The names of :ref:`Methods <wakepy-methods>` to select from the
        keep.running mode; a "whitelist" filter. Means "use these and only
        these Methods". Any Methods in `methods` but not in the keep.running
        mode will raise a ValueError. Cannot be used same time with `omit`.
        Optional.
    omit: list, tuple or set of str or None
        The names of :ref:`Methods <wakepy-methods>`  to remove from the
        keep.running mode; a "blacklist" filter. Any Method in `omit` but not
        in the keep.running mode will be silently ignored. Cannot be used same
        time with `methods`. Optional.
    methods_priority: list[str | set[str]]
        The priority order for the methods to be used when entering the
        keep.running mode. You may use this parameter to force or suggest the
        order in which Methods are used. Any methods not explicitly supported
        by the current platform will automatically be unused (no need to add
        them here). The format is a list[str | set[str]], where each
        string is a Method name. Any method within a set will have equal
        user-given priority, and they are prioritized with the automatic
        prioritization rules. The first item in the list has the highest
        priority. All method names must be unique and must be part of the
        keep.running Mode.

        The asterisk ('*') can be used to mean "all other methods"
        and may occur only once in the priority order, and cannot be part of a
        set. If asterisk is not part of the `methods_priority`, it will be
        added as the last element automatically.
    on_fail: "error" | "warn" | "pass" | Callable
        Determines what to do in case mode activation fails. Valid options
        are: "error", "warn", "pass" and a callable. If the option is
        "error", raises :class:`~wakepy.ActivationError`. Is selected "warn",
        issues a :class:`~wakepy.ActivationWarning`. If "pass", does nothing.
        If ``on_fail`` is a callable, it must take one positional argument:
        result, which is an instance of :class:`~wakepy.ActivationResult`. The
        ActivationResult contains more detailed information about the
        activation process.
    dbus_adapter: class or sequence of classes
        Optional argument which can be used to define a custom DBus adapter.
        If given, should be a subclass of :class:`~wakepy.DBusAdapter`, or a
        list of such.

    Returns
    -------
    Mode | func
        If not used as a decorator, returns a context manager :class:`Mode \\
        <wakepy.core.mode.Mode>` instance. If used as a decorator, returns a
        function that automatically enters the :ref:`keep.running \\
        <keep-running-mode>` mode when called (this automatically creates
        a new context manager and uses it).

    Examples
    --------
    Using the :ref:`decorator syntax <decorator-syntax>`::

        from wakepy import keep

        @keep.running
        def long_running_function():
            # do something that takes a long time.

    .. versionadded:: 1.0.0

        The :ref:`decorator syntax <decorator-syntax>` for `keep.running`
        was added in version 1.0.0.

    Using the :ref:`context manager syntax <context-manager-syntax>`::

        from wakepy import keep

        with keep.running() as m:
            # do something that takes a long time.

    """
    params = create_mode_params(
        mode_name=ModeName.KEEP_RUNNING,
        omit=omit,
        methods=methods,
        methods_priority=methods_priority,
        on_fail=on_fail,
        dbus_adapter=dbus_adapter,
    )

    return _get_keepawake(func, params)


@overload
def presenting(
    func: Callable[P, R],
) -> Callable[P, R]: ...


@overload
def presenting(
    *,
    methods: Optional[StrCollection] = ...,
    omit: Optional[StrCollection] = ...,
    methods_priority: Optional[MethodsPriorityOrder] = ...,
    on_fail: OnFail = ...,
    dbus_adapter: Type[DBusAdapter] | DBusAdapterTypeSeq | None = ...,
) -> Mode: ...


def presenting(
    func: Callable[P, R] | None = None,
    *,
    methods: Optional[StrCollection] = None,
    omit: Optional[StrCollection] = None,
    methods_priority: Optional[MethodsPriorityOrder] = None,
    on_fail: OnFail = "warn",
    dbus_adapter: Type[DBusAdapter] | DBusAdapterTypeSeq | None = None,
) -> Mode | Callable[P, R]:
    """Create a wakepy mode (a context manager / decorator) for keeping a
    system running and showing content.

    ➡️ :ref:`Documentation of keep.presenting mode. <keep-presenting-mode>` ⬅️

    Parameters
    ----------
    methods: list, tuple or set of str
        The names of :ref:`Methods <wakepy-methods>`  to select from the
        keep.presenting mode; a "whitelist" filter. Means "use these and only
        these Methods". Any Methods in `methods` but not in the keep.presenting
        mode will raise a ValueError. Cannot be used same time with `omit`.
        Optional.
    omit: list, tuple or set of str or None
        The names of :ref:`Methods <wakepy-methods>` to remove from the
        keep.presenting mode; a "blacklist" filter. Any Method in `omit` but
        not in the keep.presenting mode will be silently ignored. Cannot be
        used same time with `methods`. Optional.
    methods_priority: list[str | set[str]]
        The priority order for the methods to be used when entering the
        keep.presenting mode. You may use this parameter to force or suggest
        the order in which Methods are used. Any methods not explicitly
        supported by the current platform will automatically be unused (no need
        to add them here). The format is a list[str | set[str]], where each
        string is a Method name. Any method within a set will have equal
        user-given priority, and they are prioritized with the automatic
        prioritization rules. The first item in the list has the highest
        priority. All method names must be unique and must be part of the
        keep.presenting Mode.

        The asterisk ('*') can be used to mean "all other methods"
        and may occur only once in the priority order, and cannot be part of a
        set. If asterisk is not part of the `methods_priority`, it will be
        added as the last element automatically.
    on_fail: "error" | "warn" | "pass" | Callable
        Determines what to do in case mode activation fails. Valid options
        are: "error", "warn", "pass" and a callable. If the option is
        "error", raises :class:`~wakepy.ActivationError`. Is selected "warn",
        issues a :class:`~wakepy.ActivationWarning`. If "pass", does nothing.
        If ``on_fail`` is a callable, it must take one positional argument:
        result, which is an instance of :class:`~wakepy.ActivationResult`. The
        ActivationResult contains more detailed information about the
        activation process.
    dbus_adapter: class or sequence of classes
        Optional argument which can be used to define a custom DBus adapter.
        If given, should be a subclass of :class:`~wakepy.DBusAdapter`, or a
        list of such.

    Returns
    -------
    Mode | func
        If not used as a decorator, returns a context manager :class:`Mode \\
        <wakepy.core.mode.Mode>` instance. If used as a decorator, returns a
        function that automatically enters the :ref:`keep.presenting \\
        <keep-presenting-mode>` mode when called (this automatically creates
        a new context manager and uses it).

    Examples
    --------
    Using the :ref:`decorator syntax <decorator-syntax>`::

        from wakepy import keep

        @keep.presenting
        def long_running_function():
            # do something that takes a long time.

    .. versionadded:: 1.0.0

        The :ref:`decorator syntax <decorator-syntax>` for `keep.presenting`
        was added in version 1.0.0.

    Using the :ref:`context manager syntax <context-manager-syntax>`::

        from wakepy import keep

        with keep.presenting() as m:
            # do something that takes a long time.

    """
    params = create_mode_params(
        mode_name=ModeName.KEEP_PRESENTING,
        methods=methods,
        omit=omit,
        methods_priority=methods_priority,
        on_fail=on_fail,
        dbus_adapter=dbus_adapter,
    )
    return _get_keepawake(func, params)


def _get_keepawake(
    func: Callable[P, R] | None,
    params: _ModeParams,
) -> Mode | Callable[P, R]:
    if func is not None and callable(func):
        # Used as @keep.xxx; decorator without parameters
        return Mode(params)(func)
    # Used as @keep.xxx(...) or keep.xxx(); decorator with parameters
    # or a context manager
    return Mode(params)
