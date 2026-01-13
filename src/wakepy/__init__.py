# NOTE The methods sub-package is imported for registering all the methods.
from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from typing import Type

from . import methods as methods

try:
    from ._version import __version__ as __version__
    from ._version import version_tuple as version_tuple
except ImportError:  # pragma: no cover
    # Likely an editable install. Should never happen if installed from a
    # distribution package (sdist or wheel)
    __version__ = "undefined"
    version_tuple = (0, 0, 0, "undefined")


from .core import ActivationError as ActivationError
from .core import ActivationResult as ActivationResult
from .core import ActivationWarning as ActivationWarning
from .core import ContextAlreadyEnteredError as ContextAlreadyEnteredError
from .core import DBusAdapter as DBusAdapter
from .core import Method as Method
from .core import MethodActivationResult as MethodActivationResult
from .core import MethodInfo as MethodInfo
from .core import Mode as Mode
from .core import ModeExit as ModeExit
from .core import ModeName as ModeName
from .core import NoCurrentModeError as NoCurrentModeError
from .core import ProbingResults as ProbingResults
from .core import current_mode as current_mode
from .core import global_modes as global_modes
from .core import modecount as modecount
from .modes import keep as keep

JeepneyDBusAdapter: Type[DBusAdapter]
"""This is lazily imported below. The reason for this is that not all systems
support DBus, but it's nice to be able to import this directly from wakepy
top level package."""


def __getattr__(name: str) -> object:
    """Some lazy implementation of lazy loading.

    See: https://peps.python.org/pep-0562/
    """
    if name == "JeepneyDBusAdapter":
        from wakepy.dbus_adapters.jeepney import JeepneyDBusAdapter

        return JeepneyDBusAdapter  # pragma: no-cover-if-no-dbus
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
