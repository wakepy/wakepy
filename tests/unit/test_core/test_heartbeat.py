import pytest

from wakepy import Method
from wakepy.core.heartbeat import Heartbeat


@pytest.fixture
def method0() -> Method:
    return Method()


class TestHeartBeat:
    def test_heartbeat(self, method0):
        hb = Heartbeat(method0)
        hb.start()
        hb.stop()
