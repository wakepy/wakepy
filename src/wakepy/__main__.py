"""This module defines the CLI for wakepy

This is called either with

    python -m wakepy [args]

or using the executable

    wakepy [args]
"""

from __future__ import annotations

import argparse
import itertools
import logging
import platform
import sys
import textwrap
import time
import typing
from dataclasses import dataclass
from textwrap import dedent, fill, wrap

from wakepy import ModeExit
from wakepy.core.constants import IdentifiedPlatformType, ModeName
from wakepy.core.mode import Mode, create_mode_params
from wakepy.core.platform import CURRENT_PLATFORM, get_platform_debug_info, is_windows

if typing.TYPE_CHECKING:
    from argparse import Namespace
    from collections.abc import Iterator

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


@dataclass(frozen=True)
class DisplayTheme:
    """Visual theme configuration based on terminal capabilities.

    This is immutable configuration that determines HOW things are displayed
    (symbols, widths, formatting constraints).
    """

    # Character encoding mode
    ascii_mode: bool

    # Spinner animation
    spinner_symbols: tuple[str, ...]
    spinner_line_width: int

    # Status indicators
    success_symbol: str
    failure_symbol: str = " "

    # Layout constraints for info box
    mode_name_max_length: int = 43
    version_string_width: int = 24

    @property
    def method_name_max_length(self) -> int:
        """Method name max length is always mode_name_max_length - 1."""
        return self.mode_name_max_length - 1

    # Text wrapping widths
    text_max_width: int = 66
    error_text_width: int = 80

    @classmethod
    def create(cls, ascii_mode: bool | None = None) -> DisplayTheme:
        """Create theme based on platform capabilities.

        Parameters
        ----------
        ascii_mode : bool | None
            If True, use ASCII-only symbols. If False, use Unicode symbols.
            If None (default), auto-detect based on platform capabilities.

        Returns
        -------
        DisplayTheme
            Theme configured for the current terminal capabilities

        """
        if ascii_mode is None:
            ascii_mode = get_should_use_ascii_only()

        if ascii_mode:
            return cls(
                ascii_mode=True,
                spinner_symbols=("|", "/", "-", "\\"),
                spinner_line_width=32,
                success_symbol="x",
            )
        else:
            return cls(
                ascii_mode=False,
                spinner_symbols=("⢎⡰", "⢎⡡", "⢎⡑", "⢎⠱", "⠎⡱", "⢊⡱", "⢌⡱", "⢆⡱"),
                spinner_line_width=31,
                success_symbol="✔",
            )


@dataclass
class SessionData:
    """Runtime data about the current wakepy session.

    This is mutable data that represents WHAT is being displayed - the actual
    values from the running mode, version information, and any warnings.

    Parameters
    ----------
    version : str
        Wakepy version string
    mode_name : str
        Name of the wakepy Mode
    method_name : str
        Name of the active method
    deprecations : str
        Deprecation warnings (default: empty string)
    is_fake_success : bool
        Whether this is a fake success (default: False)

    """

    wakepy_version: str
    mode_name: str
    method_name: str
    deprecations: str = ""
    is_fake_success: bool = False  # noqa: FBT003

    @property
    def is_presentation_mode(self) -> bool:
        return self.mode_name == ModeName.KEEP_PRESENTING

    @classmethod
    def from_mode(cls, mode: Mode, deprecations: str) -> SessionData:
        """Create SessionData from an active Mode.

        Parameters
        ----------
        mode : Mode
            The active Mode instance
        deprecations : str
            Deprecation warnings to display

        Returns
        -------
        SessionData
            Session data ready for rendering

        """
        mode_name = mode.name or "(unknown mode)"
        method_name = mode.active_method.name if mode.active_method else "(no method)"
        is_fake_success = not mode.result.real_success

        return cls(
            wakepy_version=get_wakepy_version(),
            mode_name=mode_name,
            method_name=method_name,
            deprecations=deprecations,
            is_fake_success=is_fake_success,
        )


class CLIRenderer:
    """Renders all CLI output including banners, errors, and messages.

    This is the presentation layer that knows how to format SessionData
    using a DisplayTheme. It handles all the visual formatting, truncation,
    and layout calculations. This is the single source of truth for converting
    data objects to formatted strings for CLI display.
    """

    # External documentation URLs
    FAKE_SUCCESS_URL = (
        "https://wakepy.readthedocs.io/stable/tests-and-ci.html#wakepy-fake-success"
    )
    GITHUB_ISSUES_URL = "https://github.com/wakepy/wakepy/issues/"

    def __init__(self, theme: DisplayTheme, spinner_interval: float = 0.8):
        """Initialize renderer with a display theme.

        Parameters
        ----------
        theme : DisplayTheme
            The theme to use for rendering
        spinner_interval : float
            Animation interval for spinner in seconds (default: 0.8)

        """
        self.theme = theme
        self.spinner_interval = spinner_interval

    def render_info_banner(self, data: SessionData) -> str:
        """Render the main info banner with logo.

        Parameters
        ----------
        data : SessionData
            The session data to display

        Returns
        -------
        str
            Formatted banner text ready for printing

        """
        banner = self.render_main_info(data)
        banner += self.render_deprecations(data)
        banner += self.render_fake_success_warning(data)
        return banner

    def spinner_frames(self) -> Iterator[str]:
        """Generate spinner animation frames.

        Yields
        ------
        str
            Formatted spinner frame ready for printing

        """
        for symbol in itertools.cycle(self.theme.spinner_symbols):  # pragma: no branch
            yield (
                f"\r {symbol}{' ' * self.theme.spinner_line_width}"
                "[Press Ctrl+C to exit] "
            )

    def render_main_info(self, data: SessionData) -> str:
        """Render the main info box with mode and method information.

        Parameters
        ----------
        data : SessionData
            The session data to display

        Returns
        -------
        str
            Formatted info box

        """
        # Truncate to fit layout constraints
        mode_name = data.mode_name[: self.theme.mode_name_max_length]
        method_name = data.method_name[: self.theme.method_name_max_length]
        version = data.wakepy_version[: self.theme.version_string_width]

        header_bars = "━" * (self.theme.mode_name_max_length - len(mode_name))
        method_spacing = " " * (self.theme.method_name_max_length - len(method_name))
        version_string = f"{version: <{self.theme.version_string_width}}"

        presentation_symbol = (
            self.theme.success_symbol
            if data.is_presentation_mode
            else self.theme.failure_symbol
        )

        return WAKEPY_BANNER.strip("\n").format(
            version_string=version_string,
            wakepy_mode=mode_name,
            header_bars=header_bars,
            no_auto_suspend=self.theme.success_symbol,
            presentation_mode=presentation_symbol,
            wakepy_method=method_name,
            method_spacing=method_spacing,
        )

    def render_deprecations(self, data: SessionData) -> str:
        """Render deprecation warnings if present.

        Parameters
        ----------
        data : SessionData
            The session data to check for deprecations

        Returns
        -------
        str
            Formatted deprecation warnings or empty string

        """
        if not data.deprecations:
            return ""

        text = self.wrap_text(f"DEPRECATION NOTICE: {data.deprecations}")
        return f"\n\n{text}\n"

    def render_fake_success_warning(self, data: SessionData) -> str:
        if not data.is_fake_success:
            return ""

        warning = (
            f"WARNING: You are using the WAKEPY_FAKE_SUCCESS. "
            f"Wakepy is not active. See: {self.FAKE_SUCCESS_URL}"
        )
        text = self.wrap_text(warning)
        return f"\n{text}\n"

    def wrap_text(self, text: str) -> str:
        return "\n".join(
            wrap(
                text,
                self.theme.text_max_width,
                break_long_words=True,
                break_on_hyphens=True,
            )
        )

    def render_activation_error(self, result: ActivationResult) -> str:
        error_text = f"""
        Wakepy could not activate the "{result.mode_name}" mode. This might occur because of a bug or because your current platform is not yet supported or your system is missing required software.

        Check if there is already a related issue in the issue tracker at {self.GITHUB_ISSUES_URL} and if not, please create a new one.

        Include the following:
        - wakepy version: {get_wakepy_version()}
        - Mode: {result.mode_name}
        - Python version: {sys.version}
        {textwrap.indent(get_platform_debug_info().strip(), ' '*4).strip()}
        - Additional details: [FILL OR REMOVE THIS LINE]

        Thank you!
        """  # noqa 501

        return self.render_error_message(error_text)

    def render_error_message(self, error_text: str) -> str:
        """Format error text into wrapped blocks.

        Parameters
        ----------
        error_text : str
            Raw error text to format

        Returns
        -------
        str
            Formatted error text with proper line wrapping

        """
        blocks = dedent(error_text.strip("\n")).split("\n")
        return "\n".join(fill(block, self.theme.error_text_width) for block in blocks)


class CliApp:
    """The wakepy CLI Application."""

    def __init__(self) -> None:
        theme = DisplayTheme.create()
        self.renderer = CLIRenderer(theme)

    def run(self, sysargs: list[str]) -> Mode:
        """Run the wakepy CLI with the given command line arguments.

        Parameters
        ----------
        sysargs : list[str]
            The command line arguments to parse and use. You should pass
            sys.argv[1:] as the sysargs.

        Returns
        -------
        Mode
            The Mode instance that was run

        """
        args = parse_args(sysargs)

        setup_logging(args.verbose)

        mode_name = get_mode_name(args)
        deprecations = get_deprecations(args)

        params = create_mode_params(
            mode_name=mode_name,
            on_fail=self.handle_activation_error,
        )
        keepawake = Mode(params)

        with keepawake as mode:
            if not mode.active:
                raise ModeExit

            # Render and display banner
            data = SessionData.from_mode(mode, deprecations)
            print(self.renderer.render_info_banner(data))

            # Wait with spinner animation
            wait_until_keyboardinterrupt(self.renderer)
            print("\n", end="")  # Add newline before logs

        if mode.result and mode.result.success:
            # If activation did not succeed, there is also no deactivation /
            # exit.
            print("\nExited.")
        return mode

    def handle_activation_error(self, result: ActivationResult) -> None:
        print(self.renderer.render_activation_error(result))


def parse_args(args: list[str]) -> Namespace:
    """Parse the command line arguments and return the parsed Namespace.

    Parameters
    ----------
    args : list[str]
        Command line arguments to parse

    Returns
    -------
    Namespace
        Parsed arguments

    """
    parser = argparse.ArgumentParser(
        prog="wakepy",
        formatter_class=lambda prog: argparse.HelpFormatter(
            prog,
            # makes more space for the "options" area on the left
            max_help_position=27,
        ),
    )

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
    return parser.parse_args(args)


def get_mode_name(args: Namespace) -> ModeName:
    """Extract the mode name from parsed arguments.

    Parameters
    ----------
    args : Namespace
        Parsed command line arguments

    Returns
    -------
    ModeName
        The name of the selected mode

    Raises
    ------
    ValueError
        If multiple modes are selected

    """
    # For the duration of deprecation, allow also the old flags
    keep_running = args.keep_running or args.k
    keep_presenting = args.keep_presenting or args.presentation

    n_flags_selected = sum((keep_running, keep_presenting))

    if n_flags_selected > 1:
        raise ValueError('You may only select one of the modes! See: "wakepy -h"')

    if keep_running or n_flags_selected == 0:
        # The default action, if nothing is selected, is "keep running"
        return ModeName.KEEP_RUNNING
    else:
        # We know keep_presenting is True, so it's safe to assert it
        assert keep_presenting  # noqa: S101
        return ModeName.KEEP_PRESENTING


def get_deprecations(args: Namespace) -> str:
    """Generate deprecation warnings based on used arguments.

    Parameters
    ----------
    args : Namespace
        Parsed command line arguments

    Returns
    -------
    str
        Deprecation warning text, or empty string if no deprecated args used

    """
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
            "in a future release. Use -p/--keepf-presenting, instead. ",
        )
    return "\n".join(deprecations) if deprecations else ""


def setup_logging(verbosity: int) -> None:
    log_level = get_logging_level(verbosity)
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(levelname)s - %(message)s"
    )


def get_logging_level(verbosity: int) -> int:
    if verbosity >= 2:  # Corresponds to -vv or higher
        return logging.DEBUG
    elif verbosity == 1:  # Corresponds to -v
        return logging.INFO
    elif verbosity == 0:  # No -v flags
        return logging.WARNING
    raise ValueError("Verbosity level cannot be negative.")


def wait_until_keyboardinterrupt(renderer: CLIRenderer) -> None:
    """Display a spinner and wait for keyboard interrupt.

    Parameters
    ----------
    renderer : CLIRenderer
        The renderer to use for spinner frames

    """
    try:
        for frame in renderer.spinner_frames():  # pragma: no branch
            print(frame, end="")
            time.sleep(renderer.spinner_interval)
    except KeyboardInterrupt:
        pass


def get_should_use_ascii_only(
    current_platform: IdentifiedPlatformType | None = None,
    python_impl: str | None = None,
) -> bool:
    """Check if ASCII-only mode should be used.

    Parameters
    ----------
    current_platform : IdentifiedPlatformType | None
        The platform to check. If None, uses CURRENT_PLATFORM.
    python_impl : str | None
        Python implementation name. If None, uses
        platform.python_implementation().

    Returns
    -------
    bool
        True if ASCII-only mode should be used, False otherwise.

    """
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


def main() -> None:
    """Entry point for the wakepy CLI."""
    CliApp().run(sys.argv[1:])


if __name__ == "__main__":
    # Entry point when running 'python -m wakepy'.
    main()  # pragma: no cover
