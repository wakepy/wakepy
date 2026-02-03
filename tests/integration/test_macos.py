import platform

import pytest

from wakepy import keep

if platform.system() != "Darwin":
    pytest.skip("These tests are only for macOS", allow_module_level=True)


class TestMacOS:
    def test_caffeinate_runs(self):
        # Test that the caffeinate command can be run without errors
        with keep.running() as m:
            assert m.active is True
            assert str(m.method) == "caffeinate"

    def test_caffeinate_presents(self):
        # Test that the caffeinate command can be run without errors
        with keep.presenting() as m:
            assert m.active is True
            assert str(m.method) == "caffeinate"
