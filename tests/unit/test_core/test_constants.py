from wakepy.core import BusType, ModeName
from wakepy.core.constants import (
    BusTypeValue,
    IdentifiedPlatformType,
    ModeNameValue,
    PlatformType,
)


def test_mode_name(assert_strenum_values):
    assert_strenum_values(ModeName, ModeNameValue)


def test_bustype(assert_strenum_values):
    assert_strenum_values(BusType, BusTypeValue)


def test_platform_types_in_sync():
    """Test that each IdentifiedPlatformType is also in PlatformType: anything
    that can be detected can also be selected by the Method subclasses in
    supported_platforms."""

    identified = {member.value for member in IdentifiedPlatformType}
    selectable = {member.value for member in PlatformType}
    assert not (identified - selectable)
