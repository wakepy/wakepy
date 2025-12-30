import re
import textwrap
from unittest.mock import Mock, mock_open, patch

import pytest

from wakepy.core import PlatformType
from wakepy.core.constants import IdentifiedPlatformType
from wakepy.core.platform import (
    get_current_platform,
    get_etc_os_release,
    get_platform_debug_info,
    get_platform_debug_info_dict,
    get_platform_supported,
)

P = IdentifiedPlatformType


class TestGetCurrentPlatform:
    @patch("platform.system", lambda: "Windows")
    def test_windows(self):
        assert get_current_platform() == PlatformType.WINDOWS

    @patch("platform.system", lambda: "Darwin")
    def test_macos(self):
        assert get_current_platform() == PlatformType.MACOS

    @patch("platform.system", lambda: "Linux")
    def test_linux(self):
        assert get_current_platform() == PlatformType.LINUX

    @patch("platform.system", lambda: "FreeBSD")
    def test_bsd(self):
        assert get_current_platform() == PlatformType.FREEBSD

    @patch("platform.system", lambda: "This does not exist")
    def test_other(self):
        with pytest.warns(UserWarning, match="Could not detect current platform!"):
            assert get_current_platform() == PlatformType.UNKNOWN


class TestPlatformSupported:
    """tests for get_platform_supported"""

    def test_windows(self):
        # On Windows, anything that supports Windows is supported.
        assert get_platform_supported(P.WINDOWS, (PlatformType.WINDOWS,)) is True
        assert (
            get_platform_supported(
                P.WINDOWS,
                (PlatformType.MACOS, PlatformType.WINDOWS, PlatformType.LINUX),
            )
            is True
        )

        # If there is no windows in the supported platforms, get False
        assert get_platform_supported(P.WINDOWS, (PlatformType.LINUX,)) is False
        assert (
            get_platform_supported(P.WINDOWS, (PlatformType.LINUX, PlatformType.BSD))
            is False
        )
        # Unless there is ANY, which means anything is supported
        assert (
            get_platform_supported(
                P.WINDOWS, (PlatformType.LINUX, PlatformType.BSD, PlatformType.ANY)
            )
            is True
        )

    def test_unknown(self):
        # Unknown platform is always "unknown"; returns None
        assert get_platform_supported(P.UNKNOWN, (PlatformType.WINDOWS,)) is None
        assert get_platform_supported(P.UNKNOWN, (PlatformType.LINUX,)) is None
        # .. unless "ANY" is supported.
        assert get_platform_supported(P.UNKNOWN, (PlatformType.ANY,)) is True

    def test_freebsd(self):
        assert get_platform_supported(P.FREEBSD, (PlatformType.WINDOWS,)) is False
        assert get_platform_supported(P.FREEBSD, (PlatformType.FREEBSD,)) is True
        # FreeBSD is BSD
        assert get_platform_supported(P.FREEBSD, (PlatformType.BSD,)) is True
        # FreeBSD is unix like
        assert get_platform_supported(P.FREEBSD, (PlatformType.UNIX_LIKE_FOSS,)) is True

    def test_linux(self):
        assert get_platform_supported(P.LINUX, (PlatformType.WINDOWS,)) is False
        assert get_platform_supported(P.LINUX, (PlatformType.LINUX,)) is True
        # Linux is unix like
        assert get_platform_supported(P.LINUX, (PlatformType.UNIX_LIKE_FOSS,)) is True


class TestGetPlatformDebugInfoDict:
    def test_basic(self):
        info_dct = get_platform_debug_info_dict()
        assert isinstance(info_dct, dict)

        for key, val in info_dct.items():
            assert isinstance(key, str)
            assert isinstance(val, str)

    @staticmethod
    def raise_exc():
        raise Exception("forced exception")

    @patch("wakepy.core.platform.platform", raise_exc)
    def test_exception(self):
        with pytest.warns(match="Error in creating platform debug info"):
            info_dct = get_platform_debug_info_dict()
        assert isinstance(info_dct, dict)
        assert len(info_dct) == 2


def test_get_platform_debug_info():
    debug_info = get_platform_debug_info()
    expected_out = textwrap.dedent(
        r"""
    - os.name: .*
    - sys.platform: .*
    - platform.system\(\): .*
    - platform.release\(\): .*
    - platform.machine\(\): .*
    - sysconfig.get_platform\(\): .*
    """.strip("\n")
    )
    # re.DOTALL makes . to match also the newlines.
    assert re.match(expected_out, debug_info, re.DOTALL)


mock_etc_os_release = """
NAME="Ubuntu"
FOO=123
BUG_REPORT_URL="http://this-is-skipped"
""".strip()

mock_etc_lsb_release = """
LSB_RELEASE_KEY="something"
BAR=456
""".strip()


def get_path_class_mock(os_release_exists: bool, lsb_release_exists: bool):
    def get_path_mock(filepath: str):
        pathmock = Mock()
        if filepath == "/etc/os-release":
            pathmock.exists.return_value = os_release_exists
        elif filepath == "/etc/lsb-release":
            pathmock.exists.return_value = lsb_release_exists
        else:
            raise NotImplementedError
        return pathmock

    path_class_mock = Mock()
    path_class_mock.side_effect = get_path_mock

    return path_class_mock


class TestGetEtcOsReleaseInfo:
    mock_os_release_exists = get_path_class_mock(
        os_release_exists=True, lsb_release_exists=False
    )

    @patch("wakepy.core.platform.Path", mock_os_release_exists)
    @patch("builtins.open", mock_open(read_data=mock_etc_os_release))
    def test_os_release(self):
        # Case: os-release file exists
        out = get_etc_os_release()
        assert out == {
            "(/etc/os-release) NAME": '"Ubuntu"',
            "(/etc/os-release) FOO": "123",
        }

    mock_etc_release_exists = get_path_class_mock(
        os_release_exists=False, lsb_release_exists=True
    )

    @patch("wakepy.core.platform.Path", mock_etc_release_exists)
    @patch("builtins.open", mock_open(read_data=mock_etc_lsb_release))
    def test_lsb_release(self):
        # Case: os-release file missing, but lsb-release file exists
        out = get_etc_os_release()
        assert out == {
            "(/etc/lsb-release) LSB_RELEASE_KEY": '"something"',
            "(/etc/lsb-release) BAR": "456",
        }

    neither_one_exists = get_path_class_mock(
        os_release_exists=False, lsb_release_exists=False
    )

    @patch("wakepy.core.platform.Path", neither_one_exists)
    @patch("builtins.open", mock_open(read_data=mock_etc_lsb_release))
    def test_no_release_files(self):
        # Case: os-release and lsb-release files missing
        out = get_etc_os_release()
        assert out == dict()
