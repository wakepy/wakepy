"""This module contains registry of wakepy.Methods. All the subclasses of
wakepy.Method are automatically added to this registry. The registry can be
accessed with the functions listed below.

Functions for getting Methods
-----------------------------
get_method
    Get a single method by name
get_methods
    Get multiple methods by name
get_methods_for_mode
    Get Methods based on a Mode name
"""

from __future__ import annotations

import logging
import typing
from typing import overload

from .constants import ModeName, ModeNameValue

if typing.TYPE_CHECKING:
    from typing import Dict, List, Optional, Set, Tuple, Type, TypeVar, Union, overload

    from wakepy.core.method import Method, MethodCls

    T = TypeVar("T")

    Collection = Union[List[T], Tuple[T, ...], Set[T]]
    MethodDict = Dict[str, MethodCls]
    MethodRegistry = Dict[str, MethodDict]


_method_registry: MethodRegistry = dict()
"""A registry of Methods and Modes. This is used for searching a Method base on
the name of the Method and optionally the name of the Mode the Method
implements.

Updated automatically; when python loads a module with a subclass of Method,
the Method class is added to this registry.

Data structure: The keys are names of Modes and values are MethodDicts. In
MethodDict, keys are names of methods, and values are Method classes.
"""

logger = logging.getLogger(__name__)


class MethodRegistryError(RuntimeError):
    """Any error which is related to the method registry"""


def register_method(method_class: Type[Method]) -> None:
    """Registers a subclass of Method to the method registry"""

    if method_class.is_unnamed():
        # Methods without a name will not be registered
        logger.debug(
            "Not registering Method %s as it does not have a name set.", method_class
        )
        return

    logger.debug("Registering Method %s (name: %s)", method_class, method_class.name)

    method_dict: MethodDict = _method_registry.get(method_class.mode_name, dict())

    if method_class.name in method_dict:
        if method_dict[method_class.name] is not method_class:
            # The same class registered with different name -> raise Exception
            raise MethodRegistryError(
                f'Duplicate Method name "{method_class.name}": '
                f"{method_class.__qualname__} "
                "(already registered to "
                f"{method_dict[method_class.name].__qualname__})"
            )
        else:
            # The same class registered with same name. No action required.
            return

    # Register a new method class
    method_dict[method_class.name] = method_class
    _method_registry.setdefault(method_class.mode_name, method_dict)


def get_method(
    method_name: str, mode_name: Optional[ModeNameValue | str] = None
) -> MethodCls:
    """Get a Method class based on its name and optionally the mode.

    Parameters
    ----------
    method_name: str
        The name of the wakepy.Method. The method must be registered which
        means that the module containing the subclass definition must have
        been imported.
    mode_name: str | None
        If the method_name is registered to methods belonging to multiple
        Modes, you must provide the mode name, to make the selection
        unambiguous. Typical mode names are "keep.running" and
        "keep.presenting".

    Raises
    ------
    ValueError
        Raised if the method does not exist, or if the method exists in
        multiple modes, but the mode was not provided as argument to make the
        selection unambiguous.

    """

    notfound = ValueError(
        f'No Method with name "{method_name}" found!'
        " Check that the name is correctly spelled and that the module containing"
        " the class is being imported."
    )

    if mode_name is not None:
        method_dict = _method_registry.get(mode_name, dict())
        if method_name not in method_dict:
            raise notfound
        return method_dict[method_name]

    # mode is None -> search from all modes.
    methods_from_all_modes = []
    for method_dict in _method_registry.values():
        if method_name not in method_dict:
            continue
        methods_from_all_modes.append(method_dict[method_name])

    if not methods_from_all_modes:
        raise notfound
    elif len(methods_from_all_modes) > 1:
        n = len(methods_from_all_modes)
        modes = tuple(m.mode_name for m in methods_from_all_modes)
        raise ValueError(
            f'Multiple ({n}) Methods with name "{method_name}" found! '
            f"The selection is unambiguous. Found modes: {modes}"
        )

    return methods_from_all_modes[0]


@overload
def get_methods(
    names: List[str], mode_name: Optional[ModeName] = None
) -> List[MethodCls]: ...
@overload
def get_methods(
    names: Tuple[str, ...], mode_name: Optional[ModeName] = None
) -> Tuple[MethodCls, ...]: ...
@overload
def get_methods(
    names: Set[str], mode_name: Optional[ModeName] = None
) -> Set[MethodCls]: ...


def get_methods(
    names: Collection[str], mode_name: Optional[ModeName] = None
) -> Collection[MethodCls]:
    """Get a collection (list, tuple or set) of Method classes based on their
    names, and optionally the mode name.

    Parameters
    ----------
    names: list, tuple or set of str
        The names of the wakepy.Methods to get. The methods must be registered
        which means that the modules containing the subclass definitions must
        have been imported.
    mode_name: str | None
        If a string, only gets methods for the given mode. If None, searches
        the methods from all the modes. In this case, each Method must be found
        only in one mode. Otherwise raises ValueError.

    Raises
    ------
    ValueError
        Raised if any of the methods does not exist, or if any of the existing
        methods exists in multiple modes and the mode name (str) was not
        provided as argument to make the selection unambiguous.
    """

    if isinstance(names, list):
        return [get_method(name, mode_name) for name in names]
    elif isinstance(names, tuple):
        return tuple(get_method(name, mode_name) for name in names)
    elif isinstance(names, set):
        return set(get_method(name, mode_name) for name in names)
    else:
        raise TypeError("`names` must be a list, tuple or set")


def get_methods_for_mode(
    mode_name: ModeName | str,
) -> List[MethodCls]:
    """Get the Method classes belonging to a Mode; Methods with
    Method.mode_name = `mode_name`.

    Parameters
    ----------
    mode: str | ModeName
        The name of the Mode from which to select the Methods.

    Returns
    -------
    methods: list[MethodCls]
        The Method classes for the Mode.
    """
    return [m for m in _method_registry.get(mode_name, dict()).values()]
