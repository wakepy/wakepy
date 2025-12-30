from unittest.mock import patch

import pytest

from wakepy.core.dbus import (
    BusType,
    DBusAdapter,
    DBusAddress,
    DBusMethod,
    DBusMethodCall,
    get_dbus_adapter,
    get_default_dbus_adapter,
)

session_manager = DBusAddress(
    bus=BusType.SESSION,
    service="org.gnome.SessionManager",
    path="/org/gnome/SessionManager",
    interface="org.gnome.SessionManager",
)


@pytest.fixture
def method_inhibit():
    return DBusMethod(
        name="Inhibit",
        signature="susu",
        params=("app_id", "toplevel_xid", "reason", "flags"),
        output_signature="u",
        output_params=("inhibit_cookie",),
    )


@pytest.fixture
def args_for_inhibit():
    return "first", 123, "third", 567


def test_dbus_method_to_call(method_inhibit, args_for_inhibit):
    method_inhibit = method_inhibit.of(session_manager)

    call = method_inhibit.to_call(args_for_inhibit)

    assert isinstance(call, DBusMethodCall)
    assert call.args == args_for_inhibit
    assert call.method == method_inhibit


def test_dbus_method_to_call_not_fully_defined_method(method_inhibit, args_for_inhibit):
    # The method is not fully defined as it is not tied to any address.
    with pytest.raises(
        ValueError, match="DBusMethodCall requires completely defined DBusMethod"
    ):
        method_inhibit.to_call(args_for_inhibit)


@pytest.fixture(scope="session")
def unsupported_dbus_adapter():
    class DBusAdapterNotSupported(DBusAdapter):
        def __init__(self):
            raise Exception("not supported")

    return DBusAdapterNotSupported


@pytest.fixture(scope="session")
def supported_dbus_adapter():
    class DBusAdapterSupported(DBusAdapter):
        """This one does not raise Exception on __init__ so it's supported"""

    return DBusAdapterSupported


class TestGetDbusAdapter:
    """Tests for get_dbus_adapter"""

    def test_get_first_working_one_in_list(
        self, unsupported_dbus_adapter, supported_dbus_adapter
    ):
        adapter = get_dbus_adapter([unsupported_dbus_adapter, supported_dbus_adapter])
        assert isinstance(adapter, supported_dbus_adapter)

    def test_get_first_working_one_in_list_reversed(
        self, unsupported_dbus_adapter, supported_dbus_adapter
    ):
        adapter = get_dbus_adapter([supported_dbus_adapter, unsupported_dbus_adapter])
        assert isinstance(adapter, supported_dbus_adapter)

    def test_no_supported_adapters(self, unsupported_dbus_adapter):
        adapter = get_dbus_adapter([unsupported_dbus_adapter])
        assert adapter is None


def test_get_default_dbus_adapter_nonworking():
    with patch.dict("sys.modules", {"wakepy.dbus_adapters.jeepney": None}):
        # When jeepney is not installed, there is not default dbus adapter
        assert get_default_dbus_adapter() is None


def test_get_default_dbus_adapter_working():
    try:
        import jeepney as jeepney  # noqa
    except Exception:
        assert get_default_dbus_adapter() is None
    else:
        from wakepy import JeepneyDBusAdapter

        # When jeepney is installed, we get the JeepneyDBusAdapter as default.
        assert isinstance(get_default_dbus_adapter(), JeepneyDBusAdapter)
