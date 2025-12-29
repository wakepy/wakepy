import logging

from wakepy import keep
from wakepy.core import ModeName, PlatformType
from wakepy.methods import macos


class DummyMacCaffeinate(macos._MacCaffeinate):
    """Test class for _MacCaffeinate to allow instantiation."""

    command = ["ls"]  # some linux command for testing
    name = "DummyMacCaffeinate"
    mode_name = ModeName.KEEP_RUNNING
    supported_platforms = (PlatformType.ANY,)


def test_mac_caffeinate_context_manager():
    """Test that the context manager works as expected."""

    # If this does to raise an Exception, the context manager works as
    # expected.
    with keep.running(methods=["DummyMacCaffeinate"], on_fail="error"):
        ...


def test_exit_before_enter(caplog):
    method = DummyMacCaffeinate()

    # Act
    with caplog.at_level(logging.DEBUG):
        method.exit_mode()

    # Assert
    assert caplog.text.startswith("DEBUG ")
    assert "No need to terminate process (not started)" in caplog.text
