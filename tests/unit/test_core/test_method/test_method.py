from __future__ import annotations

import re
import sys

import pytest

from tests.unit.test_core.testmethods import TestMethod
from wakepy import Method, MethodInfo
from wakepy.core import DBusMethodCall, PlatformType
from wakepy.core.method import (
    DBusCallError,
    MethodOutcome,
    MethodOutcomeValue,
    _check_supported_platforms,
    has_enter,
    has_exit,
    has_heartbeat,
)
from wakepy.core.registry import MethodRegistryError, get_method

if sys.version_info < (3, 8):  # pragma: no-cover-if-py-gte-38
    import typing_extensions as typing
else:  # pragma: no-cover-if-py-lt-38
    import typing

if typing.TYPE_CHECKING:
    from wakepy.core import DBusMethod


def test_overridden_methods_autodiscovery():
    """The enter_mode, heartbeat and exit_mode methods by default do nothing
    (on the Method base class). In subclasses, these are usually overriden.
    Check that detecting the overridden methods works correctly
    """

    class WithEnterAndExit(TestMethod):
        def enter_mode(self):
            return

        def exit_mode(self):
            return

    method1 = WithEnterAndExit()

    assert has_enter(method1)
    assert has_exit(method1)
    assert not has_heartbeat(method1)

    class WithJustHeartBeat(TestMethod):
        def heartbeat(self):
            return

    method2 = WithJustHeartBeat()

    assert not has_enter(method2)
    assert not has_exit(method2)
    assert has_heartbeat(method2)

    class WithEnterExitAndHeartBeat(TestMethod):
        def heartbeat(self):
            return

        def enter_mode(self):
            return

        def exit_mode(self):
            return

    method3 = WithEnterExitAndHeartBeat()

    assert has_enter(method3)
    assert has_exit(method3)
    assert has_heartbeat(method3)

    class SubWithEnterAndHeart(WithJustHeartBeat):
        def enter_mode(self):
            return

    method4 = SubWithEnterAndHeart()
    assert has_enter(method4)
    assert has_heartbeat(method4)
    assert not has_exit(method4)

    class SubWithEnterAndExit(WithEnterAndExit):
        def enter_mode(self):
            return 123

    method5 = SubWithEnterAndExit()
    assert has_enter(method5)
    assert has_exit(method5)
    assert not has_heartbeat(method5)


@pytest.mark.usefixtures("empty_method_registry")
def test_not_possible_to_define_two_methods_with_same_name(testutils, monkeypatch):
    somename = "Some name"

    class SomeMethod(TestMethod):
        name = somename

    # It is not possible to define two methods if same name
    with pytest.raises(
        MethodRegistryError, match=re.escape('Duplicate Method name "Some name"')
    ):

        class SomeMethod(TestMethod):  # type: ignore # noqa:F811
            name = somename

    testutils.empty_method_registry(monkeypatch)

    # Now as the registry is empty it is possible to define method with
    # the same name again
    class SomeMethod(TestMethod):  # type: ignore # noqa:F811
        name = somename


def test_method_defaults():
    """tests the Method enter_mode, exit_mode and heartbeat defaults"""
    m = Method()
    assert m.enter_mode() is None  # type: ignore
    assert m.heartbeat() is None  # type: ignore
    assert m.exit_mode() is None  # type: ignore

    # By default, all platforms are supported
    assert set(m.supported_platforms) == set((PlatformType.ANY,))


@pytest.mark.usefixtures("provide_methods_a_f")
def test_method_string_representations():
    MethodB = get_method("B")
    method = MethodB()
    assert method.__str__() == "<wakepy Method: MethodB>"
    assert method.__repr__() == f"<wakepy Method: MethodB at {hex(id(method))}>"


class TestProcessDBusCall:
    def test_missing_dbus_adapter(self, dbus_method: DBusMethod):
        method = Method()
        # when there is no dbus adapter..
        assert method.dbus_adapter is None
        # we get RuntimeError
        with pytest.raises(
            RuntimeError,
            match=".*cannot process dbus method call.*as it does not have a DBusAdapter",  # noqa: E501
        ):
            assert method.process_dbus_call(DBusMethodCall(dbus_method))

    def test_error_when_calling_dbus_methods(self, dbus_method: DBusMethod):
        method = Method()

        class MockedDBusAdapter:
            def process(self, _: DBusMethodCall) -> object:
                raise RuntimeError("Error from mocked DBusAdapter")

        method.dbus_adapter = MockedDBusAdapter()  # type: ignore[assignment]

        # When there's an error while calling a D-Bus method,
        # we get DBusCallError with message telling what went wrong
        with pytest.raises(
            DBusCallError,
            match=re.escape(
                "DBus call of method 'test-method' on interface '/foo' with args () failed with message: Error from mocked DBusAdapter"  # noqa: E501
            ),
        ):
            assert method.process_dbus_call(DBusMethodCall(dbus_method))


def test_methodoutcome(assert_strenum_values):
    assert_strenum_values(MethodOutcome, MethodOutcomeValue)


class TestCheckSupportedPlatforms:
    def test_wrong_type_of_supported_platforms(self):
        with pytest.raises(
            ValueError,
            match="The supported_platforms of someclass must be a tuple of PlatformType!",  # noqa: E501
        ):
            _check_supported_platforms("x", "someclass")  # type: ignore

    def test_wrong_type_of_a_single_platform(self):
        supported_platforms = (PlatformType.UNIX_LIKE_FOSS, "foo", PlatformType.WINDOWS)
        with pytest.raises(
            ValueError,
            match=re.escape(
                "The supported_platforms of someclass must be a tuple of PlatformType! One item (foo) is of type \"<class 'str'>\""  # noqa: E501
            ),
        ):
            _check_supported_platforms(supported_platforms, "someclass")  # type: ignore


class TestMethodInfo:
    class SomeMethod(TestMethod):
        name = "SomeMethod"
        mode_name = "SomeMode"
        supported_platforms = (PlatformType.WINDOWS,)

    def test_method_info(self):
        method_info = MethodInfo._from_method(self.SomeMethod())

        assert method_info.name == "SomeMethod"
        assert method_info.mode_name == "SomeMode"
        assert method_info.supported_platforms == (PlatformType.WINDOWS,)

        # Check that the string representation is correct
        assert str(method_info) == "SomeMethod"
        assert repr(method_info).startswith(
            "MethodInfo(name='SomeMethod', mode_name='SomeMode', "
        )
