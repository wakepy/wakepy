"""Tests for wakepy.core.utils module."""

from __future__ import annotations

import pytest

from wakepy.core.utils import is_env_var_truthy

# These are the only "falsy" values for environment variables
FALSY_ENV_VAR_TEST_VALUES = (
    "0",
    "no",
    "NO",
    "N",
    "n",
    "False",
    "false",
    "FALSE",
    "F",
    "f",
    "",
)
TRUTHY_ENV_VAR_TEST_VALUES = ("1", "yes", "True", "anystring")


class TestIsEnvVarTruthy:
    @pytest.mark.parametrize("val", FALSY_ENV_VAR_TEST_VALUES)
    def test_falsy_values(self, val, monkeypatch):
        monkeypatch.setenv("TEST_VAR", val)
        assert is_env_var_truthy("TEST_VAR") is False

    @pytest.mark.parametrize("val", TRUTHY_ENV_VAR_TEST_VALUES)
    def test_truthy_values(self, val, monkeypatch):
        monkeypatch.setenv("TEST_VAR", val)
        assert is_env_var_truthy("TEST_VAR") is True

    def test_unset_variable(self, monkeypatch):
        monkeypatch.delenv("TEST_VAR", raising=False)
        assert is_env_var_truthy("TEST_VAR") is False
