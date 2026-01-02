"""This module defines the WakepyFakeSuccess method, which can be used to fake
activation success. It is controlled with the WAKEPY_FAKE_SUCCESS environment
variable and meant to be used in CI pipelines / tests."""

from wakepy.core import Method, PlatformType
from wakepy.core.constants import WAKEPY_FAKE_SUCCESS_METHOD


class WakepyFakeSuccess(Method):
    """This is a special fake method to be used with any mode. It can be used
    in tests for faking wakepy mode activation. This way all IO and real
    executable, library and dbus calls are prevented. To use this method (and
    skip using any other methods), set WAKEPY_FAKE_SUCCESS environment variable
    to a truthy value (e.g. "1", or "True").
    """

    name = WAKEPY_FAKE_SUCCESS_METHOD
    mode_name = "_fake"
    supported_platforms = (PlatformType.ANY,)

    def enter_mode(self) -> None:
        """Does nothing ("succeeds" automatically; Will never raise an
        Exception)"""
