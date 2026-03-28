from __future__ import annotations

import sys
import typing
from typing import overload

from ..core.constants import ModeName
from ..core.mode import Mode, ModeHook, ResultHook, create_mode_params

_MODE_DOCSTRING = """\
Create a wakepy Mode (a context manager / decorator) for %(mode_description)s.

➡️ :ref:`Documentation of %(mode_name)s mode. <%(mode_ref)s>` ⬅️

Parameters
----------
before_enter: callable or None
    Lifecycle hook called before mode activation begins. Receives the
    :class:`~wakepy.Mode` instance as parameter.
on_success: callable or None
    Called when mode activation succeeds. Receives an
    :class:`~wakepy.ActivationResult` as its single argument. When
    activation fails, ``on_fail`` is invoked instead.
on_fail: "error" | "warn" | callable or None
    Called when mode activation fails. If "error", raises
    :class:`~wakepy.ActivationError`. If "warn" (the default), issues a
    :class:`~wakepy.ActivationWarning`. If None, does nothing. If a
    callable, it is called with an :class:`~wakepy.ActivationResult` as
    its single argument.

    .. versionchanged:: 2.0.0
        ``None`` replaces the old ``"pass"`` option.
after_enter: callable or None
    Lifecycle hook called after mode activation completes (whether
    successful or failed). Receives the :class:`~wakepy.Mode` instance
    as parameter.
before_exit: callable or None
    Lifecycle hook called before mode deactivation begins. Receives the
    :class:`~wakepy.Mode` instance as parameter.
after_exit: callable or None
    Lifecycle hook called after mode deactivation completes. Receives the
    :class:`~wakepy.Mode` instance as parameter.
dbus_adapter: class or sequence of classes
    Optional argument which can be used to define a custom DBus adapter.
    If given, should be a subclass of :class:`~wakepy.DBusAdapter`, or a
    list of such.
methods: list, tuple or set of str
    The names of :ref:`Methods <wakepy-methods>` to select from the
    %(mode_name)s mode; a "whitelist" filter. Means "use these and only
    these Methods". Any Methods in `methods` but not in the %(mode_name)s
    mode will raise a ValueError. Cannot be used same time with `omit`.
    Optional.
omit: list, tuple or set of str or None
    The names of :ref:`Methods <wakepy-methods>` to remove from the
    %(mode_name)s mode; a "blacklist" filter. Any Method in `omit` but
    not in the %(mode_name)s mode will be silently ignored. Cannot be
    used same time with `methods`. Optional.
methods_priority: list[str | set[str]]
    The priority order for the methods to be used when entering the
    %(mode_name)s mode. You may use this parameter to force or suggest
    the order in which Methods are used. Any methods not explicitly
    supported by the current platform will automatically be unused (no need
    to add them here). The format is a list[str | set[str]], where each
    string is a Method name. Any method within a set will have equal
    user-given priority, and they are prioritized with the automatic
    prioritization rules. The first item in the list has the highest
    priority. All method names must be unique and must be part of the
    %(mode_name)s Mode.

    The asterisk ('*') can be used to mean "all other methods"
    and may occur only once in the priority order, and cannot be part of a
    set. If asterisk is not part of the `methods_priority`, it will be
    added as the last element automatically.

    See the :ref:`How to control order of Methods
    <how-to-control-order-of-methods>` section in the documentation for
    more information.

Returns
-------
Mode | func
    If not used as a decorator, returns a context manager :class:`Mode \\
    <wakepy.core.mode.Mode>` instance. If used as a decorator, returns a
    function that automatically enters the :ref:`%(mode_name)s \\
    <%(mode_ref)s>` mode when called (this automatically creates
    a new context manager and uses it).

Examples
--------
Using the :ref:`decorator syntax <decorator-syntax>`::

    from wakepy import keep

    @%(mode_name)s
    def long_running_function():
        # do something that takes a long time.

.. versionadded:: 1.0.0

    The :ref:`decorator syntax <decorator-syntax>` for `%(mode_name)s`
    was added in version 1.0.0.

Using the :ref:`context manager syntax <context-manager-syntax>`::

    from wakepy import keep

    with %(mode_name)s() as m:
        # do something that takes a long time.

"""

if typing.TYPE_CHECKING:
    from typing import Callable, Literal, Optional, Type

    from ..core.constants import StrCollection
    from ..core.dbus import DBusAdapter, DBusAdapterTypeSeq
    from ..core.mode import _ModeParams
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
    before_enter: ModeHook | None = ...,
    on_success: ResultHook | None = ...,
    on_fail: ResultHook | Literal["error", "warn"] | None = ...,
    after_enter: ModeHook | None = ...,
    before_exit: ModeHook | None = ...,
    after_exit: ModeHook | None = ...,
    dbus_adapter: Type[DBusAdapter] | DBusAdapterTypeSeq | None = ...,
    methods: Optional[StrCollection] = ...,
    omit: Optional[StrCollection] = ...,
    methods_priority: Optional[MethodsPriorityOrder] = ...,
) -> Mode: ...


def running(
    func: Callable[P, R] | None = None,
    *,
    before_enter: ModeHook | None = None,
    on_success: ResultHook | None = None,
    on_fail: ResultHook | Literal["error", "warn"] | None = "warn",
    after_enter: ModeHook | None = None,
    before_exit: ModeHook | None = None,
    after_exit: ModeHook | None = None,
    dbus_adapter: Type[DBusAdapter] | DBusAdapterTypeSeq | None = None,
    methods: Optional[StrCollection] = None,
    omit: Optional[StrCollection] = None,
    methods_priority: Optional[MethodsPriorityOrder] = None,
) -> Mode | Callable[P, R]:
    """%(docstring)s"""
    params = create_mode_params(
        mode_name=ModeName.KEEP_RUNNING,
        omit=omit,
        methods=methods,
        methods_priority=methods_priority,
        on_fail=on_fail,
        dbus_adapter=dbus_adapter,
        before_enter=before_enter,
        after_enter=after_enter,
        before_exit=before_exit,
        after_exit=after_exit,
        on_success=on_success,
    )

    return _get_keepawake(func, params)


running.__doc__ = (running.__doc__ or "") % {
    "docstring": _MODE_DOCSTRING
    % {
        "mode_name": "keep.running",
        "mode_ref": "keep-running-mode",
        "mode_description": "keeping programs running",
    }
}


@overload
def presenting(
    func: Callable[P, R],
) -> Callable[P, R]: ...


@overload
def presenting(
    *,
    before_enter: ModeHook | None = ...,
    on_success: ResultHook | None = ...,
    on_fail: ResultHook | Literal["error", "warn"] | None = ...,
    after_enter: ModeHook | None = ...,
    before_exit: ModeHook | None = ...,
    after_exit: ModeHook | None = ...,
    dbus_adapter: Type[DBusAdapter] | DBusAdapterTypeSeq | None = ...,
    methods: Optional[StrCollection] = ...,
    omit: Optional[StrCollection] = ...,
    methods_priority: Optional[MethodsPriorityOrder] = ...,
) -> Mode: ...


def presenting(
    func: Callable[P, R] | None = None,
    *,
    before_enter: ModeHook | None = None,
    on_success: ResultHook | None = None,
    on_fail: ResultHook | Literal["error", "warn"] | None = "warn",
    after_enter: ModeHook | None = None,
    before_exit: ModeHook | None = None,
    after_exit: ModeHook | None = None,
    dbus_adapter: Type[DBusAdapter] | DBusAdapterTypeSeq | None = None,
    methods: Optional[StrCollection] = None,
    omit: Optional[StrCollection] = None,
    methods_priority: Optional[MethodsPriorityOrder] = None,
) -> Mode | Callable[P, R]:
    """%(docstring)s"""
    params = create_mode_params(
        mode_name=ModeName.KEEP_PRESENTING,
        methods=methods,
        omit=omit,
        methods_priority=methods_priority,
        on_fail=on_fail,
        dbus_adapter=dbus_adapter,
        before_enter=before_enter,
        after_enter=after_enter,
        before_exit=before_exit,
        after_exit=after_exit,
        on_success=on_success,
    )
    return _get_keepawake(func, params)


presenting.__doc__ = (presenting.__doc__ or "") % {
    "docstring": _MODE_DOCSTRING
    % {
        "mode_name": "keep.presenting",
        "mode_ref": "keep-presenting-mode",
        "mode_description": "keeping a system running and showing content",
    }
}


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
