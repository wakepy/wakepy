"""Defines following commands which use Invoke[1].

invoke format
* Format the files automatically

invoke check
* Check the formatting, type hints, etc.

invoke docs
* Start sphinx build for documentation

invoke test
* Runs tests and coverage for the source tree (does not test docs build)

In addition to these uv is an important command.

uv build
* Builds the sdist and wheel into dist/

[1] https://docs.pyinvoke.org/
"""

from __future__ import annotations

import os
import typing
from pathlib import Path

from colorama import Fore
from invoke import task  # type: ignore

from wakepy.core import CURRENT_PLATFORM
from wakepy.core.platform import is_unix_like_foss

if typing.TYPE_CHECKING:
    from invoke.runners import Result


def get_run_with_print(c):
    def run_with_print(cmd: str, ignore_errors: bool = False) -> Result:
        print("Running:", Fore.YELLOW, cmd, Fore.RESET)

        unix_like = is_unix_like_foss(CURRENT_PLATFORM)
        res: Result = c.run(
            cmd,
            pty=unix_like,
            warn=ignore_errors,
            shell=get_shell() if unix_like else None,
        )
        return res

    return run_with_print


@task
def format(c) -> None:
    run = get_run_with_print(c)
    run("python -m isort .")
    run("python -m black .")
    run("python -m ruff check --fix .")


@task
def check(c) -> None:
    run = get_run_with_print(c)
    run("python -m isort --check .")
    run("python -m black --check .")
    run("python -m ruff check --no-fix .")
    run("python -m mypy .")


@task
def docs(c) -> None:
    """Starts sphinx build with live-reload on browser."""
    if not is_unix_like_foss(CURRENT_PLATFORM):
        print(
            "WARNING: Note that full docs are built only on Linux / BSD (most of the "
            "docs are fine)"
        )

    run = get_run_with_print(c)
    # The `-a` flag ensures that *all* files (not only edited files) will get
    # rebuild. You may also build just once with
    #   sphinx-build -b html docs/source/ docs/build
    run("sphinx-autobuild docs/source/ docs/build/ -a")


@task
def test(c, pdb: bool = False) -> None:
    run = get_run_with_print(c)
    pdb_flag = " --pdb " if pdb else ""
    res = run(
        f"env -u DBUS_SESSION_BUS_ADDRESS python -m pytest -W error {pdb_flag}"
        "--cov-branch --cov ./src --cov-fail-under=100",
        ignore_errors=True,
    )
    if res.exited:
        run(f"coverage html && python -m webbrowser -t htmlcov{os.sep}index.html")

    check(c)


def get_shell():
    bash = "/bin/bash"
    usr_bash = "/usr/local/bin/bash"
    if Path(bash).exists():
        return bash
    elif Path(usr_bash).exists():
        return usr_bash
    raise RuntimeError("Could not find a shell to be be used with invoke!")
