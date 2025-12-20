"""This module tests the Freedesktop.org specific methods.

These tests do *not* use IO / real or fake DBus calls. Instead, a special dbus
adapter is used which simply asserts the Call objects and returns what we
would expect from a dbus service."""

import os
import re
from unittest.mock import patch

import pytest

from wakepy.core.dbus import BusType, DBusAdapter, DBusAddress, DBusMethod
from wakepy.methods.freedesktop import (
    FreedesktopPowerManagementInhibit,
    FreedesktopScreenSaverInhibit,
    _get_current_desktop_environment,
    _get_kde_plasma_version,
)

screen_saver = DBusAddress(
    bus=BusType.SESSION,
    service="org.freedesktop.ScreenSaver",
    path="/org/freedesktop/ScreenSaver",
    interface="org.freedesktop.ScreenSaver",
)

power_management = DBusAddress(
    bus=BusType.SESSION,
    service="org.freedesktop.PowerManagement",
    path="/org/freedesktop/PowerManagement/Inhibit",
    interface="org.freedesktop.PowerManagement.Inhibit",
)

fake_cookie = 75848243423


def get_test_dbus_adapter(process) -> DBusAdapter:
    class TestAdapter(DBusAdapter):

        def process(self, call):
            return process(call)

    return TestAdapter()


class TestFreedesktopEnterMode:

    @pytest.mark.parametrize(
        "method_cls, dbus_address",
        [
            (FreedesktopScreenSaverInhibit, screen_saver),
            (FreedesktopPowerManagementInhibit, power_management),
        ],
    )
    def test_success(self, method_cls, dbus_address: DBusAddress):

        method_inhibit = DBusMethod(
            name="Inhibit",
            signature="ss",
            params=("application_name", "reason_for_inhibit"),
            output_signature="u",
            output_params=("cookie",),
        )

        def process(call):
            assert call.method == method_inhibit.of(dbus_address)
            assert call.get_kwargs() == {
                "application_name": "wakepy",
                "reason_for_inhibit": "wakelock active",
            }

            return (fake_cookie,)

        method = method_cls(dbus_adapter=get_test_dbus_adapter(process))
        # At the start, there is no inhibit cookie.
        assert method.inhibit_cookie is None

        # Act
        enter_retval = method.enter_mode()

        # Assert
        assert enter_retval is None
        # Entering mode sets a inhibit_cookie to value returned by the
        # DBusAdapter
        assert method.inhibit_cookie == fake_cookie

    @pytest.mark.parametrize(
        "method_cls",
        [FreedesktopScreenSaverInhibit, FreedesktopPowerManagementInhibit],
    )
    def test_with_dbus_adapter_which_returns_none(self, method_cls):

        def process(_):
            return None

        method = method_cls(dbus_adapter=get_test_dbus_adapter(process))

        with pytest.raises(
            RuntimeError,
            match=re.escape(f"Could not get inhibit cookie from {method_cls.name}"),
        ):
            assert method.enter_mode() is False


class TestFreedesktopExitMode:

    @pytest.mark.parametrize(
        "method_cls, dbus_address",
        [
            (FreedesktopScreenSaverInhibit, screen_saver),
            (FreedesktopPowerManagementInhibit, power_management),
        ],
    )
    def test_successful_exit(self, method_cls, dbus_address: DBusAddress):
        # Arrange

        method_uninhibit = DBusMethod(
            name="UnInhibit",
            signature="u",
            params=("cookie",),
        ).of(dbus_address)

        def process(call):
            assert call.method == method_uninhibit
            assert call.get_kwargs() == {"cookie": fake_cookie}

        method = method_cls(dbus_adapter=get_test_dbus_adapter(process))
        method.inhibit_cookie = fake_cookie

        # Act
        exit_retval = method.exit_mode()

        # Assert
        assert exit_retval is None
        # exiting mode unsets the inhibit_cookie
        assert method.inhibit_cookie is None

    @pytest.mark.parametrize(
        "method_cls",
        [FreedesktopScreenSaverInhibit, FreedesktopPowerManagementInhibit],
    )
    def test_screensaver_exit_before_enter(self, method_cls):
        method = method_cls(dbus_adapter=DBusAdapter())
        assert method.inhibit_cookie is None
        assert method.exit_mode() is None


class TestPowerManagementCanIUse:

    def test_on_kde_5_12_90(self, monkeypatch):
        # Should support KDE 5.12.90 +
        monkeypatch.setenv("XDG_SESSION_DESKTOP", "KDE")

        method = FreedesktopPowerManagementInhibit()

        with patch(
            "wakepy.methods.freedesktop.subprocess.getoutput",
            return_value="plasmashell 5.12.90",
        ):
            assert method.caniuse() is True

    def test_on_kde_6_0_0(self, monkeypatch):
        # Should support KDE 5.12.90 +
        monkeypatch.setenv("XDG_SESSION_DESKTOP", "KDE")

        method = FreedesktopPowerManagementInhibit()

        with patch(
            "wakepy.methods.freedesktop.subprocess.getoutput",
            return_value="plasmashell 6.0.0",
        ):
            assert method.caniuse() is True

    def test_on_kde_5_12_89(self, monkeypatch):
        monkeypatch.setenv("XDG_SESSION_DESKTOP", "KDE")

        method = FreedesktopPowerManagementInhibit()

        with patch(
            "wakepy.methods.freedesktop.subprocess.getoutput",
            return_value="plasmashell 5.12.89",
        ):
            with pytest.raises(
                RuntimeError,
                match=re.escape(
                    "org.freedesktop.PowerManagement only supports KDE >= 5.12.90"
                ),
            ):
                method.caniuse()

    def test_on_kde_version_none(self, monkeypatch):
        monkeypatch.setenv("XDG_SESSION_DESKTOP", "KDE")

        method = FreedesktopPowerManagementInhibit()

        with patch(
            "wakepy.methods.freedesktop.subprocess.getoutput",
            return_value="noversion",
        ):
            with pytest.raises(
                RuntimeError,
                match=re.escape(
                    "Running on KDE but could not detect KDE Plasma version"
                ),
            ):
                method.caniuse()

    def test_on_other_de(self, monkeypatch):
        monkeypatch.setenv("XDG_SESSION_DESKTOP", "RandomDE")

        method = FreedesktopPowerManagementInhibit()

        with patch(
            "wakepy.methods.freedesktop.subprocess.getoutput",
            return_value="foo",
        ):
            assert method.caniuse() is True

    def test_on_other_xfce(self, monkeypatch):
        monkeypatch.setenv("XDG_SESSION_DESKTOP", "XFCE")

        method = FreedesktopPowerManagementInhibit()

        with pytest.raises(
            RuntimeError,
            match=re.escape(
                "org.freedesktop.PowerManagement does not support XFCE as it has a bug "
                "which prevents automatic screenlock / screensaver. See: "
                "https://gitlab.xfce.org/xfce/xfce4-power-manager/-/issues/65"
            ),
        ):
            method.caniuse()


class TestGetKDEPlasmaVersion:
    def test_success(self):

        with patch(
            "wakepy.methods.freedesktop.subprocess.getoutput",
            return_value="plasmashell 1.2.3",
        ):
            assert _get_kde_plasma_version() == (1, 2, 3)

    def test_success2(self):
        with patch(
            "wakepy.methods.freedesktop.subprocess.getoutput",
            return_value="plasmashell 4.5.6",
        ):
            assert _get_kde_plasma_version() == (4, 5, 6)

    def test_success_with_additional_text_same_line(self):
        with patch(
            "wakepy.methods.freedesktop.subprocess.getoutput",
            return_value="FOO plasmashell 4.5.6post-123 BAR",
        ):
            assert _get_kde_plasma_version() == (4, 5, 6)

    def test_success_qthread_storage_pre(self):
        # Test for bug: https://github.com/wakepy/wakepy/issues/415
        with patch(
            "wakepy.methods.freedesktop.subprocess.getoutput",
            return_value="QThreadStorage: entry 3 destroyed before end of thread 0x61b4ee73d540\nQThreadStorage: entry 2 destroyed before end of thread 0x61b4ee73d540\nplasmashell 6.3.4",  # noqa: E501
        ):
            assert _get_kde_plasma_version() == (6, 3, 4)

    def test_success_qthread_storage_post(self):
        # Test for bug: https://github.com/wakepy/wakepy/issues/415
        with patch(
            "wakepy.methods.freedesktop.subprocess.getoutput",
            return_value="plasmashell 6.3.4\nQThreadStorage: entry 3 destroyed before end of thread 0x61b4ee73d540\nQThreadStorage: entry 2 destroyed before end of thread 0x61b4ee73d540",  # noqa: E501
        ):
            assert _get_kde_plasma_version() == (6, 3, 4)

    def test_success_qthread_storage_mid(self):
        # Test for bug: https://github.com/wakepy/wakepy/issues/415
        with patch(
            "wakepy.methods.freedesktop.subprocess.getoutput",
            return_value="QThreadStorage: entry 3 destroyed before end of thread 0x61b4ee73d540\nplasmashell 6.3.4\nQThreadStorage: entry 2 destroyed before end of thread 0x61b4ee73d540",  # noqa: E501
        ):
            assert _get_kde_plasma_version() == (6, 3, 4)

    def test_bad_output(self):
        with patch(
            "wakepy.methods.freedesktop.subprocess.getoutput",
            return_value="foo",
        ):
            assert _get_kde_plasma_version() is None

    def test_unknown_command(self):
        with patch(
            "wakepy.methods.freedesktop.subprocess.getoutput",
            return_value="If 'plasmashell' is not a typo you can use command-not-found"
            " to lookup the package that contains it, like this: cnf fooo",
        ):
            assert _get_kde_plasma_version() is None


class TestGetCurrentDesktopEnvironment:

    def test_kde(self, monkeypatch):
        monkeypatch.setenv("XDG_SESSION_DESKTOP", "KDE")
        assert _get_current_desktop_environment() == "KDE"

    def test_xfce(self, monkeypatch):
        monkeypatch.setenv("XDG_SESSION_DESKTOP", "xfce")
        assert _get_current_desktop_environment() == "XFCE"

    def test_not_set(self, monkeypatch):
        if os.environ.get("XDG_SESSION_DESKTOP"):
            monkeypatch.delenv("XDG_SESSION_DESKTOP")
        assert _get_current_desktop_environment() is None

    def test_other(self, monkeypatch):
        monkeypatch.setenv("XDG_SESSION_DESKTOP", "FOO")
        assert _get_current_desktop_environment() == "FOO"
