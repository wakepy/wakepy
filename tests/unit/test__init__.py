import sys

import pytest

import wakepy


def test_imports():
    """tests the public API"""
    from wakepy import ActivationError as ActivationError
    from wakepy import ActivationResult as ActivationResult
    from wakepy import Method as Method
    from wakepy import MethodActivationResult as MethodActivationResult
    from wakepy import Mode as Mode
    from wakepy import ModeExit as ModeExit
    from wakepy import keep as keep


@pytest.mark.skipif(
    not sys.platform.lower().startswith("linux"),
    reason="dbus methods only supported on linux",
)
def test_import_dbus():
    from wakepy import JeepneyDBusAdapter as JeepneyDBusAdapter


def test_successful_attribute_access():
    """sanity check that the lazy-loading does not mess up anything"""
    wakepy.Method
    wakepy.keep


def test_failing_import():
    with pytest.raises(AttributeError):
        wakepy.something_that_does_not_exist
