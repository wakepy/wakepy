"""Tests for the wakepy.core.activation

Exception: ActivationResult is tested in it's own file
"""

import datetime as dt
import re
from unittest.mock import patch

import pytest

from tests.unit.test_core.testmethods import (
    FAILURE_REASON,
    METHOD_MISSING,
    METHOD_OPTIONS,
    WakepyMethodTestError,
    combinations_of_test_methods,
    get_test_method_class,
)
from wakepy.core import Method, PlatformType
from wakepy.core.constants import IdentifiedPlatformType, StageName, StageNameValue
from wakepy.core.heartbeat import Heartbeat
from wakepy.core.method import (
    activate_method,
    caniuse_fails,
    deactivate_method,
    try_enter_and_heartbeat,
)

P = IdentifiedPlatformType


class TestActivateMethod:
    """tests for activate_method"""

    def test_method_without_name(self):
        """Methods used for activation must have a name. If not, there should
        be a ValueError raised"""

        method = type("MyMethod", (Method,), {})()
        with pytest.raises(
            ValueError,
            match=re.escape(
                "Methods without a name may not be used to activate modes!"
            ),
        ):
            activate_method(method)

    @patch("wakepy.core.method.CURRENT_PLATFORM", IdentifiedPlatformType.WINDOWS)
    def test_method_without_platform_support(self):
        UnsupportedMethod = get_test_method_class(
            supported_platforms=(PlatformType.LINUX,),
        )

        unsupported_method = UnsupportedMethod()

        # The supported_platform is LINUX and CURRENT_PLATFORM is set to
        # WINDOWS so this must fail.
        res, heartbeat = activate_method(unsupported_method)
        assert res.failure_stage == StageName.PLATFORM_SUPPORT
        assert res.success is False
        assert heartbeat is None
        assert (
            res.failure_reason
            == "Current platform (WINDOWS) is not in supported platforms: LINUX"
        )

    def test_with_unknown_platform_support_any(self):
        SupportedMethod = get_test_method_class(
            supported_platforms=(PlatformType.ANY,), caniuse=True, enter_mode=None
        )
        unsupported_method = SupportedMethod()

        res, _ = activate_method(unsupported_method)
        assert res.success is True

    @patch("wakepy.core.method.CURRENT_PLATFORM", IdentifiedPlatformType.UNKNOWN)
    def test_with_unknown_platform_support_just_linux(self):
        # This is otherwise supported method, so it works also on the UNKNOWN
        # system. Only the platform support check should return None ("I don't
        # know"), but the rest of the activation process should proceed and the
        # activation should succeed.
        SupportedMethod = get_test_method_class(
            supported_platforms=(PlatformType.LINUX,), caniuse=True, enter_mode=None
        )
        unsupported_method = SupportedMethod()

        res, _ = activate_method(unsupported_method)
        assert res.success is True

    def test_method_caniuse_fails(self):
        # Case 1: Fail by returning False from caniuse
        method = get_test_method_class(caniuse=False)()
        res, heartbeat = activate_method(method)
        assert res.success is False
        assert res.failure_stage == StageName.REQUIREMENTS
        assert res.failure_reason == ""
        assert heartbeat is None

        # Case 2: Fail by returning some error reason from caniuse
        method = get_test_method_class(
            caniuse="SomeSW version <2.1.5 not supported",
        )()
        res, heartbeat = activate_method(method)
        assert res.success is False
        assert res.failure_stage == StageName.REQUIREMENTS
        assert res.failure_reason == "SomeSW version <2.1.5 not supported"
        assert heartbeat is None

    def test_method_enter_mode_fails(self):
        # Case: Fail by returning False from enter_mode
        method = get_test_method_class(
            caniuse=True, enter_mode=RuntimeError("failed")
        )()
        res, heartbeat = activate_method(method)
        assert res.success is False
        assert res.failure_stage == StageName.ACTIVATION
        assert "RuntimeError('failed')" in res.failure_reason
        assert heartbeat is None

    def test_enter_mode_success(self):
        method = get_test_method_class(caniuse=True, enter_mode=None)()
        res, heartbeat = activate_method(method)
        assert res.success is True
        assert res.failure_stage is None
        assert res.failure_reason == ""
        # No heartbeat on success, as the used Method does not have heartbeat()
        assert heartbeat is None

    def test_heartbeat_success(self):
        method = get_test_method_class(heartbeat=None)()
        res, heartbeat = activate_method(method)
        assert res.success is True
        assert res.failure_stage is None
        assert res.failure_reason == ""
        # We get a Heartbeat instance on success, as the used Method does has a
        # heartbeat() # noqa: ERA001
        assert isinstance(heartbeat, Heartbeat)


class TestTryEnterAndHeartbeat:
    """tests for try_enter_and_heartbeat

    TABLE 1
    Test table for try_enter_and_heartbeat. Methods are {enter_mode}{heartbeat}
    where {enter_mode} and {heartbeat} are

    M: Missing implementation
    F: Failed attempt (with or without message)
    S: Successful attempt

    Methods   Expected result
    -------   ---------------------------------------------------------
    1)  F*    Return Fail + enter_mode error message

    2)  MM    Raise Exception -- the Method is faulty.
    3)  MF    Return Fail + heartbeat error message
    4)  MS    Return Success + heartbeat time

    5)  SM    Return Success
    6)  SF    Return Fail + heartbeat error message + call exit_mode()
    7)  SS    Return Success + heartbeat time
    """

    def test_enter_mode_failing(self):
        """Tests 1) F* from TABLE 1; enter_mode failing"""

        # Case: enter_mode raises exception
        for method in combinations_of_test_methods(
            enter_mode=[RuntimeError(FAILURE_REASON)],
            heartbeat=METHOD_OPTIONS,
            exit_mode=METHOD_OPTIONS,
        ):
            success, err_message, heartbeat_call_time = try_enter_and_heartbeat(method)
            # Expecting
            # * entering to FAIL
            # * error message (FAILURE_REASON)
            # * No heartbeat_call_time (None)
            assert success is False
            assert FAILURE_REASON in err_message
            assert heartbeat_call_time is None

    def test_enter_mode_missing_and_heartbeat(self):
        """Tests 2) MM from TABLE 1; missing both enter_mode and heartbeat"""
        for method in combinations_of_test_methods(
            enter_mode=[METHOD_MISSING],
            heartbeat=[METHOD_MISSING],
            exit_mode=METHOD_OPTIONS,
        ):
            expected_errmsg = (
                f"Method {method.__class__.__name__} ({method.name}) is not properly "
                "defined! Missing implementation for both, enter_mode() "
                "and heartbeat()!"
            )

            success, err_message, heartbeat_call_time = try_enter_and_heartbeat(method)

            # Expecting an error as missing enter_mode and heartbeat
            assert success is False
            assert err_message == expected_errmsg
            assert heartbeat_call_time is None

    def test_enter_mode_missing_heartbeat_failing(self):
        """Tests 3) MF from TABLE 1; enter_mode missing and heartbeat
        failing"""
        for method in combinations_of_test_methods(
            enter_mode=[METHOD_MISSING],
            heartbeat=[False],
            exit_mode=METHOD_OPTIONS,
        ):
            success, err_message, heartbeat_call_time = try_enter_and_heartbeat(method)
            # Expecting
            # * heartbeat to FAIL (-> success is False)
            # * Error message saying that can only return None
            # * No heartbeat_call_time (None)
            assert success is False
            assert "returned an unsupported value False." in err_message
            assert "The only accepted return value is None" in err_message
            assert heartbeat_call_time is None

        for method in combinations_of_test_methods(
            enter_mode=[METHOD_MISSING],
            heartbeat=[FAILURE_REASON],
            exit_mode=METHOD_OPTIONS,
        ):
            success, err_message, heartbeat_call_time = try_enter_and_heartbeat(method)
            # Expecting same as above, but with failing message
            assert success is False
            assert f"returned an unsupported value {FAILURE_REASON}." in err_message
            assert "The only accepted return value is None" in err_message
            assert heartbeat_call_time is None

    @pytest.mark.usefixtures("mock_datetime")
    def test_enter_mode_missing_heartbeat_success(self):
        """Tests 4) MS from TABLE 1; enter_mode missing, heartbeat success"""

        for method in combinations_of_test_methods(
            enter_mode=[METHOD_MISSING],
            heartbeat=[None],
            exit_mode=METHOD_OPTIONS,
        ):
            res = try_enter_and_heartbeat(method)
            # Expecting: Return Success + '' +  heartbeat time
            assert res == (True, "", self.fake_datetime_now)

    def test_enter_mode_success_heartbeat_missing(self):
        """Tests 5) SM from TABLE 1; enter_mode success, heartbeat missing"""

        for method in combinations_of_test_methods(
            enter_mode=[None],
            heartbeat=[METHOD_MISSING],
            exit_mode=METHOD_OPTIONS,
        ):
            res = try_enter_and_heartbeat(method)
            # Expecting: Return Success + '' + None (no heartbeat)
            assert res == (True, "", None)

    def test_enter_mode_success_heartbeat_failing(self):
        """Tests 6) SF from TABLE 1; enter_mode success, heartbeat failing

        This should, in general Return Fail + heartbeat error message + call
        exit_mode() This call of exit_mode might be failing, so we test that
        separately
        """

        # Case: Heartbeate fails by raising RuntimeError
        for method in combinations_of_test_methods(
            enter_mode=[None],
            heartbeat=[RuntimeError(FAILURE_REASON)],
            exit_mode=[None, METHOD_MISSING],
        ):
            success, err_message, heartbeat_call_time = try_enter_and_heartbeat(method)
            assert success is False
            assert f"{FAILURE_REASON}" in err_message
            assert heartbeat_call_time is None

        # Case: The heartbeat fails, and because enter_mode() has succeed,
        # wakepy tries to call exit_mode(). If that fails, the program must
        # crash, as we are in an unknown state and this is clearly an error.
        for method in combinations_of_test_methods(
            enter_mode=[None],
            heartbeat=[False, FAILURE_REASON],
            exit_mode=[False, FAILURE_REASON],
        ):
            with pytest.raises(
                RuntimeError,
                match=re.escape(
                    f"Entered {method.__class__.__name__} ({method.name}) but could not"
                    " exit!"
                ),
            ):
                try_enter_and_heartbeat(method)

        # Case: Same as the one above, but this time exit_mode() raises a
        # WakepyMethodTestError. That is re-raised as RuntimeError, instead.
        # If this happens, the Method.exit_mode() has a bug.
        for method in combinations_of_test_methods(
            enter_mode=[None],
            heartbeat=[False, FAILURE_REASON],
            exit_mode=[WakepyMethodTestError("foo")],
        ):
            with pytest.raises(
                RuntimeError,
                match="foo",
            ):
                try_enter_and_heartbeat(method)

    @pytest.mark.usefixtures("mock_datetime")
    def test_enter_mode_success_heartbeat_success(self):
        """Tests 7) SS from TABLE 1; enter_mode success & heartbeat success"""
        for method in combinations_of_test_methods(
            enter_mode=[None],
            heartbeat=[None],
            exit_mode=METHOD_OPTIONS,
        ):
            res = try_enter_and_heartbeat(method)
            # Expecting Return Success + '' + heartbeat time
            assert res == (True, "", self.fake_datetime_now)

    def test_enter_mode_returns_bad_balue(self):
        # Case: returning bad value (None return value accepted)
        method = get_test_method_class(enter_mode=132)()
        success, err_message, heartbeat_call_time = try_enter_and_heartbeat(method)

        assert success is False
        assert "The only accepted return value is None" in err_message
        assert heartbeat_call_time is None

    def test_heartbeat_returns_bad_balue(self):
        # Case: returning bad value (None return value accepted)
        method = get_test_method_class(heartbeat=132)()
        success, err_message, heartbeat_call_time = try_enter_and_heartbeat(method)

        assert success is False
        assert "The only accepted return value is None" in err_message
        assert heartbeat_call_time is None

    fake_datetime_now = dt.datetime.strptime("2000-01-01 12:34:56", "%Y-%m-%d %H:%M:%S")

    @pytest.fixture
    def mock_datetime(self):
        with patch("wakepy.core.method.dt.datetime") as datetime:
            datetime.now.return_value = self.fake_datetime_now
            yield


class TestCanIUseFails:
    """test caniuse_fails"""

    @pytest.mark.parametrize(
        "params",
        [
            # True and None -> The check does not fail
            dict(caniuse=True, expected=(False, "")),
            dict(caniuse=None, expected=(False, "")),
            # If returning False, the check fails
            dict(caniuse=False, expected=(True, "")),
            # If returning a string, the check fails with a reason
            dict(caniuse="reason", expected=(True, "reason")),
            # If .caniuse() returns anything else than a string, that is
            # silently converted to a string, and the check fails.
            dict(caniuse=123, expected=(True, "123")),
        ],
    )
    def test_normal_cases(self, params):
        class SomeMethod(Method):
            def caniuse(self):
                return params["caniuse"]

        assert caniuse_fails(SomeMethod()) == params["expected"]

    def test_special_case(self):
        """Tests the case when Method.caniuse raises an exception"""
        err = ValueError("Cannot use")

        class SomeMethod(Method):
            def caniuse(self):
                raise err

        method = SomeMethod()
        assert caniuse_fails(method) == (True, str(err))


class TestDeactivateMethod:
    def test_success_no_heartbeat(self):
        method = get_test_method_class(enter_mode=None, exit_mode=None)()
        deactivate_method(method)

    def test_success_with_heartbeat(self, heartbeat1):
        method = get_test_method_class(
            enter_mode=None, heartbeat=None, exit_mode=None
        )()
        deactivate_method(method, heartbeat=heartbeat1)

    def test_success_with_heartbeat_and_no_exit(self, heartbeat1):
        method = get_test_method_class(enter_mode=None, heartbeat=None)()
        deactivate_method(method, heartbeat=heartbeat1)

    def test_fail_deactivation_at_exit_mode_bad_value(self):
        method = get_test_method_class(enter_mode=None, exit_mode=123)()
        with pytest.raises(
            RuntimeError,
            match=re.escape(
                f"The exit_mode of '{method.__class__.__name__}' ({method.name}) was "
                "unsuccessful!"
            )
            + " .* "
            + re.escape("Original error: exit_mode returned a value other than None!"),
        ):
            deactivate_method(method)

    def test_fail_deactivation_at_exit_mode_raises_exception(self):
        method = get_test_method_class(enter_mode=None, exit_mode=Exception("oh no"))()
        with pytest.raises(
            RuntimeError,
            match=re.escape(
                f"The exit_mode of '{method.__class__.__name__}' ({method.name}) was "
                "unsuccessful"
            )
            + ".*"
            + re.escape("Original error: oh no"),
        ):
            deactivate_method(method)

    def test_fail_deactivation_heartbeat_not_stopping(self, heartbeat2_bad):
        method = get_test_method_class(enter_mode=None, exit_mode=None)()
        with pytest.raises(
            RuntimeError,
            match=re.escape(
                f"The heartbeat of {method.__class__.__name__} ({method.name}) could "
                "not be stopped! Suggesting submitting a bug report and rebooting for "
                "clearing the mode."
            ),
        ):
            deactivate_method(method, heartbeat2_bad)


def test_stagename(assert_strenum_values):
    assert StageName.PLATFORM_SUPPORT == "PLATFORM_SUPPORT"
    assert StageName.ACTIVATION == "ACTIVATION"
    assert StageName.REQUIREMENTS == "REQUIREMENTS"
    assert StageName.WAKEPY_FORCE_FAILURE == "WAKEPY_FORCE_FAILURE"
    assert_strenum_values(StageName, StageNameValue)
