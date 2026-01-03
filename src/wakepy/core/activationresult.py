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

import typing
import warnings
from dataclasses import InitVar, dataclass, field
from typing import List, Sequence

from .constants import WAKEPY_FAKE_SUCCESS_METHOD, StageName, StageNameValue

if typing.TYPE_CHECKING:
    from typing import Optional

    from .method import MethodInfo


@dataclass
class ActivationResult:
    """Responsible of keeping track on the possibly successful (max 1), failed
    and unused methods and providing different view on the results of the
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

    results: InitVar[List[MethodActivationResult]]
    # These are the results for each of the used wakepy.Methods, in the
    # order the methods were tried (first = highest priority, last =
    # lowest priority)

    success: bool = field(init=False)
    """Tells if entering into a mode was successful. Note that this may be
    faked with :ref:`WAKEPY_FAKE_SUCCESS` environment variable e.g. for testing
    purposes.

    See Also
    --------
    real_success, failure, get_failure_text
    """

    real_success: bool = field(init=False)
    """Tells is entering into a mode was successful. This may not be faked with
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

    method: MethodInfo | None = field(init=False)
    """The :class:`MethodInfo` about the used (successful) :class:`Method`. If
    the activation was not successful, this is ``None``.

    .. versionadded:: 1.0.0.

        The ``method`` attribute was added in wakepy 1.0.0 to replace the
        deprecated :attr:`active_method` attribute.
    """

    _method_results: List[MethodActivationResult] = field(init=False)

    def __post_init__(
        self,
        results: List[MethodActivationResult],
    ) -> None:
        self._method_results = results
        self.success = self._get_success()
        self.failure = not self.success
        self.real_success = self._get_real_success()
        self.method = self._get_success_method()

    def list_methods(
        self,
        ignore_platform_fails: bool = True,
        ignore_unused: bool = False,
    ) -> list[MethodActivationResult]:
        """Get a list of the methods present in the activation process, and
        their activation results. This is the higher-level interface. If you
        want more control, use :meth:`~ActivationResult.query`. The
        returned methods are in the order as given in when initializing
        ActivationResult. If you did not create the ActivationReult manually,
        the methods are in the priority order; the highest priority methods
        (those which are/were tried first) are listed first.

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

    def get_failure_text(self, newlines: bool = True) -> str:
        """Gets information about a failure as text. In case the mode
        activation was successful, returns an empty string.

        This is only intended for interactive use. Users should not rely
        on the exact text format returned by this function as it may change
        without a notice. For programmatic use cases, it is advisable to use
        :meth:`query`, instead.

        Parameters
        ----------
        newlines: bool
            If True, adds newlines in the text (useful for printing for user),
            if False, returns a single line string (useful for logging).


        Examples
        --------
        >>> # Assuming the activation will fail for some reason
        >>> with keep.presenting() as m:
        >>>     # do stuff
        >>>
        >>> print(m.result.get_failure_text())
        Could not activate wakepy Mode "keep.presenting"!
        <BLANKLINE>
        Tried Methods (in the order of attempt):
        (#1, org.gnome.SessionManager, ACTIVATION, RuntimeError('Intentional failure here')),
        (#2, caffeinate, PLATFORM_SUPPORT, -),
        (#3, SetThreadExecutionState, PLATFORM_SUPPORT, -).
        The format of each item in the list is (index, method_name, failure_stage, failure_reason).

        See Also
        --------
        list_methods, query
        """  # noqa: E501, W505

        if self.success:
            return ""
        mode_name = self.mode_name or "[unnamed mode]"

        if newlines:
            first_sep = "\n\n"
            sep = "\n"
        else:
            first_sep = sep = " "

        debug_info_lst = []
        for i, res in enumerate(self.query(), start=1):
            debug_info_lst.append(
                (
                    f"(#{i}, {res.method_name}, {res.failure_stage or 'N/A'}, "
                    f"{res.failure_reason or '-'})"
                )
            )

        if debug_info_lst:
            debug_info = f",{sep}".join(debug_info_lst)
            tried_methods_text = (
                f"Tried Methods (in the order of attempt):{sep}{debug_info}."
                f"{sep}The format of each item in the list is (index, method_name, "
                "failure_stage, failure_reason)."
            )
        else:
            tried_methods_text = "Did not try any methods!"

        err_text = (
            f'Could not activate wakepy Mode "{mode_name}"!{first_sep}'
            + tried_methods_text
        )

        return err_text

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
        error_at = " @" + self.failure_stage if self.failure_stage else ""
        failure_reason = f', "{self.failure_reason}"' if self.success is False else ""
        success_str = (
            "SUCCESS" if self.success else "FAIL" if self.success is False else "UNUSED"
        )
        return f"({success_str}{error_at}, {self.method_name}{failure_reason})"

    @property
    def mode_name(self) -> str:
        """The name of the mode of the :class:`Method` this result is for."""
        return self.method.mode_name

    @property
    def method_name(self) -> str:
        """The name of the :class:`Method` this result is for."""
        return self.method.name
