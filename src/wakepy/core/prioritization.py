"""This module contains functions which may be used in the prioritization of
wakepy Methods.

Most important functions
------------------------
order_methods_by_priority
    Order a list of Methods by priority, using an optional `methods_priority`
    order.
"""

from __future__ import annotations

import typing
from typing import List, Sequence, Set, Union

from .constants import WAKEPY_FAKE_SUCCESS_METHOD
from .platform import CURRENT_PLATFORM, get_platform_supported

if typing.TYPE_CHECKING:
    from typing import List, Optional, Tuple, Union

    from .method import MethodCls

    """The strings in MethodsPriorityOrder are names of wakepy.Methods or the
    asterisk ('*')."""
    MethodsPriorityOrder = Sequence[Union[str, Set[str]]]


def order_methods_by_priority(
    methods: List[MethodCls],
    methods_priority: Optional[MethodsPriorityOrder] = None,
) -> List[MethodCls]:
    """Take an unordered list of Methods and sort them by priority using the
    methods_priority and automatic ordering. The methods_priority is used to
    define groups of priority (sets of methods). The automatic ordering part is
    used to order the methods *within* each priority group. In particular, all
    methods supported by the current platform are placed first, and all
    supported methods are then ordered alphabetically (ignoring case).

    Parameters
    ----------
    methods:
        The list of Methods to sort.
    methods_priority:
        Optional priority order, which is a list of method names (strings) or
        sets of method names (sets of strings). An asterisk ('*') may be used
        for "all the rest methods". None is same as ['*'].

    Returns
    -------
    sorted_methods:
        The input `methods` sorted with priority, highest priority first.

    Example
    -------
    Assuming: Current platform is Linux.

    >>> methods = [LinuxA, LinuxB, LinuxC, MultiPlatformA, WindowsA]
    >>> order_methods_by_priority(
    >>>    methods,
    >>>    methods_priority=[{"WinA", "LinuxB"}, "*"],
    >>> )
    [LinuxB, WindowsA, LinuxA, LinuxC, MultiPlatformA]

    Explanation:

    WindowsA and LinuxB were given high priority, but since the current
    platform is Linux, LinuxB was prioritized to be before WindowsA.

    The asterisk ('*') is converted to a set of rest of the methods:
    {"LinuxA", "LinuxC", "MultiPlatformA"}, and those are then
    automatically ordered. As all of them support Linux, the result is
    just the methods sorted alphabetically. The asterisk in the end is
    optional; it is added to the end of `methods_priority` if missing.

    """
    unordered_priority_groups: List[Set[MethodCls]] = _sort_methods_to_priority_groups(
        methods, methods_priority=methods_priority
    )

    ordered_groups: List[List[MethodCls]] = [
        _order_set_of_methods_by_priority(group) for group in unordered_priority_groups
    ]

    methods = [method for group in ordered_groups for method in group]

    # Prioritize the WAKEPY_FAKE_SUCCESS before anything else.
    return sorted(
        methods,
        key=lambda m: (0 if m.name == WAKEPY_FAKE_SUCCESS_METHOD else 1,),
    )


def _sort_methods_to_priority_groups(
    methods: List[MethodCls], methods_priority: Optional[MethodsPriorityOrder]
) -> List[Set[MethodCls]]:
    """Sorts Methods in `methods` to groups based on priority order defined by
    the given `methods_priority`.

    Parameters
    ----------
    methods: list[MethodCls]
        The source list of methods. These methods are returned as prioritized
        groups.
    methods_priority: list[str | set[str]]
        The names of the methods in `methods`. This specifies the priority
        order; the order of method classes in the returned list. An asterisk
        ('*') can be used to denote "all other methods".


    Returns
    -------
    method_groups: list[set[MethodCls]]
        The prioritized methods. Each set in the output represents a group of
        equal priority. All Methods from the input `methods` are always
        included in the output


    Example
    -------
    Say there are methods MethodA, MethodB, MethodC, MethodD, MethodE, MethodF
    with names "A", "B", "C", "D", "E", "F":

    >>> methods = [MethodA, MethodB, MethodC, MethodD, MethodE, MethodF]
    >>> _sort_methods_to_priority_groups(
            methods,
            methods_priority=["A", "F", "*"]
        )
    [
        {MethodA},
        {MethodF},
        {MethodB, MethodC, MethodD, MethodE},
    ]

    """
    _check_methods_priority(methods_priority, methods)

    # Make this a list of sets just to make things simpler
    methods_priority_sets: List[Set[str]] = [
        {item} if isinstance(item, str) else item for item in methods_priority or []
    ]

    method_dct = {m.name: m for m in methods}

    asterisk = {"*"}
    asterisk_index = None
    out: List[Set[MethodCls]] = []

    for item in methods_priority_sets:
        if item == asterisk:
            # Save the location where to add the rest of the methods ('*')
            asterisk_index = len(out)
        else:  # Item is a set but not `asterisk`
            out.append({method_dct[name] for name in item})

    out_flattened = {m for group in out for m in group}
    rest_of_the_methods = {m for m in methods if m not in out_flattened}

    if rest_of_the_methods:
        if asterisk_index is not None:
            out.insert(asterisk_index, rest_of_the_methods)
        else:
            out.append(rest_of_the_methods)

    return out


def _check_methods_priority(
    methods_priority: Optional[MethodsPriorityOrder], methods: List[MethodCls]
) -> None:
    """Checks against `methods` that the `methods_priority` is valid.

    Parameters
    ----------
    methods_priority: list[str | set[str]]
        The priority order, which is a list of where items are method names,
        sets of methods names or the asterisk ('*'). The asterisk means "all
        rest methods" and may occur only once in the priority order, and cannot
        be part of a set. All method names must be unique and must be part of
        the `methods`.
    methods: list[MethodCls]
        The methods which the `methods_priority` is validated against.

    Raises
    ------
    ValueError or TypeError if the `methods_priority` is not valid.
    """
    if methods_priority is None:
        return

    known_method_names = {m.name for m in methods}
    known_method_names.add("*")
    seen_method_names = set()

    for method_name, in_set in _iterate_methods_priority(methods_priority):
        if not isinstance(method_name, str):
            raise TypeError("methods_priority must be a list[str | set[str]]!")

        if in_set and method_name == "*":
            raise ValueError(
                "Asterisk (*) may not be a part of a set in methods_priority!"
            )
        if method_name not in known_method_names:
            raise ValueError(
                f'Method "{method_name}" in methods_priority not in selected methods!'
            )
        if method_name in seen_method_names:
            if method_name != "*":
                raise ValueError(
                    f'Duplicate method name "{method_name}" in methods_priority'
                )
            else:
                raise ValueError(
                    "The asterisk (*) can only occur once in methods_priority!"
                )
        seen_method_names.add(method_name)


def _iterate_methods_priority(
    methods_priority: Optional[MethodsPriorityOrder],
) -> typing.Iterator[Tuple[str, bool]]:
    """Provides an iterator over the items in methods_priority. The items in
    the iterator are (method_name, in_set) 2-tuples, where the method_name is
    the method name (str) and the in_set is a boolean which is True if the
    returned method_name is part of a set and False otherwise."""

    if not methods_priority:
        return

    for item in methods_priority:
        if isinstance(item, set):
            for method_name in item:
                yield method_name, True
        else:
            yield item, False


def _order_set_of_methods_by_priority(methods: Set[MethodCls]) -> List[MethodCls]:
    """Sorts Method classes by priority and returns a new sorted list with
    Methods with highest priority first.

    The logic is:
    (1) Any Methods supporting the CURRENT_PLATFORM are placed before any other
        Methods (the others are not expected to work at all)
    (2) Sort alphabetically by Method name, ignoring the case
    """

    # Later: Use some better logic for this.
    # See: https://github.com/wakepy/wakepy/issues/262
    return sorted(
        methods,
        key=lambda m: (
            # Prioritize the WakepyFakeSuccess method before anything else.
            0 if m.name == WAKEPY_FAKE_SUCCESS_METHOD else 1,
            # Then, prioritize methods supporting CURRENT_PLATFORM over any
            # others
            0 if get_platform_supported(CURRENT_PLATFORM, m.supported_platforms) else 1,
            m.name.lower() if m.name else "",
        ),
    )
