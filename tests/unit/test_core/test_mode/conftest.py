from __future__ import annotations

from typing import Callable

import pytest

from wakepy import Method, Mode
from wakepy.core import PlatformType
from wakepy.core.mode import create_mode_params


@pytest.fixture
def hook_modes() -> list[Mode]:
    """Actual instances invoking entry hooks, including decorator clones."""
    return []


@pytest.fixture
def lifecycle_case(
    empty_method_registry: None,
    monkeypatch: pytest.MonkeyPatch,
    hook_modes: list[Mode],
) -> Callable[[dict[str, BaseException], bool], tuple[Mode, list[str]]]:
    """Real mode/method and recording hooks, with injectable failures."""
    monkeypatch.delenv("WAKEPY_FAKE_SUCCESS", raising=False)
    case_count = 0

    def make_case(
        errors: dict[str, BaseException], success: bool
    ) -> tuple[Mode, list[str]]:
        nonlocal case_count
        case_count += 1
        events: list[str] = []

        def record(name: str) -> None:
            events.append(name)
            if name in errors:
                raise errors[name]

        def hook(name: str) -> Callable[[object], None]:
            def callback(arg: object) -> None:
                if name == "before_enter" and isinstance(arg, Mode):
                    hook_modes.append(arg)
                record(name)

            return callback

        class RecordingMethod(Method):
            name = f"LifecycleRecording{case_count}"
            mode_name = "lifecycle-recording"
            supported_platforms = (PlatformType.ANY,)

            def caniuse(self) -> bool:
                return success

            def enter_mode(self) -> None:
                record("activate")

            def exit_mode(self) -> None:
                record("deactivate")

        mode = Mode(
            create_mode_params(
                RecordingMethod.mode_name,
                methods=[RecordingMethod.name],
                before_enter=hook("before_enter"),
                on_success=hook("on_success"),
                on_fail=hook("on_fail"),
                after_enter=hook("after_enter"),
                before_exit=hook("before_exit"),
                after_exit=hook("after_exit"),
            )
        )
        return mode, events

    return make_case
