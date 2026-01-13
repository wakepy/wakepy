"""This module defines two important helpers for the tests

1) get_test_method_class
A function which may used to create wakepy.Method classes using arguments.

Example
-------
Create Method which return True from Method.caniuse() and raises a
RuntimeError in Method.enter_mode()

>>>  method_cls = get_test_method_class(
            caniuse=True, enter_mode=RuntimeError("failed")
)

2) combinations_of_test_methods
A function which returns an iterator for testing a cross product of different
Methods. This uses get_test_method_class underneath.

Example
-------
>>> METHOD_OPTIONS = [
    METHOD_MISSING,
    True,
    False,
    RunTimeError('foo'),
]
>>> for method in combinations_of_test_methods(
        enter_mode=[METHOD_MISSING],
        heartbeat=[METHOD_MISSING],
        exit_mode=METHOD_OPTIONS,
    ):
        # test
"""

from __future__ import annotations

import itertools
from collections import Counter
from typing import Iterable, Type

from wakepy.core import PlatformType
from wakepy.core.method import Method


class TestMethod(Method):
    __test__ = False  # for pytest; this won't be interpreted as test class.
    mode_name = "_test"


class WakepyMethodTestError(Exception): ...


_class_counter: Counter[str] = Counter()


def get_new_classname(prefix="TestMethod") -> str:
    """Creates a new class name. Just to make it easier to generate lots of
    Methods."""
    _class_counter[prefix] += 1
    return f"{prefix}{_class_counter[prefix]}"


_test_method_classes = dict()
"""Container for all created method classes (caching for get_test_method_class)
"""
METHOD_MISSING = "__method_is_not_implemented__"
"""Magic constant for creating classes with some functions not implemented"""
FAILURE_REASON = "failure_reason"
DEFAULT_ERROR_TEXT = "wakepy test error"
METHOD_OPTIONS = [
    METHOD_MISSING,
    True,
    False,
    FAILURE_REASON,
    WakepyMethodTestError(DEFAULT_ERROR_TEXT),
]


def get_test_method_class(
    *,
    caniuse=METHOD_MISSING,
    enter_mode=METHOD_MISSING,
    heartbeat=METHOD_MISSING,
    exit_mode=METHOD_MISSING,
    supported_platforms=(PlatformType.ANY,),
    name: str | None = None,
) -> Type[Method]:
    """Get a test Method class with the .caniuse(), .enter_mode(), .heartbeat()
    and .exit_mode() methods defined as wanted. All methods can either be:

    (a) METHOD_MISSING: missing method. The created Method subclass will have
        the default implementation from the Method class.
    (b) An instance of an Exception. For example MyException('foo'). In this
        case, the exception will be raised.
    (c) Any value. In this case, the value will be returned. Typical values
      are True (success), string (fail with a reason), False (fail without
      giving a reason) and None.

    If `name` is provided, uses that as the Method name.

    For the expected outcome of each of these, see:
        tests/unit/test_core/test_activation.py
    """

    def _create_function(instructions):
        if instructions == METHOD_MISSING:
            return None
        elif isinstance(instructions, type) and issubclass(instructions, BaseException):

            def m(self):
                raise instructions()

        elif isinstance(instructions, Exception):

            def m(self):
                raise instructions

        else:

            def m(self):
                return instructions

        return m

    def _create_class() -> Type[Method]:
        clsname = name if name is not None else get_new_classname()
        clskwargs = {
            "supported_platforms": supported_platforms,
            "name": clsname,
            "mode_name": "_tests",
        }
        clsmethods = dict()
        clsmethods["caniuse"] = _create_function(caniuse)
        clsmethods["enter_mode"] = _create_function(enter_mode)
        clsmethods["exit_mode"] = _create_function(exit_mode)
        clsmethods["heartbeat"] = _create_function(heartbeat)
        clskwargs = {
            **clskwargs,
            **{k: v for k, v in clsmethods.items() if callable(v)},
        }
        return type(clsname, (Method,), clskwargs)

    key = (enter_mode, heartbeat, exit_mode, caniuse, supported_platforms, name)
    if key not in _test_method_classes:
        _test_method_classes[key] = _create_class()

    return _test_method_classes[key]


def combinations_of_test_methods(
    enter_mode=Iterable,
    heartbeat=Iterable,
    exit_mode=Iterable,
) -> Iterable[Method]:
    """Create an iterator of Methods over the combinations of the given
    enter_mode, heartbeat and exit_mode"""
    for enter_mode_, heartbeat_, exit_mode_ in itertools.product(
        enter_mode, heartbeat, exit_mode
    ):
        yield get_test_method_class(
            enter_mode=enter_mode_, heartbeat=heartbeat_, exit_mode=exit_mode_
        )()
