from __future__ import annotations

import datetime as dt
import typing

if typing.TYPE_CHECKING:
    from typing import Optional

    from .method import Method


class Heartbeat:
    # This is just temporary dummy implementation.
    # Will be created as part of https://github.com/wakepy/wakepy/issues/109
    def __init__(
        self, method: Method, heartbeat_call_time: Optional[dt.datetime] = None
    ):
        self.method = method
        self.prev_call = heartbeat_call_time

    def start(self) -> bool:
        return True

    def stop(self) -> bool:
        return True
