"""Common terms and definitions used in many places"""

import sys
from typing import List, Set, Tuple, TypeVar, Union

from .strenum import StrEnum, auto

if sys.version_info < (3, 8):  # pragma: no-cover-if-py-gte-38
    from typing_extensions import Literal
else:  # pragma: no-cover-if-py-lt-38
    from typing import Literal

WAKEPY_FAKE_SUCCESS_METHOD = "WakepyFakeSuccess"
"""Name of the Wakepy fake success method"""

# This variable should only contain lower-case characters.
FALSY_ENV_VAR_VALUES = ("0", "no", "false", "n", "f", "")
"""The falsy environment variable values. All other values are considered to be
truthy. These values are case insensitive; Also "NO", "False" and "FALSE" are
falsy.
"""


class IdentifiedPlatformType(StrEnum):
    """The type identifier for the (:attr:`~wakepy.core.platform.CURRENT_PLATFORM`).
    Any process will be categorized into exactly one
    :class:`IdentifiedPlatformType` type; these are mutually exclusive options.
    Any platform that is not detected will be labeled as ``UNKNOWN``.

    See also: :class:`PlatformType`, which you should use with Method
    subclasses."""  # noqa: W505

    WINDOWS = auto()
    LINUX = auto()
    MACOS = auto()
    FREEBSD = auto()
    UNKNOWN = auto()


class PlatformType(StrEnum):
    """Enumeration for supported platform types. Each identified platform can
    be categorized to at least one, but potentially many of these. In other
    words, each :class:`IdentifiedPlatformType` (type of
    :attr:`~wakepy.core.platform.CURRENT_PLATFORM`) maps into one or many
    ``PlatformType``.

    To be used in subclasses of :class:`~wakepy.Method` in the
    :meth:`~wakepy.Method.supported_platforms`.
    """

    # All of the IdentifiedPlatformType are always part of the PlatformType
    # (also enforced with a test)
    WINDOWS = IdentifiedPlatformType.WINDOWS.value
    """Any Windows version from Windows 10 onwards."""

    LINUX = IdentifiedPlatformType.LINUX.value
    """Includes any Linux distro. Excludes things like  Android &  ChromeOS"""

    MACOS = IdentifiedPlatformType.MACOS.value
    """Mac OS (Darwin)"""

    FREEBSD = IdentifiedPlatformType.FREEBSD.value
    """FreeBSD. Also includes GhostBSD"""

    UNKNOWN = IdentifiedPlatformType.UNKNOWN.value
    """Any non-identified platform"""

    # These are special, combined platform types that make it easier to
    # define the MethodSubclass.supported_platforms.
    BSD = auto()
    """Any BSD system (Currently just FreeBSD / GhostBSD, but is likely to
    change in the future)."""

    UNIX_LIKE_FOSS = auto()
    """Unix-like desktop environment, but FOSS. Includes: LINUX and BSD.
    Excludes: Android (mobile), MacOS (non-FOSS), ChromeOS (non-FOSS)."""

    ANY = auto()
    """Means any platform."""


class ModeName(StrEnum):
    """The names of the modes wakepy supports

    See: :ref:`wakepy-modes` for full definitions of the modes.
    """

    KEEP_RUNNING = "keep.running"
    KEEP_PRESENTING = "keep.presenting"


ModeNameValue = Literal["keep.running", "keep.presenting"]


class BusType(StrEnum):
    """Type of D-Bus bus."""

    SESSION = auto()
    SYSTEM = auto()


BusTypeValue = Literal["SESSION", "SYSTEM"]


class StageName(StrEnum):
    # These are stages which occur in order for each of the methods
    # when using a Method for activation.

    NONE = auto()  # No stage at all.

    # The stages in the activation process in order
    PLATFORM_SUPPORT = auto()
    REQUIREMENTS = auto()
    ACTIVATION = auto()


StageNameValue = Literal["NONE", "PLATFORM_SUPPORT", "REQUIREMENTS", "ACTIVATION"]

# Type annotations
T = TypeVar("T")
Collection = Union[List[T], Tuple[T, ...], Set[T]]
StrCollection = Collection[str]
