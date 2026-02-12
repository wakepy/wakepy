import re

import pytest

from wakepy import ActivationError, ActivationWarning
from wakepy.core import ActivationResult, DBusAdapter, Method, Mode, ModeName
from wakepy.core.mode import UnrecognizedMethodNames
from wakepy.modes import keep


@pytest.mark.parametrize(
    "name_prefix, function_under_test, mode_name_",
    [
        (
            "running",
            keep.running,
            ModeName.KEEP_RUNNING,
        ),
        (
            "presenting",
            keep.presenting,
            ModeName.KEEP_PRESENTING,
        ),
    ],
)
class TestKeepRunninAndPresenting:
    """Tests common for keep.running and keep.presenting functions. The
    `function_under_test` is either the keep.running or keep.presenting
    function"""

    @staticmethod
    @pytest.fixture
    def methods(name_prefix, mode_name_, monkeypatch, testutils):
        """This fixture creates three methods, which belong to a given mode."""

        testutils.empty_method_registry(monkeypatch)

        class MethodA(Method):
            name = f"{name_prefix}A"
            mode_name = mode_name_

        class MethodB(Method):
            name = f"{name_prefix}B"
            mode_name = mode_name_

        class MethodC(Method):
            name = f"{name_prefix}C"
            mode_name = mode_name_

        return dict(
            MethodA=MethodA,
            MethodB=MethodB,
            MethodC=MethodC,
        )

    def test_all_modes_are_selected_automatically(self, function_under_test, methods):
        """Simple test for keep.running and keep.presenting. Tests that all
        input arguments for the functions are passed to the Mode.__init__
        """

        mode = function_under_test()
        # All the methods for the mode are selected automatically
        assert set(mode._selected_method_classes) == {
            methods["MethodA"],
            methods["MethodB"],
            methods["MethodC"],
        }

    def test_omit_parameter(self, name_prefix, function_under_test, methods):
        # Case: Test "omit" parameter
        mode = function_under_test(omit=[f"{name_prefix}A"])
        assert set(mode._selected_method_classes) == {
            methods["MethodB"],
            methods["MethodC"],
        }

    def test_methods_parameter(self, name_prefix, function_under_test, methods):
        # Case: Test "methods" parameter
        mode = function_under_test(methods=[f"{name_prefix}A", f"{name_prefix}B"])
        assert set(mode._selected_method_classes) == {
            methods["MethodA"],
            methods["MethodB"],
        }

    def test_methods_priority_parameter(
        self, name_prefix, function_under_test, methods
    ):
        # Case: Test "methods_priority" parameter
        methods_priority = [f"{name_prefix}A", f"{name_prefix}B"]
        mode = function_under_test(methods_priority=methods_priority)
        assert mode.methods_priority == methods_priority
        assert set(mode._selected_method_classes) == {
            methods["MethodA"],
            methods["MethodB"],
            methods["MethodC"],
        }

    def test_methods_dbus_adapter_parameter(self, function_under_test, methods):
        # Case: Test "dbus_adapter" parameter
        class MyDBusAdapter(DBusAdapter): ...

        mode = function_under_test(
            dbus_adapter=MyDBusAdapter, methods=[x.name for x in methods.values()]
        )
        assert mode._dbus_adapter_cls == MyDBusAdapter


def test_keep_running_with_fake_success(monkeypatch, fake_dbus_adapter):
    """Simple smoke test for keep.running()"""
    monkeypatch.setenv("WAKEPY_FAKE_SUCCESS", "1")
    mode = keep.running(dbus_adapter=fake_dbus_adapter)
    assert mode.active is None

    with mode as m:
        assert mode is m
        assert m.active is True
        assert m.result.success is True

    assert m.active is None
    assert isinstance(m.result, ActivationResult)


def test_keep_presenting(monkeypatch, fake_dbus_adapter):
    """Simple smoke test for keep.presenting()"""
    monkeypatch.setenv("WAKEPY_FAKE_SUCCESS", "1")
    with keep.presenting(dbus_adapter=fake_dbus_adapter) as m:
        assert isinstance(m, Mode)
        assert m.result.success is True


@pytest.mark.parametrize(
    "mode_under_test, expected_name",
    [
        (keep.running, "keep.running"),
        (keep.presenting, "keep.presenting"),
    ],
)
class TestOnFail:
    """Test failure handling for keep.presenting and keep.running. (the on_fail
    parameter)"""

    @pytest.mark.filterwarnings("ignore:.*:wakepy.core.mode.NoMethodsWarning")
    def test_on_fail_pass(self, mode_under_test, expected_name):
        with mode_under_test(methods=[], on_fail="pass") as m:
            self._assertions_for_activation_failure(m, expected_name)

    @pytest.mark.filterwarnings("ignore:.*:wakepy.core.mode.NoMethodsWarning")
    def test_on_fail_warn(self, mode_under_test, expected_name):
        err_txt = f'Could not activate wakepy Mode "{expected_name}"!'
        with pytest.warns(ActivationWarning, match=re.escape(err_txt)):
            with mode_under_test(methods=[], on_fail="warn") as m:
                self._assertions_for_activation_failure(m, expected_name)

    @pytest.mark.filterwarnings("ignore:.*:wakepy.core.mode.NoMethodsWarning")
    def test_on_fail_error(self, mode_under_test, expected_name):
        err_txt = f'Could not activate wakepy Mode "{expected_name}"!'
        with pytest.raises(ActivationError, match=re.escape(err_txt)):
            with mode_under_test(methods=[], on_fail="error") as m:
                self._assertions_for_activation_failure(m, expected_name)

    @pytest.mark.filterwarnings("ignore:.*:wakepy.core.mode.NoMethodsWarning")
    def test_on_fail_callable(self, mode_under_test, expected_name):
        called = False

        def my_callable(result):
            nonlocal called
            called = True
            assert isinstance(result, ActivationResult)

        with mode_under_test(methods=[], on_fail=my_callable) as m:
            assert called is True
            self._assertions_for_activation_failure(m, expected_name)

    @staticmethod
    def _assertions_for_activation_failure(m: Mode, expected_name):
        assert m.active is False
        assert isinstance(m, Mode)
        assert m.name == expected_name
        assert m.result.mode_name == expected_name


class TestWithBadMethodName:
    def test_with_bad_method_name(self):
        with pytest.raises(
            UnrecognizedMethodNames,
            match=re.escape(
                'The following Methods are not part of the "keep.running" Mode: '
                "['bad_method']. Please check that the Methods are correctly "
                'spelled and that the Methods are part of the "keep.running" Mode. '
                "You may refer to full Methods listing at "
                "https://wakepy.readthedocs.io/stable/methods-reference.html."
            ),
        ):
            keep.running(methods=["bad_method"])
