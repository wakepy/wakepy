"""This module defines the CLI for wakepy

This is called either with

    python -m wakepy [args]

or using the executable

    wakepy [args]
"""

from __future__ import annotations

import argparse
import logging
import platform
import sys
import time
import typing
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from itertools import cycle
from textwrap import dedent, fill, wrap

if sys.version_info < (3, 8):  # pragma: no-cover-if-py-gte-38
    from typing_extensions import TypedDict
else:  # pragma: no-cover-if-py-lt-38
    from typing import TypedDict

from wakepy import ModeExit
from wakepy.core.activationresult import ActivationResult, ProbingResults
from wakepy.core.constants import IdentifiedPlatformType, ModeName
from wakepy.core.mode import Mode, create_mode_params
from wakepy.core.platform import CURRENT_PLATFORM, get_platform_debug_info, is_windows

if typing.TYPE_CHECKING:
    from argparse import Namespace

    from wakepy import ActivationResult


WAKEPY_LOGO = r"""                         _
                        | |
        __      __ __ _ | | __ ___  _ __   _   _
        \ \ /\ / // _` || |/ // _ \| '_ \ | | | |
         \ V  V /| (_| ||   <|  __/| |_) || |_| |
          \_/\_/  \__,_||_|\_\\___|| .__/  \__, |
         v.{version_string}| |      __/ |
                                   |_|     |___/ """


INFO_BOX = """
 ┏━━ Mode: {wakepy_mode} {header_bars}━┓
 ┃                                                      ┃
 ┃  [{no_auto_suspend}] Programs keep running                           ┃
 ┃  [{presentation_mode}] Display kept on, screenlock disabled            ┃
 ┃                                                      ┃
 ┃   Method: {wakepy_method} {method_spacing}┃
 ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛"""


WAKEPY_BANNER = WAKEPY_LOGO + INFO_BOX

# Display layout constants
MODE_NAME_MAX_LENGTH = 43
VERSION_STRING_WIDTH = 24
BELOW_BOX_TEXT_WIDTH = 66
GENERAL_TEXT_WIDTH = 80


def _create_help_formatter(prog: str) -> argparse.HelpFormatter:
    """Create help formatter with wider help position for better layout."""
    return argparse.HelpFormatter(prog, max_help_position=27)


def wait_for_interrupt(frames: Iterator[str], interval: float) -> None:
    """Display animated frames until keyboard interrupt.

    Args:
        frames: Iterator of frame strings to display
        interval: Seconds to wait between frames
    """
    try:
        for frame in frames:
            print(frame, end="")
            time.sleep(interval)
    except KeyboardInterrupt:
        pass


@dataclass(frozen=True)
class DisplayTheme:
    ascii_mode: bool
    spinner_symbols: tuple[str, ...]
    success_symbol: str
    failure_symbol: str = " "

    @property
    def spinner_line_width(self) -> int:
        return 32 if self.ascii_mode else 31

    @classmethod
    def create(cls, ascii_mode: bool | None = None) -> DisplayTheme:
        if ascii_mode is None:
            ascii_mode = get_should_use_ascii_only()

        if ascii_mode:
            return cls(
                ascii_mode=True,
                spinner_symbols=("|", "/", "-", "\\"),
                success_symbol="x",
            )
        else:
            return cls(
                ascii_mode=False,
                spinner_symbols=("⢎⡰", "⢎⡡", "⢎⡑", "⢎⠱", "⠎⡱", "⢊⡱", "⢌⡱", "⢆⡱"),
                success_symbol="✔",
            )


class SystemInfo(TypedDict):
    wakepy_version: str
    python_version: str
    platform_info: str


def main(argv: list[str] | None = None, app: CliApp | None = None) -> None:
    """Entry point for the wakepy CLI."""
    if argv is None:
        argv = sys.argv[1:]
    if app is None:
        app = CliApp()

    args = parse_args(argv)
    setup_logging(args.verbose, args.command)

    if args.command == "methods":
        app.run_wakepy_methods(args)
    else:
        app.run_wakepy(args)


def parse_args(args: list[str]) -> Namespace:
    parser = argparse.ArgumentParser(
        prog="wakepy",
        formatter_class=_create_help_formatter,
    )

    # Main wakepy command arguments (when no subcommand)
    _add_mode_arguments(parser)
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help=(
            "Increase verbosity level (-v for INFO, -vv for DEBUG). Default is "
            "WARNING, which shows only really important messages."
        ),
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add 'methods' subcommand
    methods_parser = subparsers.add_parser(
        "methods",
        help=(
            "List all available wakepy Methods for the selected mode in "
            "priority order"
        ),
        formatter_class=_create_help_formatter,
    )

    _add_mode_arguments(methods_parser)
    methods_parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help=(
            "Increase verbosity level (-v for detailed output, -vv for INFO logging, "
            "-vvv for DEBUG logging). Default shows only method names and status."
        ),
    )

    return parser.parse_args(args)


def get_mode_name(args: Namespace) -> ModeName:
    keep_running = args.keep_running or args.k
    keep_presenting = args.keep_presenting or args.presentation

    if keep_running and keep_presenting:
        raise ValueError(
            "Cannot use both --keep-running and --keep-presenting. " "See: wakepy -h"
        )

    if keep_presenting:
        return ModeName.KEEP_PRESENTING

    return ModeName.KEEP_RUNNING


def get_deprecations(args: Namespace) -> str:
    deprecations: list[str] = []

    if args.k:
        deprecations.append(
            "Using -k is deprecated in wakepy 0.10.0, and will be removed in a future "
            "release. Use -r/--keep-running, instead. "
            "Note that this is the default value so -r is optional.",
        )
    if args.presentation:
        deprecations.append(
            "Using --presentation is deprecated in wakepy 0.10.0, and will be removed "
            "in a future release. Use -p/--keep-presenting, instead. ",
        )
    return "\n".join(deprecations) if deprecations else ""


def setup_logging(verbosity: int, command: str) -> None:
    log_level = get_logging_level(verbosity, command)
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(levelname)s - %(message)s"
    )


def get_logging_level(verbosity: int, command: str | None = None) -> int:
    if command == "methods":
        if verbosity >= 3:  # Corresponds to -vvv or higher
            return logging.DEBUG
        elif verbosity == 2:  # Corresponds to -vv
            return logging.INFO
        else:
            return logging.WARNING
    else:
        if verbosity >= 2:  # Corresponds to -vv or higher
            return logging.DEBUG
        elif verbosity == 1:  # Corresponds to -v
            return logging.INFO
        else:  # No -v flags
            return logging.WARNING


def get_should_use_ascii_only(
    current_platform: IdentifiedPlatformType | None = None,
    python_impl: str | None = None,
) -> bool:
    if current_platform is None:
        current_platform = CURRENT_PLATFORM
    if python_impl is None:
        python_impl = platform.python_implementation()

    if is_windows(current_platform) and python_impl.lower() == "pypy":
        # Windows + PyPy combination does not support unicode well, at least
        # yet at version 7.3.17. See:
        # https://github.com/pypy/pypy/issues/3890
        # https://github.com/wakepy/wakepy/issues/274#issuecomment-2363293422
        return True
    return False


def get_wakepy_version() -> str:
    # Must be imported here to avoid circular imports
    from wakepy import __version__

    return __version__


class CliApp:
    def __init__(
        self,
        theme: DisplayTheme | None = None,
        system_info: SystemInfo | None = None,
        spinner_interval: float = 0.8,
    ) -> None:
        self.theme = theme or DisplayTheme.create()
        self.system_info = system_info or get_system_info()
        self.spinner_interval = spinner_interval

    def run_wakepy(self, args: Namespace) -> Mode:
        mode_name = get_mode_name(args)
        deprecations = get_deprecations(args)

        keepawake = Mode(
            create_mode_params(
                mode_name=mode_name,
                on_fail=self.handle_activation_error,
            )
        )

        with keepawake as mode:
            res = mode.result
            method_name = (
                mode.active_method.name if mode.active_method else "(no method)"
            )

            if res.success and args.verbose >= 1:
                txt = res.get_methods_text_detailed(max_width=80)
                if not txt.strip():
                    print("\nDid not try any methods!")
                else:
                    print(f"\nWakepy Methods (in the order of attempt):\n\n{txt}")

            print(render_logo(get_wakepy_version()))

            if res.success is False:
                print("\n" + res.get_failure_text(style="block"))

            if not mode.active:
                raise ModeExit

            print(
                render_info_box(
                    self.theme,
                    str(mode_name),
                    method_name,
                    is_presentation_mode=mode_name == ModeName.KEEP_PRESENTING,
                )
            )

            if deprecations:
                print(render_deprecations(deprecations))

            if not res.real_success:
                print(render_fake_success_warning())

            wait_for_interrupt(spinner_frames(self.theme), self.spinner_interval)
            print("\n", end="")

        if mode.result.success:
            # If activation did not succeed, there is also no deactivation /
            # exit.
            print("\nExited.")
        return mode

    def run_wakepy_methods(
        self,
        args: Namespace,
        probe_runner: Callable[[ModeName], ProbingResults] | None = None,
    ) -> None:
        mode_name = get_mode_name(args)
        if probe_runner is None:
            params = create_mode_params(mode_name=mode_name)
            result = Mode(params).probe_all_methods()
        else:
            result = probe_runner(mode_name)
        output = render_methods_output(mode_name, result, verbose=args.verbose >= 1)
        print(output)

    def handle_activation_error(
        self,
        result: ActivationResult,
    ) -> None:
        print(render_activation_error(result, system_info=self.system_info))


def get_system_info() -> SystemInfo:
    return {
        "wakepy_version": get_wakepy_version(),
        "python_version": sys.version,
        "platform_info": get_platform_debug_info().strip(),
    }


def spinner_frames(theme: DisplayTheme) -> Iterator[str]:
    padding = " " * theme.spinner_line_width
    suffix = " [Press Ctrl+C to exit] "

    for symbol in cycle(theme.spinner_symbols):  # pragma: no branch
        yield f"\r {symbol}{padding}{suffix}"


def render_logo(wakepy_version: str) -> str:
    version = wakepy_version[:VERSION_STRING_WIDTH]
    version_string = f"{version: <{VERSION_STRING_WIDTH}}"
    return WAKEPY_LOGO.strip("\n").format(version_string=version_string)


def render_info_box(
    theme: DisplayTheme,
    mode_name: str,
    method_name: str,
    *,
    is_presentation_mode: bool,
) -> str:
    mode_name = mode_name[:MODE_NAME_MAX_LENGTH]
    method_name_max_length = MODE_NAME_MAX_LENGTH - 1
    method_name = method_name[:method_name_max_length]

    header_bars = "━" * (MODE_NAME_MAX_LENGTH - len(mode_name))
    method_spacing = " " * (method_name_max_length - len(method_name))

    presentation_symbol = (
        theme.success_symbol if is_presentation_mode else theme.failure_symbol
    )

    return INFO_BOX.strip("\n").format(
        wakepy_mode=mode_name,
        header_bars=header_bars,
        no_auto_suspend=theme.success_symbol,
        presentation_mode=presentation_symbol,
        wakepy_method=method_name,
        method_spacing=method_spacing,
    )


def render_deprecations(deprecations: str) -> str:
    text = "\n".join(
        wrap(
            f"DEPRECATION NOTICE: {deprecations}",
            BELOW_BOX_TEXT_WIDTH,
            break_long_words=True,
            break_on_hyphens=True,
        )
    )
    return f"\n\n{text}\n"


def render_fake_success_warning() -> str:
    warning = (
        "WARNING: You are using the WAKEPY_FAKE_SUCCESS. "
        "Wakepy is not active. See: "
        "https://wakepy.readthedocs.io/stable/tests-and-ci.html#"
        "wakepy-fake-success"
    )
    text = "\n".join(
        wrap(
            warning,
            BELOW_BOX_TEXT_WIDTH,
            break_long_words=True,
            break_on_hyphens=True,
        )
    )
    return f"\n{text}\n"


def render_error_message(error_text: str) -> str:
    blocks = dedent(error_text.strip("\n")).split("\n")
    return "\n".join(fill(block, GENERAL_TEXT_WIDTH) for block in blocks)


def render_activation_error(
    result: ActivationResult,
    system_info: SystemInfo | None = None,
) -> str:
    if system_info is None:
        system_info = get_system_info()
    error_text = f"""
Wakepy could not activate the "{result.mode_name}" mode. This might occur because of a bug or because your current platform is not yet supported or your system is missing required software.

Check if there is already a related issue in the issue tracker at https://github.com/wakepy/wakepy/issues/ and if not, please create a new one.

Include the following:
- wakepy version: {system_info["wakepy_version"]}
- Mode: {result.mode_name}
- Python version: {system_info["python_version"]}
{system_info["platform_info"]}
- Additional details: [FILL OR REMOVE THIS LINE]

Thank you!
"""  # noqa: E501

    return render_error_message(error_text)


def render_methods_output(
    mode_name: str,
    result: ProbingResults,
    *,
    verbose: bool,
) -> str:
    width = GENERAL_TEXT_WIDTH if verbose else 55
    separator = "━" * width
    header = mode_name.center(width).rstrip()

    if verbose:
        methods_text = result.get_methods_text_detailed(max_width=width)
        content = f"\n{methods_text}\n"
    else:
        content = result.get_methods_text(
            index_width=3, name_width=width - 17, status_width=10
        )

    return f"{separator}\n{header}\n{separator}\n{content}\n{separator}\n"


def _add_mode_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-r",
        "--keep-running",
        help=(
            "Keep programs running (DEFAULT); inhibit automatic idle timer based sleep "
            "/ suspend. If a screen lock (or a screen saver) with a password is "
            "enabled, your system *may* still lock the session automatically. You may, "
            "and probably should, lock the session manually. Locking the workstation "
            "does not stop programs from executing."
        ),
        action="store_true",
        default=False,
    )

    # old name for -r, --keep-running. Used during deprecation time
    parser.add_argument(
        "-k",
        help=argparse.SUPPRESS,
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "-p",
        "--keep-presenting",
        help=(
            "Presentation mode; inhibit automatic idle timer based sleep, screensaver, "
            "screenlock and display power management."
        ),
        action="store_true",
        default=False,
    )

    # old name for -p, --keep-presenting. Used during deprecation time
    parser.add_argument(
        "--presentation",
        help=argparse.SUPPRESS,
        action="store_true",
        default=False,
    )


if __name__ == "__main__":
    # Entry point when running 'python -m wakepy'.
    main()  # pragma: no cover
