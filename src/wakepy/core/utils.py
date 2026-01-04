"""Utility functions for wakepy core."""

from __future__ import annotations

import logging
import os

from .constants import FALSY_ENV_VAR_VALUES

logger = logging.getLogger(__name__)


def is_env_var_truthy(env_var_name: str) -> bool:
    """Check if an environment variable is set to a truthy value.

    Parameters
    ----------
    env_var_name:
        The name of the environment variable to check.

    Returns
    -------
    is_truthy:
        True if the environment variable is set to a truthy value, False if
        it's unset or set to a falsy value ('0', 'no', 'false', 'f', 'n', '').
        The check is case-insensitive.

    Notes
    -----
    This function is used to check environment variables like
    WAKEPY_FAKE_SUCCESS and WAKEPY_FORCE_FAILURE.
    """
    env_var_value = os.environ.get(env_var_name)

    if env_var_value is None:
        logger.debug("'%s' is not set.", env_var_name)
        return False

    if env_var_value.lower() in FALSY_ENV_VAR_VALUES:
        logger.debug("'%s' has a falsy value: %s.", env_var_name, env_var_value)
        return False

    logger.debug("'%s' has a truthy value: %s.", env_var_name, env_var_value)
    return True
