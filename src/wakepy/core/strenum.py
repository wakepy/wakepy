"""This module defines StrEnum for making string enumerations.

NOTE: The enum.StrEnum could be used in place of StrEnum on Python 3.11
onwards, so consider removing this module when python 3.10 is no longer
supported."""

from __future__ import annotations

import typing
from enum import Enum, EnumMeta, auto

if typing.TYPE_CHECKING:
    from enum import _EnumDict
    from typing import Any, Callable, Dict, KeysView, Tuple, Type, ValuesView


class StrEnumMeta(EnumMeta):
    """This metaclass is an extension of the basic Enum metaclass, and provides
    the following

    1) Containment check for enumeration member values; `val in SomeClass`
    2) `unique` parameter when creating constants.
    """

    # The __prepare__ function signature has some problems in mypy 1.9.0
    # CPython 3.10.12. It says that `Signature of "__prepare__" incompatible
    # with supertype X` where X is "EnumMeta" or "type". Could not find a
    # function signature which would be okay with both the EnumMeta and type
    # superclasses so just ignoring the error.
    @classmethod
    def __prepare__(  # type: ignore[override]
        metacls: Type[StrEnumMeta],
        clsname: str,
        bases: Tuple[type, ...],
        **_: Any,
    ) -> _EnumDict:
        # This is needed since we have to allow passing kwargs to __init__
        # Needed on 3.7.x, not needed on 3.10. (not tested 3.8 & 3.9)
        return super().__prepare__(clsname, bases)

    def __new__(
        metacls: Type[StrEnumMeta],
        clsname: str,
        bases: Tuple[Type[object], ...],
        classdict: _EnumDict,
        **_: Dict[str, object],
    ) -> StrEnumMeta:
        # This is needed since we have to allow passing kwargs to __init__

        return super().__new__(metacls, clsname, bases, classdict)

    def __init__(cls, *_: Tuple[object, ...], unique: bool = False) -> None:
        if unique:
            cls._check_uniqueness()

    def _check_uniqueness(cls) -> None:
        vals: ValuesView[Enum] = cls.__members__.values()
        if len(vals) > len(set(vals)):
            raise ValueError("The values must be unique!")

    def __contains__(cls, value: Any) -> bool:
        """Provides the `val in SomeConstClass` containment check

        Parameters
        ----------
        cls:
            This will be the (subclass) of the class using StrEnumMeta.
            If you use class Const(metaclass=StrEnumMeta): ... and
            SomeConst(Const), cls will be SomeConst; a class.
        value:
            The `val` in the example
        """
        return value in cls.values()

    @property
    def keys(cls) -> Callable[[], KeysView[str]]:
        return cls.__members__.keys

    @property
    def values(cls) -> Callable[[], ValuesView[str]]:
        return cls.__members__.values


class StrEnum(str, Enum, metaclass=StrEnumMeta):
    """A string constant / enumeration. For creating reusable, typed constants.

    Properties
    -----------

    1) All enumeration members are (subtype of) strings; they can be used
    directly as strings, without the need for the typical member.value type
    of accessing pattern.

    2) All enumeration members can have automatic name:

    >>> from enum import auto
    >>>
    >>> class MyConst(StrEnum):
    ...     BAR = auto()

    >>> MyConst.BAR == "BAR"
    True

    3) Possibility to make values unique; for example

    >>> class MyConst(StrEnum, unique=True):
    ...     FIRST = 'foo'
    ...     SECOND = 'foo'

        ValueError: The values must be unique!


    4) Testing for containment looks for *values*; for example

    >>> class MyConst(StrEnum):
    ...     FOO = 'bar'

    >>> 'bar' in MyConst
    True

    """

    @staticmethod
    def _generate_next_value_(
        name: str, start: int, count: int, last_values: list[Any]
    ) -> str:
        """Turn auto() value to be a string corresponding to the enumeration
        member name

        Ref: https://docs.python.org/3/library/enum.html#enum.Enum._generate_next_value_
        """
        return name

    def __str__(self) -> str:
        return str.__str__(self)

    def __hash__(self) -> int:
        return super().__hash__()

    def __eq__(self, other: object) -> bool:
        # This was added just to make mypy happy. Without this mypy will
        # assume SomeConst.FOO == 'somestr' always to be False.
        # In reality, the EnumMemberString.__eq__ is called in this case.
        return str(self) == other  # pragma: no cover

    @property
    def name(self) -> str:
        return self._name_


__all__ = [
    "StrEnum",
    "auto",
]
