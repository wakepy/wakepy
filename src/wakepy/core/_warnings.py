"""Locate application callers without warnings.warn's second stack walk."""

from __future__ import annotations

import contextlib
import sys
import typing
import warnings

if typing.TYPE_CHECKING:
    from types import FrameType, TracebackType
    from typing import Optional, Type


def currentframe() -> Optional[FrameType]:
    """Return the caller's frame, using a traceback if _getframe is absent."""
    if hasattr(sys, "_getframe"):
        return sys._getframe(1)

    try:
        raise RuntimeError("Locate the caller's frame")
    except RuntimeError as exc:
        # Raising and catching the exception here guarantees a traceback.
        traceback = typing.cast("TracebackType", exc.__traceback__)
        try:
            return traceback.tb_frame.f_back
        finally:
            del traceback


def warn_at_user_call(message: str, category: Type[Warning]) -> None:
    """Issue a warning at the first caller outside wakepy and contextlib.

    Frame selection is explicit: warnings.warn may skip filenames containing
    'importlib' and '_bootstrap', making its stacklevel differ from a raw
    frame count. Preserve the selected module's registry for warning filters.
    """
    frame = currentframe()
    try:
        while frame is not None and _is_internal_frame(frame):
            frame = frame.f_back
        if frame is None:
            warnings.warn_explicit(message, category, filename="<unknown>", lineno=0)
            return
        # Globals help retrieve source through import loaders (e.g. ZIPs).
        # Missing spec/loaders can raise ValueError during source lookup.
        # With -m, __main__ has a loader for the original module name;
        # affected CPython asks it for "__main__" and raises ImportError.
        # See https://github.com/python/cpython/issues/123011.
        # Omit globals in these cases: linecache can still read ordinary files
        # using filename. The module name and warning registry stay intact.
        module_globals = (
            frame.f_globals
            if getattr(frame.f_globals.get("__spec__"), "loader", None) is not None
            and frame.f_globals.get("__name__") != "__main__"
            else None
        )
        warnings.warn_explicit(
            message,
            category,
            filename=frame.f_code.co_filename,
            lineno=frame.f_lineno,
            module=frame.f_globals.get("__name__", "<string>"),
            registry=frame.f_globals.setdefault("__warningregistry__", {}),
            module_globals=module_globals,
        )
    finally:
        del frame


def _is_internal_frame(frame: FrameType) -> bool:
    """Skip wakepy package frames and the actual contextlib module.

    All wakepy modules are internal, including helpers introduced by future
    refactors. contextlib delegates entry to context managers; compare its
    globals by identity so application globals named 'contextlib' survive.
    """
    module_name = frame.f_globals.get("__name__")
    return (
        isinstance(module_name, str)
        and (module_name == "wakepy" or module_name.startswith("wakepy."))
    ) or frame.f_globals is vars(contextlib)
