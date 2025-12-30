from __future__ import annotations

import logging
import os
import platform
import sys
import sysconfig
import typing
import warnings
from pathlib import Path

from .constants import IdentifiedPlatformType, PlatformType

if typing.TYPE_CHECKING:
    from typing import Callable, Dict, Tuple

    PlatformFunc = Callable[[IdentifiedPlatformType], bool]


logger = logging.getLogger(__name__)


def get_current_platform() -> IdentifiedPlatformType:
    # Ref: https://docs.python.org/3/library/platform.html#platform.system
    system = platform.system()
    if system == "Windows":
        return IdentifiedPlatformType.WINDOWS
    elif system == "Darwin":
        return IdentifiedPlatformType.MACOS
    elif system == "Linux":
        return IdentifiedPlatformType.LINUX
    elif system == "FreeBSD":
        return IdentifiedPlatformType.FREEBSD

    warnings.warn(
        f"Could not detect current platform! Debug info:\n{get_platform_debug_info()}",
        stacklevel=8,
    )
    return IdentifiedPlatformType.UNKNOWN


def get_platform_debug_info() -> str:
    info_dict = get_platform_debug_info_dict()
    return "\n".join(f"- {key}: {val}" for key, val in info_dict.items())


def get_platform_debug_info_dict() -> Dict[str, str]:
    info = dict()
    try:
        info["os.name"] = os.name
        info["sys.platform"] = sys.platform
        info["platform.system()"] = platform.system()
        info["platform.release()"] = platform.release()
        info["platform.machine()"] = platform.machine()
        info["sysconfig.get_platform()"] = sysconfig.get_platform()
        info["DESKTOP_SESSION"] = os.environ.get("DESKTOP_SESSION", "[not set]")
        os_release_info = get_etc_os_release()
        info.update(os_release_info)
    except Exception:
        # This should never happen, but better to be safe.
        logger.error("Error in creating platform debug info", exc_info=True)
        warnings.warn("Error in creating platform debug info")

    return info


def get_etc_os_release() -> dict[str, str]:
    """Get metadata about OS release from /etc/os-release file or, if that is
    missing, from /etc/lsb-release. If neither of the files exist, returns an
    empty dictionary. Otherwise, returns key-value pairs from the release
    file."""

    if Path(ETC_OS_RELEASE_PATH).exists():
        release_file = ETC_OS_RELEASE_PATH
    elif Path(ETC_LSB_RELEASE_PATH).exists():
        release_file = ETC_LSB_RELEASE_PATH
    else:
        return dict()

    out = dict()
    with open(release_file) as f:
        for line in f:
            key, value = line.split("=", maxsplit=1)
            if key in IGNORED_RELEASE_FILE_KEYS:
                continue
            key_out = f"({release_file}) {key}"
            out[key_out] = value.strip()
    return out


ETC_OS_RELEASE_PATH = "/etc/os-release"
ETC_LSB_RELEASE_PATH = "/etc/lsb-release"

# keys ignored in /etc/os-release and /etc/lsb-release files
IGNORED_RELEASE_FILE_KEYS = [
    "ANSI_COLOR",
    "LOGO",
    "CPE_NAME",
    "DEFAULT_HOSTNAME",
    "HOME_URL",
    "DOCUMENTATION_URL",
    "SUPPORT_URL",
    "SUPPORT_END",
    "BUG_REPORT_URL",
    "REDHAT_BUGZILLA_PRODUCT",
    "REDHAT_BUGZILLA_PRODUCT_VERSION",
    "REDHAT_SUPPORT_PRODUCT",
    "REDHAT_SUPPORT_PRODUCT_VERSION",
]

CURRENT_PLATFORM: IdentifiedPlatformType = get_current_platform()
"""The current platform as detected. If the platform cannot be detected,
defaults to ``UNKNOWN``."""


def get_platform_supported(
    platform: IdentifiedPlatformType, supported_platforms: Tuple[PlatformType, ...]
) -> bool | None:
    """Checks if a platform is in the supported platforms.

    Parameters
    ----------
    platform: IdentifiedPlatformType
        The platform to check.
    supported_platforms:
        The platforms to check against.

    Returns
    -------
    is_supported: bool | None
        If platform is supported, returns True. If the support is unknown,
        returns None, and if the platform is not supported, returns False.
    """
    for supported_platform in supported_platforms:
        func = PLATFORM_INFO_FUNCS[supported_platform]
        if func(platform) is True:
            return True
    if is_unknown(platform):
        return None
    return False


def is_windows(current_platform: IdentifiedPlatformType) -> bool:
    return current_platform == IdentifiedPlatformType.WINDOWS


def is_linux(current_platform: IdentifiedPlatformType) -> bool:
    return current_platform == IdentifiedPlatformType.LINUX


def is_freebsd(current_platform: IdentifiedPlatformType) -> bool:
    return current_platform == IdentifiedPlatformType.FREEBSD


def is_macos(current_platform: IdentifiedPlatformType) -> bool:
    return current_platform == IdentifiedPlatformType.MACOS


def is_bsd(current_platform: IdentifiedPlatformType) -> bool:
    return is_freebsd(current_platform)


def is_unknown(current_platform: IdentifiedPlatformType) -> bool:
    return current_platform == IdentifiedPlatformType.UNKNOWN


def is_unix_like_foss(current_platform: IdentifiedPlatformType) -> bool:
    return is_bsd(current_platform) or is_linux(current_platform)


PLATFORM_INFO_FUNCS: dict[PlatformType, PlatformFunc] = {
    PlatformType.WINDOWS: is_windows,
    PlatformType.LINUX: is_linux,
    PlatformType.MACOS: is_macos,
    PlatformType.FREEBSD: is_freebsd,
    PlatformType.UNKNOWN: is_unknown,
    PlatformType.BSD: is_bsd,
    PlatformType.ANY: lambda _: True,
    PlatformType.UNIX_LIKE_FOSS: is_unix_like_foss,
}
