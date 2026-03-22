"""This module defines the Mode class and functions which may be used in the
activation and deactivation of Modes (using Methods).

Classes
-------
Mode:
    The main class of wakepy. Provides the entry point to any wakepy mode. A
    context manager, which enters the mode defined with one of the Methods
    given to it upon initialization.
"""

from __future__ import annotations

import logging
import threading
import typing
import warnings
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import wraps

from wakepy.core.constants import WAKEPY_FAKE_SUCCESS_METHOD, StageName
from wakepy.core.platform import CURRENT_PLATFORM, get_platform_supported

from .activationresult import (
    ActivationResult,
    MethodActivationResult,
    ProbingResults,
)
from .dbus import DBusAdapter, get_dbus_adapter
from .heartbeat import Heartbeat
from .method import Method, MethodInfo, activate_method, deactivate_method
from .prioritization import order_methods_by_priority
from .registry import get_method, get_methods_for_mode
from .utils import is_env_var_truthy

if typing.TYPE_CHECKING:
    import sys
    from contextvars import Token
    from types import TracebackType
    from typing import Callable, List, Optional, Tuple, Type, Union

    from .constants import Collection, ModeName, StrCollection
    from .dbus import DBusAdapter, DBusAdapterTypeSeq
    from .method import MethodCls
    from .prioritization import MethodsPriorityOrder

    if sys.version_info < (3, 8):  # pragma: no-cover-if-py-gte-38
        from typing_extensions import Literal
    else:  # pragma: no-cover-if-py-lt-38
        from typing import Literal

    if sys.version_info >= (3, 10):  # pragma: no-cover-if-py-gte-310
        from typing import ParamSpec, TypeVar
    else:  # pragma: no-cover-if-py-lt-310
        from typing_extensions import ParamSpec, TypeVar

    P = ParamSpec("P")
    R = TypeVar("R")

    OnFail = Union[Literal["error", "warn", "pass"], Callable[[ActivationResult], None]]

    IfAlreadyEntered = Literal["warn", "pass", "error"]

    MethodClsCollection = Collection[MethodCls]


logger = logging.getLogger(__name__)


class ActivationError(RuntimeError):
    """Raised if the activation of a :class:`Mode` is not successful and the
    on-fail action is to raise an Exception. See the ``on_fail`` parameter of
    the ``Mode`` constructor. This is a subclass of `RuntimeError <https://\
    docs.python.org/3/library/exceptions.html#RuntimeError>`_.
    """


class ActivationWarning(UserWarning):
    """Issued if the activation of a :class:`Mode` is not successful and the
    on-fail action is to issue a Warning. See the ``on_fail`` parameter of
    the ``Mode`` constructor. This is a subclass of `UserWarning <https://docs\
    .python.org/3/library/exceptions.html#UserWarning>`_.
    """


class NoMethodsWarning(UserWarning):
    """Issued if no methods are selected for a Mode; e.g. when user tries to
    activate a Mode using empty list as the methods. This is a subclass of
    `UserWarning <https://docs.python.org/3/library/exceptions.html#UserWarning>`_."""


class ModeExit(Exception):
    """This can be used to exit from any wakepy mode with block. Just raise it
    within any with block which is a wakepy mode, and no code below it will
    be executed.

    Examples
    --------
    You may use ``ModeExit`` to exit a with block, like this::

        with keep.running():

            # do something

            if SOME_CONDITION:
                print('failure')
                raise ModeExit
            print('success')

    This will print just "failure" if ``SOME_CONDITION`` is truthy, and
    just "success" in case it did succeed (never both).
    """


class ContextAlreadyEnteredError(RuntimeError):
    """Raised when :meth:`Mode.enter() <wakepy.Mode.enter>` is called on a
    Mode that is already active and ``if_already_entered="error"`` is passed.
    This is a subclass of `RuntimeError <https://docs.python.org/3/library/exceptions.html#RuntimeError>`_.

    .. versionadded:: 1.0.0

    .. versionchanged:: 2.0.0
        Previously raised unconditionally on double entry. Now only raised when
        ``if_already_entered="error"`` is explicitly passed to
        :meth:`Mode.enter() <wakepy.Mode.enter>`.

    .. seealso:: :meth:`Mode.enter() <wakepy.Mode.enter>`
    """


class NoCurrentModeError(RuntimeError):
    """Raised when trying to get the current mode but none is active.
    This is a subclass of `RuntimeError <https://docs.python.org/3/library/exceptions.html#RuntimeError>`_.

    .. versionadded:: 1.0.0

    .. seealso:: :func:`current_mode() <wakepy.current_mode>`
    """


@dataclass(frozen=True)
class _ModeParams:
    method_classes: list[Type[Method]] = field(default_factory=list)
    name: ModeName | str = "__unnamed__"
    methods_priority: Optional[MethodsPriorityOrder] = None
    use_only: Optional[StrCollection] = None
    omit: Optional[StrCollection] = None
    on_fail: OnFail = "warn"
    dbus_adapter: Type[DBusAdapter] | DBusAdapterTypeSeq | None = None


def create_mode_params(
    mode_name: ModeName | str,
    methods: Optional[StrCollection] = None,
    omit: Optional[StrCollection] = None,
    methods_priority: Optional[MethodsPriorityOrder] = None,
    on_fail: OnFail = "warn",
    dbus_adapter: Type[DBusAdapter] | DBusAdapterTypeSeq | None = None,
) -> _ModeParams:
    """Creates Mode parameters based on a mode name."""
    methods_for_mode = get_methods_for_mode(mode_name)
    logger.debug(
        'Found %d method(s) for mode "%s": %s',
        len(methods_for_mode),
        mode_name,
        methods_for_mode,
    )
    return _ModeParams(
        name=mode_name,
        method_classes=methods_for_mode,
        methods_priority=methods_priority,
        on_fail=on_fail,
        dbus_adapter=dbus_adapter,
        use_only=methods,
        omit=omit,
    )


def get_selected_methods(
    mode_name: ModeName | str,
    methods_for_mode: MethodClsCollection,
    methods: Optional[StrCollection] = None,
    omit: Optional[StrCollection] = None,
) -> List[MethodCls]:
    try:
        selected_methods = select_methods(methods_for_mode, use_only=methods, omit=omit)
    except UnrecognizedMethodNames as e:
        err_msg = (
            f'The following Methods are not part of the "{str(mode_name)}" Mode: '
            f"{e.missing_method_names}. Please check that the Methods are correctly"
            f' spelled and that the Methods are part of the "{str(mode_name)}" '
            "Mode. You may refer to full Methods listing at https://wakepy.readthedocs.io/stable/methods-reference.html."
        )
        raise UnrecognizedMethodNames(
            err_msg,
            missing_method_names=e.missing_method_names,
        ) from e

    selected_methods = select_methods(methods_for_mode, use_only=methods, omit=omit)

    logger.debug(
        'Selected %d method(s) for mode "%s": %s',
        len(selected_methods),
        mode_name,
        selected_methods,
    )
    if methods_for_mode and (not selected_methods):
        warn_text = (
            f'No methods selected for mode "{mode_name}"! This will lead to automatic failure of mode activation. '  # noqa E501
            f"To suppress this warning, select at least one of the available methods, which are: {methods_for_mode}"  # noqa E501
        )
        warnings.warn(warn_text, NoMethodsWarning, stacklevel=4)

    return selected_methods


# Storage for the currently active (innermost) Mode for the current thread and
# context.
_current_mode: ContextVar[Mode] = ContextVar("wakepy._current_mode")

# Lock for accessing the _all_modes
_mode_lock = threading.Lock()

# Global storage for all modes from all threads and contexts.
_all_modes: List[Mode] = []


def current_mode() -> Mode:
    """Gets the current :class:`Mode` instance for the current thread and
    context.

    Raises
    ------
    NoCurrentModeError
        If there are no Modes active in the call stack, raises a
        :class:`NoCurrentModeError`.

    Notes
    -----

    - This function cannot return any Modes from other threads. This means that
      even if you have entered a Mode in an another thread, but not in the
      current thread, this function will return ``None``
    - You may access the current :class:`Mode` instance from anywhere
      throughout the call stack, as long you are in the same thread and
      context.
    - You only need the :func:`current_mode` if you're using the decorator
      syntax, or if you're checking the mode within a function which is lower
      in the call stack.
    - Internally, a `ContextVar <https://docs.python.org/3/library/\
      contextvars.html#contextvars.ContextVar>`_. is used to store the
      current Mode instance for the current thread and context.

    Returns
    -------
    current_mode: Mode | None
        The current Mode instance for the thread and context. ``None``, if not
        entered in any Mode.


    Examples
    --------
    **Decorator syntax**: You may use this function to get the current
    :class:`Mode` instance, when using the :ref:`decorator syntax \\
    <decorator-syntax>`, like this::

        from wakepy import keep, current_mode

        @keep.presenting
        def long_running_function():
            m = current_mode()
            print(f"Used method is: {m.method}")

    **Deeper in the call stack**: You can also use this function to get the
    current :class:`Mode` instance in a function which is lower in the call
    stack, like this::

        from wakepy import keep, current_mode

        def long_running_function():
            with keep.presenting():
                sub_function()

        def sub_function():
            m = current_mode()
            print(f"Used method is: {m.method}")

    .. versionadded:: 1.0.0

    .. seealso:: :func:`global_modes() <wakepy.global_modes>`,
      :func:`modecount()  <wakepy.modecount>`,
      :ref:`multithreading-multiprocessing`
    """
    try:
        return _current_mode.get()
    except LookupError:
        raise NoCurrentModeError("No wakepy Modes active!")


def global_modes() -> List[Mode]:
    """Gets all the :class:`Mode` instances from all threads and active
    contexts for the current python process.

    While the :func:`current_mode` returns the innermost Mode for the
    current thread and context, this function returns all Modes from all
    threads and contexts.

    Returns
    -------
    all_modes: List[Mode]
        The list of all active wakepy :class:`Mode` instances from all threads
        and active contexts.

    .. versionadded:: 1.0.0

    .. seealso:: :func:`current_mode() <wakepy.current_mode>` for getting the
       current Mode instance and :func:`modecount() <wakepy.modecount>` for
       getting the number of all Modes from all threads and contexts.
    """
    _mode_lock.acquire()
    try:
        return _all_modes.copy()
    finally:
        _mode_lock.release()


def modecount() -> int:
    """The global mode count across all threads and contexts, for the current
    python process

    Returns
    -------
    mode_count: int
        The number of all Mode instances from all threads and active contexts.

    .. versionadded:: 1.0.0

    .. seealso:: :func:`current_mode() <current_mode>` for getting the current
        Mode instance and :func:`global_modes() <global_modes>` for getting all
        the Modes from all threads and contexts.
    """
    _mode_lock.acquire()
    try:
        return len(_all_modes)
    finally:
        _mode_lock.release()


def _handle_already_entered(
    if_already_entered: IfAlreadyEntered,
) -> None:
    """Handle the case when enter() is called on an already-entered Mode."""
    if if_already_entered == "pass":
        return
    elif if_already_entered == "warn":
        warnings.warn(
            "Mode is already active. Ignoring second enter() call. "
            "Pass if_already_entered='pass' to silence this warning.",
            UserWarning,
            stacklevel=3,
        )
    else:
        raise ContextAlreadyEnteredError(
            "A Mode can only be entered once! Use a separate Mode instance "
            "for each activation."
        )


class Mode:
    """Mode instances are the most important objects, and they provide the main
    API of wakepy for the user. Typically, :class:`Mode` instances are created
    with the factory functions like :func:`keep.presenting() \\
    <wakepy.keep.presenting>` and :func:`keep.running() <wakepy.keep.running>`

    There are three ways to use Mode instances:

    1. As :ref:`context managers <context-manager-syntax>`::

        with keep.running() as m:
            type(m) # <class 'wakepy.Mode'>
            # do something that takes a long time

    2. As :ref:`decorators <decorator-syntax>`::

        @keep.running
        def long_running_function():
            # do something that takes a long time

    3. With :ref:`explicit enter/exit <explicit-enter-exit-syntax>` — useful
       in event-driven apps or GUI frameworks where activation and deactivation
       happen in separate callbacks::

        mode = keep.running()
        try:
            mode.enter()
            # event loop, GUI mainloop, etc. (takes a long time)
        finally:
            mode.exit()  # safe even if enter() failed

    For more information about how to use the Mode instances, see the
    :ref:`user-guide-page`.
    """

    name: str | None
    """The name of the mode. Examples: "keep.running" for the
    :func:`keep.running <wakepy.keep.running>` mode and "keep.presenting"
    for the :func:`keep.presenting <wakepy.keep.presenting>` mode.
    """

    active: bool | None
    """Tells whether the mode is active.

    - ``None``: The Mode has not been activated yet, or has been deactivated.
    - ``True``: The Mode was activated successfully.
    - ``False``: The Mode was activated, but activation failed (no Method
      succeeded).

    When using the context manager or decorator syntax, this is always
    ``True`` or ``False`` during the active scope (inside the ``with``
    block or the decorated function).

    See also: :attr:`active_method`.

    .. versionchanged:: 2.0.0
        Changed from ``bool`` to ``bool | None``. The initial value and the
        value after deactivation is now ``None`` instead of ``False``.
    """

    result: ActivationResult
    """The activation result which tells more about the activation process
    outcome. See :class:`ActivationResult`.

    .. versionchanged:: 1.0.0
        Renamed from ``activation_result`` to ``result``.
    """

    method: MethodInfo | None
    """The :class:`MethodInfo` representing the currently used (active) or
    previously used (already deactivated) Method. ``None`` if the Mode has not
    ever been successfully activated. See also :attr:`active_method`.

    .. versionadded:: 1.0.0

        The ``method`` attribute was added in wakepy 1.0.0 to replace the
        deprecated :attr:`used_method` attribute. """

    active_method: MethodInfo | None
    """The :class:`MethodInfo` representing the currently used (active) Method.
    ``None`` if the Mode is not active. See also :attr:`used_method`.

    .. versionchanged:: 1.0.0

        The ``active_method`` is now a ``MethodInfo`` instance instead of
        a ``str`` representing the method name. """

    on_fail: OnFail
    """Tells what the mode does in case the activation fails. This can be
    "error", "warn", "pass" or a callable. If "error", raises
    :class:`ActivationError`. If "warn", issues a :class:`ActivationWarning`.
    If "pass", does nothing. If ``on_fail`` is a callable, it is called with
    an instance of :class:`ActivationResult`. For mode information, refer to
    the :ref:`on-fail-actions-section` in the user guide."""

    methods_priority: Optional[MethodsPriorityOrder]
    """The priority order for the methods to be used when entering the Mode.
    For more detailed explanation, see the ``methods_priority`` argument of the
    :func:`keep.presenting <wakepy.keep.presenting>` or :func:`keep.running \\
    <wakepy.keep.running>` factory functions.
    """

    def __init__(self, params: _ModeParams):
        r"""Initialize a Mode instance with the given parameters.

        Parameters
        ----------
        params: _ModeParams
            The parameters for the Mode.
        """

        logger.debug(
            'Creating wakepy Mode "%s" with methods=%s, omit=%s, methods_priority=%s, on_fail=%s, dbus_adapter=%s',  # noqa E501
            params.name,
            params.use_only,
            params.omit,
            params.methods_priority,
            params.on_fail,
            params.dbus_adapter,
        )

        self._init_params = params
        self.active: bool | None = None
        self.result = ActivationResult([])
        self.name = params.name

        self._method: Method | None = None
        """This holds the used method instance. The used method instance will
        not be set to None when deactivating."""
        self.method: MethodInfo | None = None

        self._active_method: Method | None = None
        """This holds the active method instance"""
        self.active_method: MethodInfo | None = None

        self.heartbeat: Heartbeat | None = None

        self._dbus_adapter_cls = params.dbus_adapter
        # Retrieved and updated using the _dbus_adapter property
        self._dbus_adapter_instance: DBusAdapter | None = None
        self._dbus_adapter_created: bool = False

        self._all_method_classes = params.method_classes
        """All Method classes for this Mode, regardless of what user has
        selected to use"""

        self._selected_method_classes = get_selected_methods(
            mode_name=params.name,
            methods_for_mode=params.method_classes,
            methods=params.use_only,
            omit=params.omit,
        )
        """The Method classes for this Mode that user has selected to use
        (either by whitelisting with "use_only" (="methods"), or by
        blacklisting with "omit" parameter)."""

        self.on_fail = params.on_fail
        self.methods_priority = params.methods_priority
        self._lock = threading.Lock()
        self._context_token: Optional[Token[Mode]] = None

        self._has_entered_context: bool = False
        """This is used to track if the mode has been entered already. Set to
        True when activated, and to False when deactivated. A bit different
        from `active`, because you might be entered into a mode which fails,
        so `active` can be False even if this is True. """

    def __call__(self, func: Callable[P, R]) -> Callable[P, R]:
        """Provides the decorator syntax for the KeepAwake instances."""

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Note that using `with self` would not work here as in multi-
            # threaded environment, the `self` would be shared between threads.
            # It would create multiple Mode instances on __enter__() but only
            # the last one would be set to be self._mode. During the
            # __exit__() the last Mode instance would be used on every thread.
            with Mode(self._init_params):
                retval = func(*args, **kwargs)
            return retval

        return wrapper

    def __enter__(self) -> Mode:
        """Called automatically when entering a with block and a instance of
        Mode is used as the context expression. This tries to enter the
        Mode using :attr:`~wakepy.Mode.method_classes`.
        """
        logger.debug(
            'Calling Mode.__enter__() for "%s" mode on object with id=%s, thread=%s',
            self.name,
            id(self),
            threading.get_ident(),
        )
        self.enter()
        self._set_current_mode()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exception: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> bool:
        """Called when exiting the with block.

        If with block completed normally, called with `(None, None, None)`
        If with block had an exception, called with `(exc_type, exc_value,
        traceback)`, which is the same as `*sys.exc_info`.

        Will swallow any ModeExit exception. Other exceptions will be
        re-raised.
        """

        # These are not used but are part of context manager protocol.
        # Make linters happy
        _ = exc_type
        _ = traceback

        logger.debug(
            'Calling Mode.__exit__() for "%s" mode on object with id=%s, thread=%s',
            self.name,
            id(self),
            threading.get_ident(),
        )
        self.exit()
        self._unset_current_mode()

        if exception is None or isinstance(exception, ModeExit):
            # Returning True means that the exception within the with block is
            # swallowed. We skip only ModeExit which should simply exit the
            # with block.
            return True

        # Other types of exceptions are not handled; ignoring them here and
        # returning False will tell python to re-raise the exception. Can't
        # return None as type-checkers would mark code after with block
        # unreachable.

        return False

    def enter(self, if_already_entered: IfAlreadyEntered = "warn") -> ActivationResult:
        """Enter the mode and try to activate it.

        Use this when a context manager is impractical — for example in
        event-driven applications or GUI frameworks where the activation and
        deactivation happen in separate callbacks (e.g. button clicks).

        For most use cases, the :ref:`context manager <context-manager-syntax>`
        or :ref:`decorator <decorator-syntax>` syntax are
        preferred::

            with keep.running():
                # your long-running work here

            @keep.running
            def long_running_task():
                # your long-running work here

        When ``enter()`` is used directly, user is responsible for ensuring
        that :meth:`exit` is guaranteed to run. Since :meth:`exit` is always a
        safe no-op (even if ``enter()`` was never called or failed), it can
        be called unconditionally in a ``finally`` block or cleanup handler.

        .. seealso:: :meth:`exit` — the counterpart that deactivates the mode.

        .. versionadded:: 2.0.0

        Parameters
        ----------
        if_already_entered : "warn", "pass" or "error". Defaults to "warn".
            Controls behavior when enter() is called on a Mode that is
            already entered. ``"warn"`` emits a UserWarning and returns the
            existing result (no-op). ``"pass"`` silently returns the existing
            result (no-op). ``"error"`` raises
            :class:`ContextAlreadyEnteredError`.

        Returns
        -------
        :class:`ActivationResult`
            The result of the activation. Check
            :attr:`ActivationResult.success` (or :attr:`active`) to see if
            activation succeeded.

        Warns
        -----
        UserWarning
            If the mode is already entered and ``if_already_entered="warn"``
            (the default). Pass ``if_already_entered="pass"`` to silence, or
            ``if_already_entered="error"`` to raise
            :class:`ContextAlreadyEnteredError` instead.

        Raises
        ------
        ContextAlreadyEnteredError
            If the mode has already been entered and
            ``if_already_entered="error"`` is passed.



        Examples
        --------
        Typical try/finally pattern for reliable cleanup::

            mode = keep.running()
            try:
                mode.enter()
                # your event loop, GUI mainloop, etc.
            finally:
                mode.exit()  # safe even if enter() failed

        The ``mode.exit()`` in the finally block guarantees that the mode is
        exited properly.
        """
        with self._lock:
            if self._has_entered_context:
                _handle_already_entered(if_already_entered)
                return self.result
            self._enter()

        if not self.active:
            handle_activation_fail(self.on_fail, self.result)

        return self.result

    def _enter(self) -> None:
        """Orchestrate full mode entry. Called with self._lock held."""
        self._has_entered_context = True
        possibly_supported, unsupported = self._get_supported_and_unsupported_methods()

        logger.info(
            'The full list of prioritized wakepy Methods for Mode "%s" is: %s',
            self.name,
            [m.name for m in possibly_supported],
        )
        logger.info(
            'Unsupported wakepy Methods on %s, "%s" Mode: %s',
            CURRENT_PLATFORM,
            self.name,
            [m.name for m in unsupported],
        )

        method_results = self._activate(possibly_supported)
        unsupported_results = self._create_unsupported_results(unsupported)
        self.result = ActivationResult(
            method_results + unsupported_results, mode_name=self.name
        )

        if self.active:
            with _mode_lock:
                _all_modes.append(self)
            logger.info(
                'Activated wakepy mode "%s" with method: %s',
                self.name,
                self.active_method,
            )
        else:
            logger.info(self.result.get_failure_text(style="inline"))

    def _activate(self, methods: List[Type[Method]]) -> List[MethodActivationResult]:
        """Try methods in order until the first success. Sets method state.

        Returns the list of :class:`MethodActivationResult` for all tried
        (and untried) methods. Does not include unsupported methods.
        """
        method_kwargs = self._get_method_kwargs()
        methodresults, self._active_method, self.heartbeat = (
            self._activate_first_successful_method(
                method_classes=methods, **method_kwargs
            )
        )
        self.active_method = (
            MethodInfo._from_method(self._active_method)
            if self._active_method
            else None
        )
        self.active = self._active_method is not None
        self._method = self._active_method
        self.method = self.active_method
        return methodresults

    def exit(self) -> None:
        """Exit the mode, and deactivates if it is active.

        This is the counterpart of :meth:`enter`. It is always safe to
        call — even if :meth:`enter` was never called, failed, or was
        already called once before. No guard like ``if mode.active:
        mode.exit()`` is needed.

        Put ``exit()`` unconditionally in a ``finally`` block or cleanup
        handler. See the try/finally pattern in :meth:`enter` for the
        recommended usage.

        .. seealso:: :meth:`enter` — the counterpart that enters the mode.

        .. versionadded:: 2.0.0


        """
        if not self._has_entered_context:
            return

        with self._lock:
            if self.active:
                if self._active_method is None:
                    raise RuntimeError(
                        f"Cannot exit mode: {str(self.name)}. "
                        "The active_method is None! This should never happen."
                    )
                deactivate_method(self._active_method, self.heartbeat)
            self._active_method = None
            self.active_method = None
            self.heartbeat = None
            self.active = None
            self._has_entered_context = False
            with _mode_lock:
                try:
                    _all_modes.remove(self)
                except ValueError:
                    pass  # defensive: already removed

    def probe_all_methods(self) -> ProbingResults:
        """Probe all methods for a mode.

        Unlike normal activation (which stops on first success and keeps method
        active), this tests all methods and deactivates each after testing.

        You can use this to see which methods would work on the current system
        (and which would not). The CLI command :ref:`wakepy methods \
        <wakepy-methods-cli>` uses this function internally.

        .. versionadded:: 1.0.0

        Returns
        -------
        :class:`ProbingResults`
            Result containing activation outcomes for each tested Method. Tells
            which Methods would work on the current system and which would not.
        """
        possibly_supported, unsupported = self._get_supported_and_unsupported_methods()

        method_kwargs = self._get_method_kwargs()
        results = self._try_to_activate_each(possibly_supported, **method_kwargs)

        platform_unsupported_results = self._create_unsupported_results(
            unsupported,
        )

        results.extend(platform_unsupported_results)
        return ProbingResults(results, mode_name=str(self.name))

    def _get_supported_and_unsupported_methods(
        self,
    ) -> Tuple[List[Type[Method]], List[Type[Method]]]:
        method_classes = self._add_fake_success_if_needed(self._selected_method_classes)
        ordered = order_methods_by_priority(method_classes, self.methods_priority)
        possibly_supported, unsupported = self._split_by_platform_support(ordered)
        return possibly_supported, unsupported

    def _set_current_mode(self) -> None:
        """Set this mode as current for the current thread and context.

        Does NOT add to _all_modes; that is handled by enter() so that
        manual enter()/exit() calls (without a context manager)
        also register correctly without double-counting.
        """
        self._context_token = _current_mode.set(self)

    def _unset_current_mode(self) -> None:
        """Unset this mode as current for the current thread and context.

        Does NOT remove from _all_modes; that is handled by exit().
        """
        if self._context_token is None:
            raise RuntimeError(  # should never happen
                "Cannot unset current mode, because it was never set! "
            )
        _current_mode.reset(self._context_token)

    def _add_fake_success_if_needed(
        self,
        method_classes: list[Type[Method]],
    ) -> list[Type[Method]]:
        methods = list(method_classes)
        if is_env_var_truthy("WAKEPY_FAKE_SUCCESS"):
            methods.insert(0, get_method(WAKEPY_FAKE_SUCCESS_METHOD))
            if is_env_var_truthy("WAKEPY_FORCE_FAILURE"):
                logger.warning(
                    "Both WAKEPY_FAKE_SUCCESS and WAKEPY_FORCE_FAILURE are set. "
                    "WAKEPY_FORCE_FAILURE takes precedence, so the activation will "
                    "be forced to fail. To remove this log message, unset "
                    "WAKEPY_FAKE_SUCCESS or set it to a falsy value."
                )
        return methods

    @staticmethod
    def _create_unsupported_results(
        unsupported_method_classes: list[Type[Method]],
    ) -> List[MethodActivationResult]:
        results: List[MethodActivationResult] = []
        for methodcls in unsupported_method_classes:
            method_info = MethodInfo(
                name=methodcls.name,
                mode_name=str(methodcls.mode_name),
                supported_platforms=methodcls.supported_platforms,
            )
            supported_platforms = ", ".join(methodcls.supported_platforms)
            results.append(
                MethodActivationResult(
                    method=method_info,
                    success=False,
                    failure_stage=StageName.PLATFORM_SUPPORT,
                    failure_reason=(
                        f"{methodcls.name} is not supported on {CURRENT_PLATFORM}. "
                        f"The supported platforms are: {supported_platforms}"
                    ),
                )
            )
        return results

    @staticmethod
    def _activate_first_successful_method(
        method_classes: list[Type[Method]],
        **method_kwargs: object,
    ) -> Tuple[List[MethodActivationResult], Optional[Method], Optional[Heartbeat]]:
        """Tries to activate methods in order, until the first successful one.

        If any of the Methods activate successfully, the Method is kept active.
        """

        results: List[MethodActivationResult] = []
        active_method: Optional[Method] = None
        heartbeat: Optional[Heartbeat] = None
        tried = 0

        # Find first successful method
        for cls in method_classes:
            method = cls(**method_kwargs)
            result, heartbeat = activate_method(method)
            results.append(result)
            tried += 1
            if result.success:
                active_method, heartbeat = method, heartbeat
                break

        # Unused methods
        for cls in method_classes[tried:]:
            methodinfo = MethodInfo(
                name=cls.name,
                mode_name=str(cls.mode_name),
                supported_platforms=cls.supported_platforms,
            )
            results.append(MethodActivationResult(method=methodinfo, success=None))

        return results, active_method, heartbeat

    @staticmethod
    def _try_to_activate_each(
        method_classes: list[Type[Method]],
        **method_kwargs: object,
    ) -> List[MethodActivationResult]:
        """Try to activate all the given Methods.

        If any Method activates successfully, deactivate it right after.
        Used for probing all methods to see which would work on the
        current system.
        """
        results: List[MethodActivationResult] = []
        for cls in method_classes:
            method = cls(**method_kwargs)
            result, heartbeat = activate_method(method)
            if result.success:
                deactivate_method(method, heartbeat)
            results.append(result)
        return results

    @staticmethod
    def _split_by_platform_support(
        method_classes: list[Type[Method]],
    ) -> Tuple[List[Type[Method]], List[Type[Method]]]:
        """Split methods into two groups based on platform support.

        Returns
        -------
        possibly_supported, unsupported: tuple of two lists
            First list contains methods supported on current platform or with
            unknown support. Second list contains methods definitely not
            supported on current platform.
        """
        possibly_supported: List[Type[Method]] = []
        unsupported: List[Type[Method]] = []
        for cls in method_classes:
            support = get_platform_supported(CURRENT_PLATFORM, cls.supported_platforms)
            if support is False:
                unsupported.append(cls)
            else:
                possibly_supported.append(cls)
        return possibly_supported, unsupported

    @property
    def _dbus_adapter(self) -> DBusAdapter | None:
        """The DbusAdapter instance of the Mode, if any. Created on the first
        call."""
        if not self._dbus_adapter_created:
            # Only do this once even if the returned instance is None, as this
            # might be a costly operation.
            self._dbus_adapter_instance = get_dbus_adapter(self._dbus_adapter_cls)
            self._dbus_adapter_created = True
        return self._dbus_adapter_instance

    def _get_method_kwargs(self) -> dict[str, object]:
        method_kwargs: dict[str, object] = {"dbus_adapter": self._dbus_adapter}
        return method_kwargs

    @property
    def activation_result(self) -> ActivationResult:  # pragma: no cover
        """
        .. deprecated:: 1.0.0
            Use :attr:`result` instead. This property will be removed in a
            future version of wakepy."""
        warnings.warn(
            "'Mode.activation_result' is deprecated in wakepy 1.0.0 and will be "
            "removed in a future version. Use 'Mode.result', instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.result

    @property
    def used_method(self) -> str | None:  # pragma: no cover
        """
        .. deprecated:: 1.0.0
            Use :attr:`method` instead. This property will be removed in a
            future version of wakepy."""
        warnings.warn(
            "'Mode.used_method' is deprecated in wakepy 1.0.0 and will be "
            "removed in a future version. Use 'Mode.method', instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.method.name if self.method else None


class UnrecognizedMethodNames(ValueError):
    """Raised if a method name is not recognized. This can happen if the
    method name is not part of the Methods used for a Mode. Typically this
    is caused by a typo, or mixing methods of different Modes (e.g.
    keep.presenting and keep.running).
    """

    def __init__(self, message: str, missing_method_names: StrCollection) -> None:
        """Initialize the UnrecognizedMethodName exception with a message."""
        super().__init__(message)
        self.message = message
        self.missing_method_names = missing_method_names


def select_methods(
    methods: MethodClsCollection,
    omit: Optional[StrCollection] = None,
    use_only: Optional[StrCollection] = None,
) -> List[MethodCls]:
    """Selects Methods from from `methods` using a blacklist (omit) or
    whitelist (use_only). If `omit` and `use_only` are both None, will return
    all the original methods.

    Parameters
    ----------
    methods: collection of Method classes
        The collection of methods from which to make the selection.
    omit: list, tuple or set of str or None
        The names of Methods to remove from the `methods`; a "blacklist"
        filter. Any Method in `omit` but not in `methods` will be silently
        ignored. Cannot be used same time with `use_only`. Optional.
    use_only: list, tuple or set of str
        The names of Methods to select from the `methods`; a "whitelist"
        filter. Means "use these and only these Methods". Any Methods in
        `use_only` but not in `methods` will raise a ValueError. Cannot
        be used same time with `omit`. Optional.

    Returns
    -------
    methods: list[MethodCls]
        The selected method classes.

    Raises
    ------
    ValueError if the input arguments (omit or use_only) are invalid.
    """

    if omit and use_only:
        raise ValueError(
            "Can only define omit (blacklist) or use_only (whitelist), not both!"
        )
    elif omit is None and use_only is None:
        selected_methods = list(methods)
    elif omit is not None:
        selected_methods = [m for m in methods if m.name not in omit]
    elif use_only is not None:
        selected_methods = [m for m in methods if m.name in use_only]
        if not set(use_only).issubset(m.name for m in selected_methods):
            missing = sorted(set(use_only) - set(m.name for m in selected_methods))
            raise UnrecognizedMethodNames(
                f"Methods {missing} in `use_only` are not part of `methods`!",
                missing_method_names=missing,
            )
    else:  # pragma: no cover
        raise ValueError("Invalid `omit` and/or `use_only`!")

    return selected_methods


def handle_activation_fail(on_fail: OnFail, result: ActivationResult) -> None:
    if on_fail == "pass":
        return
    elif on_fail == "warn":
        warnings.warn(
            result.get_failure_text(style="block"), ActivationWarning, stacklevel=5
        )
        return
    elif on_fail == "error":
        raise ActivationError(result.get_failure_text(style="block"))
    elif not callable(on_fail):
        raise ValueError(
            'on_fail must be one of "error", "warn", pass" or a callable which takes '
            "single positional argument (ActivationResult)"
        )
    on_fail(result)
