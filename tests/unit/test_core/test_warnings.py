"""Caller lookup, fallback behavior, and warning filter semantics."""

from __future__ import annotations

import sys
import warnings
from types import FrameType
from typing import Optional

import pytest

from wakepy.core import _warnings
from wakepy.core._warnings import currentframe, warn_at_user_call


class TestCurrentFrame:
    @pytest.mark.parametrize("use_fallback", [False, True])
    def test_returns_caller(
        self, monkeypatch: pytest.MonkeyPatch, use_fallback: bool
    ) -> None:
        with monkeypatch.context() as patch:
            if use_fallback:
                patch.delattr(sys, "_getframe")
            frame = currentframe()
        try:
            assert frame is not None
            assert frame.f_code is self.test_returns_caller.__code__
        finally:
            del frame


class TestWarningEmission:
    @pytest.fixture
    def without_frame(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def no_frame() -> Optional[FrameType]:
            return None

        monkeypatch.setattr(_warnings, "currentframe", no_frame)

    @pytest.mark.usefixtures("without_frame")
    def test_missing_frame_still_warns(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            warn_at_user_call("frame unavailable", UserWarning)
        assert len(caught) == 1
        assert (caught[0].filename, caught[0].lineno) == ("<unknown>", 0)

    @pytest.mark.parametrize(
        "action, count", [("default", 1), ("always", 2), ("ignore", 0)]
    )
    def test_repeat_filter(self, action: str, count: int) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter(action)
            for _ in range(2):
                warn_at_user_call("repeat filter", UserWarning)
        assert len(caught) == count

    def test_filter_error(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            with pytest.raises(UserWarning, match="filter error"):
                warn_at_user_call("filter error", UserWarning)

    def test_module_filter_uses_application_name(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            warnings.filterwarnings("ignore", module=__name__.replace(".", r"\.") + "$")
            warn_at_user_call("module filter", UserWarning)
        assert caught == []

    def test_missing_module_name(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            exec(  # noqa: S102 - Exercise an application namespace without __name__.
                "warn('unnamed namespace', UserWarning)", {"warn": warn_at_user_call}
            )
        assert len(caught) == 1
        assert caught[0].filename == "<string>"

    def test_releases_frame_if_warning_raises(self) -> None:
        """Error filters must not retain the selected frame in locals."""
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            with pytest.raises(UserWarning, match="release frame") as raised:
                warn_at_user_call("release frame", UserWarning)
        traceback = raised.value.__traceback__
        assert traceback is not None
        traceback = traceback.tb_next
        assert traceback is not None
        assert traceback.tb_frame.f_code is warn_at_user_call.__code__
        assert "frame" not in traceback.tb_frame.f_locals


class TestInternalFrameSelection:
    def test_package_root(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            exec(  # noqa: S102 - Simulate a helper in the package root.
                "warn('root helper', UserWarning)",
                {"__name__": "wakepy", "warn": warn_at_user_call},
            )
        assert len(caught) == 1
        assert caught[0].filename == __file__
