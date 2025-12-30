import re

import pytest

from wakepy.core import DBusAddress, DBusMethod, DBusMethodCall


@pytest.fixture
def method_without_params(service):
    service = DBusAddress(path="/foo", service="wakepy.foo", interface="/foo")
    return DBusMethod(
        name="test-method",
        signature="isi",
    ).of(service)


def test_dbusmethod_args_none(dbus_method: DBusMethod):
    call = DBusMethodCall(dbus_method, args=None)
    assert call.args == tuple()


def test_dbusmethod_args_missing(dbus_method: DBusMethod):
    call = DBusMethodCall(dbus_method)
    assert call.args == tuple()


def test_dbusmethod_args_tuple(dbus_method: DBusMethod):
    args = (1, "2", 3)
    call = DBusMethodCall(dbus_method, args=args)
    assert call.args == args


def test_dbusmethod_args_tuple_too_long(dbus_method: DBusMethod):
    args = (1, "2", 3, 4)
    with pytest.raises(
        ValueError,
        match=re.escape("Expected args to have 3 items! (has: 4)"),
    ):
        DBusMethodCall(dbus_method, args=args)


def test_dbusmethod_args_tuple_too_short(dbus_method: DBusMethod):
    args = (1, "2")
    with pytest.raises(
        ValueError,
        match=re.escape("Expected args to have 3 items! (has: 2)"),
    ):
        DBusMethodCall(dbus_method, args=args)


def test_dbusmethod_args_list(dbus_method: DBusMethod):
    args = [1, "2", 3]
    call = DBusMethodCall(dbus_method, args=args)
    assert call.args == (1, "2", 3)


def test_dbusmethod_args_invalid_type(dbus_method: DBusMethod):
    args = 123  # Invalid type: not a tuple, list, or dict
    with pytest.raises(
        ValueError,
        match=re.escape("args may only be tuple, list or dict. Got: <class 'int'>"),
    ):
        DBusMethodCall(dbus_method, args=args)  # type: ignore[arg-type]


def test_dbusmethod_args_dict_method_without_params(
    method_without_params: DBusMethod,
):
    args = dict(first=1, second="2", third=3)
    with pytest.raises(
        ValueError,
        match=re.escape(
            "args cannot be a dictionary if method does not have the params defined! "
            "Either add params to the DBusMethod 'test-method' or give args as a tuple "
            "or a list."
        ),
    ):
        DBusMethodCall(method_without_params, args=args)


def test_dbusmethod_args_dict_too_many_keys(dbus_method: DBusMethod):
    args = dict(first=1, second="2", third=3, fourth=4)

    with pytest.raises(
        ValueError,
        match=re.escape("Expected args to have 3 items! (has: 4)"),
    ):
        DBusMethodCall(dbus_method, args=args)


def test_dbusmethod_args_dict_too_few_keys(dbus_method: DBusMethod):
    args = dict(first=1, second="2")

    with pytest.raises(
        ValueError,
        match=re.escape("Expected args to have 3 items! (has: 2)"),
    ):
        DBusMethodCall(dbus_method, args=args)


def test_dbusmethod_args_dict_wrong_keys(dbus_method: DBusMethod):
    args = dict(first=1, second="2", fifth="2")

    with pytest.raises(
        ValueError,
        match=re.escape(
            "The keys in `args` do not match the keys in the DBusMethod params! "
            "Expected: ('first', 'second', 'third'). Got: ('first', 'second', 'fifth')"
        ),
    ):
        DBusMethodCall(dbus_method, args=args)


def test_dbusmethod_args_dict(dbus_method: DBusMethod):
    args = dict(first=1, second="2", third=3)
    call = DBusMethodCall(dbus_method, args=args)
    assert call.args == (1, "2", 3)


def test_dbusmethod_args_dict_different_order(dbus_method: DBusMethod):
    args = dict(third=3, first=1, second="2")
    call = DBusMethodCall(dbus_method, args=args)
    assert call.args == (1, "2", 3)


def test_dbusmethod_get_kwargs(dbus_method: DBusMethod):
    args = (1, "2", 3)
    call = DBusMethodCall(dbus_method, args=args)
    assert call.get_kwargs() == dict(first=1, second="2", third=3)


def test_dbusmethod_get_kwargs_noparams(method_without_params: DBusMethod):
    args = (1, "2", 3)
    call = DBusMethodCall(method_without_params, args=args)
    # Not possible to convert to args to dict as the params are not named.
    assert call.get_kwargs() is None


def test_dbusmethod_string_representation(dbus_method: DBusMethod):
    args = (1, "2", 3)
    call = DBusMethodCall(dbus_method, args=args)
    assert call.__repr__() == "<wakepy.foo (1, '2', 3) | bus: SESSION>"
