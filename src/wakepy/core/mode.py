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
import os
import threading
import typing
import warnings
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import wraps

from wakepy.core.constants import FALSY_ENV_VAR_VALUES, WAKEPY_FAKE_SUCCESS

from .activationresult import ActivationResult, MethodActivationResult
from .dbus import DBusAdapter, get_dbus_adapter
from .heartbeat import Heartbeat
from .method import Method, MethodInfo, activate_method, deactivate_method
from .prioritization import order_methods_by_priority
from .registry import get_method, get_methods_for_mode

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


class ThreadSafetyWarning(UserWarning):
    """Issued if entering or exiting a Mode in a different thread than the one
    it was created in. This is a subclass of `UserWarning \\
    <https://docs.python.org/3/library/exceptions.html#UserWarning>`_.
    """


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
    """Raised if the context of a :class:`Mode` is already entered. This is a
    subclass of `RuntimeError <https://docs.python.org/3/library/exceptions.html#RuntimeError>`_.

    .. versionadded:: 1.0.0
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
    """The global mode count accross all threads and contexts, for the current
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


class Mode:
    """Mode instances are the most important objects, and they provide the main
    API of wakepy for the user. Typically, :class:`Mode` instances are created
    with the factory functions like :func:`keep.presenting() \\
    <wakepy.keep.presenting>` and :func:`keep.running() <wakepy.keep.running>`

    The Mode instances are `context managers \\
    <https://peps.python.org/pep-0343/>`_, which means that they can be used
    with the `with` statement, like this::

        with keep.running() as m:
            type(m) # <class 'wakepy.Mode'>

    The factory functions (and the Mode instances) are also decorators, which
    means you can also use them like this::

        @keep.running
        def long_running_function():
            # do something

    For more information about how to use the Mode instances, see the
    :ref:`user-guide-page`.
    """

    name: str | None
    """The name of the mode. Examples: "keep.running" for the
    :func:`keep.presenting <wakepy.keep.presenting>` mode and "keep.presenting"
    for the :func:`keep.running <wakepy.keep.running>` mode.
    """

    active: bool
    """``True`` if the mode is active. Otherwise, ``False``. See also:
    :attr:`active_method`."""

    result: ActivationResult
    """The activation result which tells more about the activation process
    outcome. See :class:`ActivationResult`.

    .. versionchanged:: 1.0.0
        Renamed from ``activation_result`` to ``result``.
    """

    method: MethodInfo | None
    """The :class:`MethodInfo` representing the currenly used (active) or
    previously used (already deactivated) Method. ``None`` if the Mode has not
    ever been succesfully activated. See also :attr:`active_method`.

    .. versionadded:: 1.0.0

        The ``method`` attribute was added in wakepy 1.0.0 to replace the
        deprecated :attr:`used_method` attribute. """

    active_method: MethodInfo | None
    """The :class:`MethodInfo` representing the currenly used (active) Method.
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
        self.active: bool = False
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
        self._thread_id = threading.get_ident()
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
        Mode is used as the context expression. This tries to activate the
        Mode using :attr:`~wakepy.Mode.method_classes`.
        """
        logger.debug(
            'Calling Mode.__enter__() for "%s" mode on object with id=%s, thread=%s',
            self.name,
            id(self),
            threading.get_ident(),
        )
        self._activate()
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
        #  make linters happy
        _ = exc_type
        _ = traceback

        logger.debug(
            'Calling Mode.__exit__() for "%s" mode on object with id=%s, thread=%s',
            self.name,
            id(self),
            threading.get_ident(),
        )
        self._deactivate()
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

    def _set_current_mode(self) -> None:
        self._context_token = _current_mode.set(self)
        try:
            _mode_lock.acquire()
            _all_modes.append(self)
        finally:
            _mode_lock.release()

    def _unset_current_mode(self) -> None:
        if self._context_token is None:
            raise RuntimeError(  # should never happen
                "Cannot unset current mode, because it was never set! "
            )
        _current_mode.reset(self._context_token)
        try:
            _mode_lock.acquire()
            try:
                _all_modes.remove(self)
            except ValueError:
                # This should never happen in practice.
                logger.warning(
                    'Mode "%s" with id=%s was not found in _all_modes. '
                    "This can happen if the Mode was not entered in the current "
                    "thread or context, or if it was already removed.",
                    self.name,
                    id(self),
                )
        finally:
            _mode_lock.release()

    def _activate(self) -> ActivationResult:
        """Activates the mode with one of the methods which belong to the mode.
        The methods are used with descending priority; highest priority first,
        and the priority is determined with the mode.methods_priority.

        The activation may be faked as to be successful by using the
        WAKEPY_FAKE_SUCCESS environment variable.
        """
        if self._has_entered_context:
            raise ContextAlreadyEnteredError(
                "A Mode can only be activated once! If "
                "you need to activate two Modes, you need to use two separate Mode "
                "instances."
            )
        self._thread_check()

        method_classes = add_fake_success_if_required(
            self._selected_method_classes, os.environ.get(WAKEPY_FAKE_SUCCESS)
        )
        method_classes_ordered = order_methods_by_priority(
            method_classes, self.methods_priority
        )

        logger.info(
            'Activating wakepy mode "%s". Will try the following methods in this order: %s',  # noqa E501
            self.name,
            [m.name for m in method_classes_ordered],
        )
        methodresults, self._active_method, self.heartbeat = (
            self._activate_one_of_methods(
                method_classes=method_classes_ordered,
                dbus_adapter=self._dbus_adapter,
            )
        )
        self.active_method = (
            MethodInfo._from_method(self._active_method)
            if self._active_method
            else None
        )

        self.result = ActivationResult(methodresults, mode_name=self.name)
        self.active = self.result.success
        self._method = self._active_method
        self.method = self.active_method

        if self.active:
            logger.info(
                'Activated wakepy mode "%s" with method: %s',
                self.name,
                self.active_method,
            )
        else:
            logger.info(
                self.result.get_failure_text(newlines=False),
            )

        if not self.active:
            handle_activation_fail(self.on_fail, self.result)

        self._has_entered_context = True
        return self.result

    @staticmethod
    def _activate_one_of_methods(
        method_classes: list[Type[Method]], **method_kwargs: object
    ) -> Tuple[List[MethodActivationResult], Optional[Method], Optional[Heartbeat]]:
        """Activates mode using the first Method in `method_classes` which
        succeeds. The methods are tried in the order given in `method_classes`
        argument.

        Parameters
        ----------
        method_classes:
            The list of Methods to be used for activating this Mode.
        method_kwargs:
            optional kwargs passed to the all the Method class constructors.

        Returns
        -------
        List[MethodActivationResult], Optional[Method], Optional[Heartbeat]
            A three-tuple: The list of method activation results, the activated
            method (None if not any), the activated heartbeat (None if not
            any).
        """

        methodresults = []
        while method_classes:
            methodcls = method_classes.pop(0)
            active_method = methodcls(**method_kwargs)
            methodresult, heartbeat = activate_method(active_method)
            methodresults.append(methodresult)
            if methodresult.success:
                break
        else:
            # Tried activate with all methods, but none of them succeed
            active_method, heartbeat = None, None

        # Add unused methods to the results
        for methodcls in method_classes:
            unused_method = methodcls(**method_kwargs)
            method_info = MethodInfo._from_method(unused_method)
            methodresults.append(
                MethodActivationResult(method=method_info, success=None)
            )

        return methodresults, active_method, heartbeat

    def _deactivate(self) -> bool:
        """Deactivates the active mode, defined by the active Method, if any.
        If there was no active method, does nothing.

        Returns
        -------
        deactivated:
            If there was no active method, returns False (nothing was done).
            If there was an active method, and it was deactivated, returns True

        Raises
        ------
        RuntimeError, if there was active method but an error occurred when
        trying to deactivate it."""

        self._thread_check()

        if self.active:
            if self._active_method is None:
                raise RuntimeError(
                    f"Cannot deactivate mode: {str(self.name)}. The active_method is None! This should never happen."  # noqa E501
                )
            deactivate_method(self._active_method, self.heartbeat)
            deactivated = True
        else:
            deactivated = False

        self._active_method = None
        self.active_method = None
        self.heartbeat = None
        self.active = False
        self._has_entered_context = False
        return deactivated

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

    def _thread_check(self) -> None:
        current_thread_id = threading.get_ident()
        if self._thread_id != current_thread_id:

            warning_text = (
                f"Using the Mode {self.name} with id ({id(self)}) in thread "
                f"{current_thread_id} but it was created in thread {self._thread_id}. "
                "Wakepy Modes are not thread-safe!"
            )
            warnings.warn(warning_text, ThreadSafetyWarning, stacklevel=2)
            logger.warning(warning_text)

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
        `use_only` but not in `methods` will raise a ValueErrosr. Cannot
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


def add_fake_success_if_required(
    method_classes: List[Type[Method]], wakepy_fake_success: str | None
) -> List[Type[Method]]:
    """Adds the WAKEPY_FAKE_SUCCESS method to the list of method classes, if
    the WAKEPY_FAKE_SUCCESS environment variable has been set into a non-falsy
    value. See also: `should_fake_success`.

    Parameters
    ----------
    method_classes:
        The list of method classes
    wakepy_fake_success:
        Value read from WAKEPY_FAKE_SUCCESS environment variable; either None
        or a string. For example: '0', '1', 'True', or 'False'. None has same
        behavior as falsy values ('0', 'no', 'false', 'f', 'n', '').
    """
    if not should_fake_success(wakepy_fake_success):
        return method_classes

    return [get_method(WAKEPY_FAKE_SUCCESS)] + method_classes


def should_fake_success(wakepy_fake_success: str | None) -> bool:
    """Function which says if fake success should be enabled

    Parameters
    ----------
    wakepy_fake_success:
        Value read from WAKEPY_FAKE_SUCCESS environment variable; either None
        or a string. For example: '0', '1', 'True', or 'False'. None has same
        behavior as falsy values ('0', 'no', 'false', 'f', 'n', '').

    Returns
    -------
    fake_success_enabled:
        True, if fake success is enabled, False otherwise.

    Motivation
    ----------
    When running on CI system, wakepy might fail to acquire an inhibitor
    lock just because there is no Desktop Environment running. In these
    cases, it might be useful to just tell with an environment variable
    that wakepy should fake the successful inhibition anyway. Faking the
    success is done after every other method is tried (and failed).
    """

    if wakepy_fake_success is None:
        logger.debug("'%s' not set.", WAKEPY_FAKE_SUCCESS)
        return False

    if wakepy_fake_success.lower() in FALSY_ENV_VAR_VALUES:
        logger.info(
            "'%s' set to a falsy value: %s.", WAKEPY_FAKE_SUCCESS, wakepy_fake_success
        )
        return False

    logger.info(
        "'%s' set to a truthy value: %s.", WAKEPY_FAKE_SUCCESS, wakepy_fake_success
    )
    return True


def handle_activation_fail(on_fail: OnFail, result: ActivationResult) -> None:
    if on_fail == "pass":
        return
    elif on_fail == "warn":
        warnings.warn(result.get_failure_text(), ActivationWarning, stacklevel=5)
        return
    elif on_fail == "error":
        raise ActivationError(result.get_failure_text())
    elif not callable(on_fail):
        raise ValueError(
            'on_fail must be one of "error", "warn", pass" or a callable which takes '
            "single positional argument (ActivationResult)"
        )
    on_fail(result)
