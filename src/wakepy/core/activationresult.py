"""This module defines the activation result classes.


Most important classes
----------------------
ActivationResult
    This is something returned from mode activation task. Contains the summary
    of all used methods, and whether the activation was successful or not.
MethodActivationResult
    One level lower than ActivationResult. This is result from activation task
    using a single Method.
"""

from __future__ import annotations

import sys
import textwrap
import typing
import warnings
from dataclasses import InitVar, dataclass, field
from typing import List, Sequence

from .constants import WAKEPY_FAKE_SUCCESS_METHOD, StageName, StageNameValue

if sys.version_info < (3, 8):  # pragma: no-cover-if-py-gte-38
    from typing_extensions import Literal
else:  # pragma: no-cover-if-py-lt-38
    from typing import Literal

FailureTextStyle = Literal["block", "inline"]


if typing.TYPE_CHECKING:
    from typing import List, Optional, Tuple

    from .method import MethodInfo


@dataclass
class _BaseActivationResult:
    """Base class for activation result classes. Contains shared functionality
    for querying and formatting method activation results.

    This is a private class and should not be used directly.
    """

    results: InitVar[List[MethodActivationResult]]

    _method_results: List[MethodActivationResult] = field(init=False, repr=False)

    success: bool = field(init=False)
    """Tells if entering into a mode was successful. Note that this may be
    faked with :ref:`WAKEPY_FAKE_SUCCESS` environment variable e.g. for testing
    purposes.

    See Also
    --------
    real_success, failure, get_failure_text
    """

    real_success: bool = field(init=False)
    """Tells if entering into a mode was successful. This may not be faked with
    the :ref:`WAKEPY_FAKE_SUCCESS` environment variable.

    See also: :attr:`success`.
    """

    failure: bool = field(init=False)
    """Always opposite of :attr:`success`. Included for convenience. See also:
    :meth:`get_failure_text`.
    """

    mode_name: Optional[str] = None
    """Name of the :class:`Mode`. If the associated ``Mode`` does not have a
    name, the ``mode_name`` will be ``None``.

    .. versionchanged:: 1.0.0.
        The ``mode_name`` is now always a string (or None) instead of
        ``ModeName``."""

    def __post_init__(
        self,
        results: List[MethodActivationResult],
    ) -> None:
        self._method_results = results
        self.success = self._get_success()
        self.failure = not self.success
        self.real_success = self._get_real_success()

    def list_methods(
        self,
        *,
        ignore_platform_fails: bool = True,
        ignore_unused: bool = False,
    ) -> list[MethodActivationResult]:
        """Get a list of methods involved in the activation process together
        with their activation results.

        This is the higher-level interface. For more finer-grained control, use
        :meth:`~ActivationResult.query`.

        The returned methods are in the order as given in when initializing
        ActivationResult. If you did not create the ActivationResult manually,
        the methods are in the priority order; the highest priority methods
        (those which are/were tried first) are listed first.

        .. versionchanged:: 1.0.0.

            The parameters are now keyword-only (See: https://github.com/wakepy/wakepy/issues/527)

        Parameters
        ----------
        ignore_platform_fails: bool
            If True, ignores platform support check fail. This is the default
            as usually one is not interested in methods which are meant for
            other platforms. If False, includes also platform fails. Default:
            ``True``.

        ignore_unused: bool
            If True, ignores all unused / remaining methods. Default:
            ``False``.


        See Also
        --------
        query

        """

        success_values = (True, False) if ignore_unused else (True, False, None)

        fail_stages = [
            StageName.WAKEPY_FORCE_FAILURE,
            StageName.PLATFORM_SUPPORT,
            StageName.REQUIREMENTS,
            StageName.ACTIVATION,
        ]
        if ignore_platform_fails:
            fail_stages.remove(StageName.PLATFORM_SUPPORT)

        return self.query(success=success_values, fail_stages=fail_stages)

    def query(
        self,
        success: Sequence[bool | None] = (True, False, None),
        fail_stages: Sequence[StageName | StageNameValue] = (
            StageName.WAKEPY_FORCE_FAILURE,
            StageName.PLATFORM_SUPPORT,
            StageName.REQUIREMENTS,
            StageName.ACTIVATION,
        ),
    ) -> list[MethodActivationResult]:
        """Get a list of the methods present in the activation process, and
        their activation results. This is the lower-level interface. If you
        want easier access, use :meth:`~ActivationResult.list_methods`. The
        methods are in the order as given in when initializing
        ActivationResult. If you did not create the ActivationResult manually,
        the methods are in the priority order; the highest priority methods
        (those which are/were tried first) are listed first.

        Parameters
        ----------
        success:
            Controls what methods to include in the output. Options are:
            True (success), False (failure) and None (method not used). If
            `success = (True, False)`, returns only methods which did succeed
            or fail (do not return unused methods).
        fail_stages:
            The fail stages to include in the output. The options are
            "WAKEPY_FORCE_FAILURE", "PLATFORM_SUPPORT", "REQUIREMENTS" and
            "ACTIVATION".

        See Also
        --------
        list_methods, get_failure_text
        """
        out = []
        for res in self._method_results:
            if res.success not in success:
                continue
            elif res.success is False and res.failure_stage not in fail_stages:
                continue
            out.append(res)

        return out

    def get_failure_text(self, style: FailureTextStyle = "block") -> str:
        """Gets information about a failure as text. In case the mode
        activation was successful, returns an empty string.

        This is only intended for interactive use or for logging purposes.
        Users should not rely on the exact text format returned by this
        function as it may change without a notice. For programmatic use cases,
        it is advisable to use :meth:`query`, or :meth:`list_methods` instead.

        Parameters
        ----------
        style: "block" | "inline"
            The style of the failure text. "block" adds newlines in the text
            and makes it easier to read, while "inline" returns a single line
            string (useful for logging). Default: "block".


        Examples
        --------
        >>> # Assuming the activation will fail for some reason
        >>> with keep.presenting() as m:
        >>>     # do stuff
        >>>
        >>> print(m.result.get_failure_text())
        Could not activate wakepy Mode "keep.running"!
        <BLANKLINE>
        Tried Methods (in the order of attempt):
        <BLANKLINE>
        1. org.freedesktop.PowerManagement
            Reason: DBusCallError("DBus call of method 'Inhibit' on interface
            'org.freedesktop.PowerManagement.Inhibit' with args ('wakepy', 'wakelock
            active') failed with message: [org.freedesktop.DBus.Error.ServiceUnknown]
            ('The name org.freedesktop.PowerManagement was not provided by any
            .service files',)")
        <BLANKLINE>
        2. org.gnome.SessionManager
            Reason: RuntimeError('Intentional failure here (for demo purposes)')
        <BLANKLINE>
        3. caffeinate
            Reason: Current platform (LINUX) is not in supported platforms: MACOS
        <BLANKLINE>
        4. SetThreadExecutionState
            Reason: Current platform (LINUX) is not in supported platforms: WINDOWS

        >>> # Inline style
        >>> print(m.result.get_failure_text('inline'))
        Could not activate wakepy Mode "keep.running"! Tried Methods (in the order of attempt): (#1, org.freedesktop.PowerManagement, ACTIVATION, DBusCallError("DBus call of method 'Inhibit' on interface 'org.freedesktop.PowerManagement.Inhibit' with args ('wakepy', 'wakelock active') failed with message: [org.freedesktop.DBus.Error.ServiceUnknown] ('The name org.freedesktop.PowerManagement was not provided by any .service files',)")), (#2, org.gnome.SessionManager, ACTIVATION, RuntimeError('Intentional failure here (for demo purposes)')), (#3, caffeinate, PLATFORM_SUPPORT, Current platform (LINUX) is not in supported platforms: MACOS), (#4, SetThreadExecutionState, PLATFORM_SUPPORT, Current platform (LINUX) is not in supported platforms: WINDOWS). The format of each item in the list is (index, method_name, failure_stage, failure_reason).

        .. versionchanged:: 1.0.0.

            The ``style`` parameter was added in wakepy 1.0.0, and the default
            style was changed to "block".


        See Also
        --------
        list_methods, query, get_methods_text, get_methods_text_detailed

        """  # noqa: E501, W505

        if self.success:
            return ""

        mode_name = self.mode_name or "[unnamed mode]"
        method_results = self.query()

        if not method_results:
            tried_methods_text = "Did not try any methods!"
            sep = "\n\n" if style == "block" else " "
            msg = f'Could not activate wakepy Mode "{mode_name}"!'
            return f"{msg}{sep}{tried_methods_text}"

        msg = f'Could not activate wakepy Mode "{mode_name}"!'

        if style == "block":
            methods_text = self.get_methods_text_detailed(
                fail="Reason", unsupported="Reason"
            )
            return (
                f"{msg}\n\nTried Methods (in the order of attempt):\n\n{methods_text}"
            )
        else:
            inline_items = []
            for (
                index,
                method_name,
                failure_reason,
            ) in self._get_methods_text_detailed_list(
                fail="Reason", unsupported="Reason"
            ):
                inline_items.append(f"(#{index}, {method_name}, {failure_reason})")
            inline = ", ".join(inline_items)
            tried = (
                "Tried Methods (in the order of attempt): "
                f"{inline}. "
                "The format of each item in the list is "
                "(index, method_name, failure_reason)."
            )
            return f"{msg} {tried}"

    def _get_success(self) -> bool:
        for res in self._method_results:
            if res.success:
                return True
        return False

    def _get_real_success(self) -> bool:
        for res in self._method_results:
            if res.success and res.method_name != WAKEPY_FAKE_SUCCESS_METHOD:
                return True
        return False

    def get_methods_text(
        self,
        *,
        width_index: int = 3,
        width_name: int = 35,
        width_status: int = 8,
    ) -> str:
        """Format method activation results as a simple list with status.

        Parameters
        ----------
        width_index: int, optional
            Width for the index number column. You can also control the level
            of indent by changing this value.
        width_name: int, optional
            Maximum width for method name column. Long names will be truncated
            with "...".
        width_status: int, optional
            Width for status column.

        Returns
        -------
        str
            Formatted output with method names and status

        Examples
        --------
        >>> print(result.get_methods_text())
          1. org.freedesktop.PowerManagement             SUCCESS
          2. org.gnome.SessionManager                    FAIL
          3. caffeinate                                  *
          4. SetThreadExecutionState                     *

        .. versionadded:: 1.0.0

        .. seealso:: :meth:`get_methods_text_detailed`,
            :meth:`get_failure_text`

        """
        results = self._method_results
        if not results:
            return ""

        lines = []
        for i, result in enumerate(results, start=1):
            status = result.get_status_string(unsupported="*")
            name = result.method_name

            if len(name) > width_name:
                method_formatted = name[: width_name - 3] + "..."
            else:
                method_formatted = name.ljust(width_name)

            status_formatted = status.ljust(width_status)

            lines.append(f"{i:>{width_index}}. {method_formatted}   {status_formatted}")
        return "\n".join(lines)

    def get_methods_text_detailed(
        self,
        max_width: int = 80,
        *,
        success: str = "SUCCESS",
        fail: str = "FAIL",
        unused: str = "UNUSED",
        unsupported: str = "UNSUPPORTED",
    ) -> str:
        """Format method activation results with detailed status and reasons.

        Parameters
        ----------
        max_width : int, optional
            Maximum width for each line in the output. Default: 80.
        success : str, optional
            String to use for successful methods.
        fail : str, optional
            String to use for failed methods (non-platform failures).
        unused : str, optional
            String to use for unused methods.
        unsupported : str, optional
            String to use for platform support failures.

        Returns
        -------
        str
            Formatted output with method names, status, and failure reasons

        Examples
        --------
        >>> print(result.get_methods_text_detailed())
          1. org.freedesktop.PowerManagement
             FAIL: DBusCallError("DBus call of method 'Inhibit' on interface
             'org.freedesktop.PowerManagement.Inhibit' with args ('wakepy',
             'wakelock active') failed with message:
             [org.freedesktop.DBus.Error.ServiceUnknown] ('The name
             org.freedesktop.PowerManagement was not provided by any .service
             files',)")
        <BLANKLINE>
          2. org.gnome.SessionManager
             SUCCESS
        <BLANKLINE>
          3. caffeinate
             UNSUPPORTED: caffeinate is not supported on LINUX. The supported
             platforms are: MACOS
        <BLANKLINE>
          4. SetThreadExecutionState
             UNSUPPORTED: SetThreadExecutionState is not supported on LINUX.
             The supported platforms are: WINDOWS

        .. versionadded:: 1.0.0

        .. seealso:: :meth:`get_methods_text`, :meth:`get_failure_text`
        """
        data = self._get_methods_text_detailed_list(
            success=success, fail=fail, unused=unused, unsupported=unsupported
        )
        if not data:
            return ""

        lines = []
        for idx, method_name, status_line in data:
            method_line_prefix = f"{idx:>3}. "
            method_wrapped = textwrap.fill(
                method_name,
                width=max_width,
                initial_indent=method_line_prefix,
                subsequent_indent="     ",
                break_long_words=True,
                break_on_hyphens=False,
            )

            status_wrapped = textwrap.fill(
                status_line,
                width=max_width,
                initial_indent="     ",
                subsequent_indent="     ",
                break_long_words=True,
                break_on_hyphens=True,
            )

            lines.append(f"{method_wrapped}\n{status_wrapped}")

        return "\n\n".join(lines)

    def _get_methods_text_detailed_list(
        self,
        *,
        success: str = "SUCCESS",
        fail: str = "FAIL",
        unused: str = "UNUSED",
        unsupported: str = "UNSUPPORTED",
    ) -> List[Tuple[int, str, str]]:
        """Get raw method data: (index, method_name, status_line)."""
        data = []
        for i, result in enumerate(self._method_results, start=1):
            status_line = result.get_status_line(
                success=success, fail=fail, unused=unused, unsupported=unsupported
            )
            data.append((i, result.method_name, status_line))
        return data


@dataclass
class ActivationResult(_BaseActivationResult):
    """Responsible for keeping track of the possibly successful (max 1), failed
    and unused methods and providing a different view of the results of the
    activation process. The ``ActivationResult`` instances are created in
    activation process of a ``Mode`` like :func:`keep.presenting` and
    :func:`keep.running`, and one would not typically initialize one manually.

    **If you want to**:

    - Check if the activation was successful: See :attr:`success`
    - Check the active method: See :attr:`active_method`
    - Get information about activation failure in text format: See
      :meth:`get_failure_text`
    - Know more about the Methods involved: See :meth:`list_methods` and
      :meth:`query`.

    Parameters
    ----------
    results:
        The MethodActivationResults to be used to fill the ActivationResult
    mode_name:
        Name of the Mode. Optional.

    """

    method: MethodInfo | None = field(init=False)
    """The :class:`MethodInfo` about the used (successful) :class:`Method`. If
    the activation was not successful, this is ``None``.

    .. versionadded:: 1.0.0.

        The ``method`` attribute was added in wakepy 1.0.0 to replace the
        deprecated :attr:`active_method` attribute.
    """

    def __post_init__(
        self,
        results: List[MethodActivationResult],
    ) -> None:
        super().__post_init__(results)
        self.method = self._get_success_method()

    def _get_success_method(self) -> MethodInfo | None:
        methods = [res.method for res in self._method_results if res.success]
        if not methods:
            return None
        elif len(methods) == 1:
            return methods[0]
        else:
            methodnames = [m.name for m in methods]
            raise ValueError(
                "The ActivationResult cannot have more than one active methods! "
                f"Active methods: {methodnames}"
            )

    @property
    def active_method(self) -> str | None:  # pragma: no cover
        """
        .. deprecated:: 1.0.0
            Use :attr:`method` instead. This property will be removed in a
            future version of wakepy."""
        warnings.warn(
            "'ActivationResult.active_method' is deprecated in wakepy 1.0.0 and will"
            " be removed in a future version. Use 'ActivationResult.method', instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.method.name if self.method else None


@dataclass
class ProbingResults(_BaseActivationResult):
    """Result from probing all Methods for a Mode. Tells which Methods would
    work on the current system and which would not.

    No Methods can be UNUSED in a :class:`ProbingResults` as all Methods are
    probed.

    .. versionadded:: 1.0.0
    """

    methods: List[MethodInfo] = field(init=False)
    """List of all :class:`MethodInfo` about wakepy Methods used, in the order
    they were tried.

    .. versionadded:: 1.0.0
    """

    def __post_init__(
        self,
        results: List[MethodActivationResult],
    ) -> None:
        super().__post_init__(results)
        self.methods = [result.method for result in self._method_results]


@dataclass
class MethodActivationResult:
    r"""This class is a result from using a single Method to activate a mode.

    When activating a wakepy :class:`Mode`, the activation process:

    * Creates a list of :class:`Method`\ s to try, and prioritizes them
    * Tries to activate the mode by using the Methods in the list, one by one.

    For each Method activation attempt, a :class:`MethodActivationResult`
    is created. The :class:`ActivationResult` then collects all the
    :class:`MethodActivationResult` instances and provides a higher-level
    interface to access the results of the activation process.
    """

    method: MethodInfo
    """Information about the wakepy :class:`Method` this result is for.

    .. versionadded:: 1.0.0
   """

    success: bool | None
    """Tells about the result of the activation:

    - ``True``: Using Method was successful
    - ``False``: Using Method failed
    - ``None``: Method is unused
    """

    failure_stage: Optional[StageName] = None
    """None if the method did not fail. Otherwise, the name of the stage where
    the method failed.
    """

    failure_reason: str = ""
    """Empty string if activating the Method did not fail. Otherwise, failure
    reason as string, if provided."""

    def __repr__(self) -> str:
        status = self.get_status_string(unsupported="FAIL")
        error_at = " @" + self.failure_stage if self.failure_stage else ""
        failure_reason = f', "{self.failure_reason}"' if self.success is False else ""
        return f"({status}{error_at}, {self.method_name}{failure_reason})"

    @property
    def mode_name(self) -> str:
        """The name of the mode of the :class:`Method` this result is for."""
        return self.method.mode_name

    @property
    def method_name(self) -> str:
        """The name of the :class:`Method` this result is for."""
        return self.method.name

    def get_status_string(
        self,
        *,
        success: str = "SUCCESS",
        fail: str = "FAIL",
        unused: str = "UNUSED",
        unsupported: str = "UNSUPPORTED",
    ) -> str:
        """Get a short status string for this method activation result.

        Parameters
        ----------
        success : str, optional
            String to return for successful methods.
        fail : str, optional
            String to return for failed methods (non-platform failures).
        unused : str, optional
            String to return for unused methods.
        unsupported : str, optional
            String to return for platform support failures.

        Returns
        -------
        str
            One of the customizable status strings: `success`, `fail`,
            `unused`, or `unsupported` depending on the method activation
            result.

        .. versionadded:: 1.0.0

        """
        if self.success:
            return success
        elif self.success is False:
            if self.failure_stage == StageName.PLATFORM_SUPPORT:
                return unsupported
            return fail
        else:
            return unused

    def get_status_line(
        self,
        *,
        success: str = "SUCCESS",
        fail: str = "FAIL",
        unused: str = "UNUSED",
        unsupported: str = "UNSUPPORTED",
    ) -> str:
        """Get a status and failure reason, if any.

        For failed methods, includes the failure reason. For successful or
        unused methods, returns just the status string.

        Parameters
        ----------
        success : str, optional
            String to use for successful methods.
        fail : str, optional
            String to use for failed methods (non-platform failures).
        unused : str, optional
            String to use for unused methods.
        unsupported : str, optional
            String to use for platform support failures.

        Returns
        -------
        str
            Status line with format "{status}: {reason}" for failures,
            or just "{status}" for success/unused.

        .. versionadded:: 1.0.0

        """
        status = self.get_status_string(
            success=success, fail=fail, unused=unused, unsupported=unsupported
        )
        if self.success is False:
            failure_reason = self.failure_reason or "Unknown reason"
            return f"{status}: {failure_reason}"
        return status
