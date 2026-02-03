import platform

import pytest

from wakepy import keep

if platform.system() != "Darwin":
    pytest.skip("These tests are only for macOS", allow_module_level=True)


class TestMacOS:
    """This test runs the actual 'caffeinate' command on macOS."""

    def test_caffeinate_keep_running(self):
        with keep.running() as m:
            assert m.active is True
            assert str(m.method) == "caffeinate"

    def test_caffeinate_keep_presenting(self):
        with keep.presenting() as m:
            assert m.active is True
            assert str(m.method) == "caffeinate"
