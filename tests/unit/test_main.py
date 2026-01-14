"""Unit tests for the __main__ module"""

import argparse
import logging
import string
import sys
from dataclasses import replace
from unittest.mock import patch

import pytest

from tests.helpers import get_method_info
from wakepy import ActivationResult, Method, Mode, ProbingResults
from wakepy.__main__ import (
    CliApp,
    CLIRenderer,
    DisplayTheme,
    SessionData,
    get_deprecations,
    get_logging_level,
    get_mode_name,
    get_should_use_ascii_only,
    main,
    parse_args,
    setup_logging,
    wait_until_keyboardinterrupt,
)
from wakepy.core import PlatformType
from wakepy.core.activationresult import MethodActivationResult
from wakepy.core.constants import IdentifiedPlatformType, ModeName, StageName
from wakepy.core.mode import _ModeParams
from wakepy.methods._testing import WakepyFakeSuccess


@pytest.fixture
def mode_name_working():
    return "testmode_working"


@pytest.fixture
def mode_name_broken():
    return "testmode_broken"


@pytest.fixture
def method1(mode_name_working):
    class WorkingMethod(Method):
        """This is a successful method as it implements enter_mode which
        returns None"""

        name = "method1"
        mode_name = mode_name_working
        supported_platforms = (PlatformType.ANY,)

        def enter_mode(self) -> None:
            return

    return WorkingMethod


@pytest.fixture
def method2_broken(mode_name_broken):
    class BrokenMethod(Method):
        """This is a unsuccessful method as it implements enter_mode which
        raises an Exception"""

        name = "method2_broken"
        mode_name = mode_name_broken
        supported_platforms = (PlatformType.ANY,)

        def enter_mode(self) -> None:
            raise RuntimeError("foo")

    return BrokenMethod


class TestGetModeName:
    @pytest.mark.parametrize(
        "sysargs",
        [
            ["-r"],
            ["--keep-running"],
            # Also no args means keep running
            [],
        ],
    )
    def test_keep_running(self, sysargs):
        assert get_mode_name(parse_args(sysargs)) == ModeName.KEEP_RUNNING

    @pytest.mark.parametrize(
        "sysargs",
        [
            ["-p"],
            ["--keep-presenting"],
        ],
    )
    def test_keep_presenting(self, sysargs):
        assert get_mode_name(parse_args(sysargs)) == ModeName.KEEP_PRESENTING

    @pytest.mark.parametrize(
        "sysargs",
        [
            ["-r", "-p"],
            ["--keep-presenting", "-r"],
            ["-p", "--keep-running"],
            ["--keep-presenting", "--keep-running"],
        ],
    )
    def test_too_many_modes(self, sysargs):
        with pytest.raises(ValueError, match="You may only select one of the modes!"):
            assert get_mode_name(parse_args(sysargs))


@pytest.mark.parametrize(
    "sysargs",
    [
        ["--presentation"],
        ["-k"],
    ],
)
def test_deprecations(sysargs):
    deprecations = get_deprecations(parse_args(sysargs))
    assert f"Using {sysargs[0]} is deprecated in wakepy 0.10.0" in deprecations


def test_wait_until_keyboardinterrupt():
    def raise_keyboardinterrupt(_):
        raise KeyboardInterrupt

    with patch("wakepy.__main__.time") as timemock:
        timemock.sleep.side_effect = raise_keyboardinterrupt
        theme = DisplayTheme.create()
        renderer = CLIRenderer(theme)
        wait_until_keyboardinterrupt(renderer)


@patch("builtins.print")
def test_handle_activation_error(print_mock):
    result = ActivationResult([])
    app = CliApp()
    app.handle_activation_error(result)
    if sys.version_info[:2] == (3, 7):
        # on python 3.7, need to do other way.
        printed_text = print_mock.mock_calls[0][1][0]
    else:
        printed_text = "\n".join(print_mock.mock_calls[0].args)
    # Some sensible text was printed to the user
    assert "Wakepy could not activate" in printed_text


class TestCliAppRunWakepy:
    """Tests the CliApp.run_wakepy() method from the __main__.py in a simple
    way. This is more of a smoke test. The functionality of the different parts
    is already tested in other unit tests."""

    @pytest.fixture(autouse=True)
    def patch_function(self):
        with patch("wakepy.__main__.wait_until_keyboardinterrupt"), patch(
            "builtins.print"
        ):
            yield

    def test_working_mode(
        self,
        method1,
    ):
        with patch("wakepy.__main__.get_mode_name", return_value=method1.mode_name):
            app = CliApp()
            args = parse_args([])
            mode = app.run_wakepy(args)
            assert mode.result.success is True

    def test_non_working_mode(self, method2_broken, monkeypatch):
        # need to turn off WAKEPY_FAKE_SUCCESS as we want to get a failure.
        monkeypatch.setenv("WAKEPY_FAKE_SUCCESS", "0")
        with patch(
            "wakepy.__main__.get_mode_name", return_value=method2_broken.mode_name
        ):
            app = CliApp()
            args = parse_args([])
            mode = app.run_wakepy(args)
            assert mode.result.success is False

            # the method2_broken enter_mode raises this:
            assert mode.result.query()[0].failure_reason == "RuntimeError('foo')"


class TestCliAppRunWakepyMethods:
    @pytest.fixture
    def probe_result(self):
        return ProbingResults(
            [
                MethodActivationResult(
                    method=get_method_info("method-a"),
                    success=True,
                ),
                MethodActivationResult(
                    method=get_method_info("method-b"),
                    success=False,
                    failure_stage=StageName.REQUIREMENTS,
                    failure_reason="Missing requirement",
                ),
            ]
        )

    def test_non_verbose_output(self, capsys, probe_result: ProbingResults):
        args = argparse.Namespace(
            keep_running=False,
            k=False,
            keep_presenting=False,
            presentation=False,
            verbose=0,
        )

        with patch(
            "wakepy.__main__.Mode.probe_all_methods",
            return_value=probe_result,
        ), patch("wakepy.__main__.get_mode_name", return_value=ModeName.KEEP_RUNNING):
            app = CliApp()
            app.run_wakepy_methods(args)

        output = capsys.readouterr().out
        expected = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                      keep.running
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. method-a                                 SUCCESS   
  2. method-b                                 FAIL      
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

""".lstrip("\n")  # noqa: W291

        assert expected == output

    def test_verbose_output(self, capsys, probe_result: ProbingResults):
        args = argparse.Namespace(
            keep_running=False,
            k=False,
            keep_presenting=False,
            presentation=False,
            verbose=1,
        )

        with patch(
            "wakepy.__main__.Mode.probe_all_methods",
            return_value=probe_result,
        ), patch("wakepy.__main__.get_mode_name", return_value=ModeName.KEEP_RUNNING):
            app = CliApp()
            app.run_wakepy_methods(args)

        output = capsys.readouterr().out
        expected = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                                  keep.running
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. method-a
     SUCCESS

  2. method-b
     FAIL: Missing requirement

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

""".lstrip("\n")
        assert expected == output


class TestDisplayTheme:
    def test_create_unicode(self):
        theme = DisplayTheme.create(ascii_mode=False)
        # fmt: off
        assert theme.spinner_symbols == ("⢎⡰", "⢎⡡", "⢎⡑", "⢎⠱", "⠎⡱", "⢊⡱", "⢌⡱", "⢆⡱")  # noqa: E501
        # fmt: on
        assert theme.success_symbol == "✔"
        assert theme.ascii_mode is False

    def test_create_ascii(self):
        theme = DisplayTheme.create(ascii_mode=True)
        assert theme.spinner_symbols == ("|", "/", "-", "\\")
        assert theme.success_symbol == "x"
        assert theme.ascii_mode is True


class TestShouldUseAsciiOnly:
    @pytest.mark.parametrize(
        "platform,python_impl,expected",
        [
            # Non-Windows platforms should always use Unicode
            (IdentifiedPlatformType.LINUX, "CPython", False),
            (IdentifiedPlatformType.LINUX, "PyPy", False),
            (IdentifiedPlatformType.MACOS, "CPython", False),
            (IdentifiedPlatformType.MACOS, "PyPy", False),
            # Windows + PyPy needs ASCII mode
            (IdentifiedPlatformType.WINDOWS, "PyPy", True),
            (IdentifiedPlatformType.WINDOWS, "pypy", True),  # case insensitive
            # Windows + CPython can use Unicode
            (IdentifiedPlatformType.WINDOWS, "CPython", False),
        ],
    )
    def test_ascii_mode_detection(self, platform, python_impl, expected):
        """Test ASCII mode detection based on platform and Python impl."""
        assert (
            get_should_use_ascii_only(
                current_platform=platform, python_impl=python_impl
            )
            is expected
        )


@pytest.fixture
def somemode():
    params = _ModeParams([WakepyFakeSuccess], name="testmode")
    return Mode(params)


class TestSessionData:
    @patch("wakepy.__version__", "0.10.0")
    def test_from_mode(self, somemode: Mode):
        with somemode as m:
            session_data = SessionData.from_mode(m, deprecations="")

        assert session_data.wakepy_version == "0.10.0"
        assert session_data.mode_name == "testmode"
        assert session_data.method_name == "WakepyFakeSuccess"
        assert session_data.is_presentation_mode is False
        assert session_data.deprecations == ""
        # WakepyFakeSuccess has real_success=False, so is_fake_success=True
        assert session_data.is_fake_success is True

        with somemode as m:
            session_data = SessionData.from_mode(m, deprecations="test deprecation")

        assert session_data.deprecations == "test deprecation"

    @pytest.mark.parametrize(
        "mode_name,expected",
        [
            (ModeName.KEEP_PRESENTING, True),
            (ModeName.KEEP_RUNNING, False),
            ("other_mode", False),
        ],
    )
    def test_is_keep_presenting_mode(self, mode_name, expected):
        session_data = SessionData(
            wakepy_version="1.0.0",
            mode_name=mode_name,
            method_name="test_method",
        )
        assert session_data.is_presentation_mode is expected


class TestCLIRenderer:
    """Test the formatting logic of CLIRenderer.

    These tests verify that the renderer correctly formats SessionData
    using a DisplayTheme, but focus on structural elements
    rather than exact string matching.
    """

    @pytest.fixture
    def base_session_data(self):
        """Base SessionData for testing."""
        return SessionData(
            wakepy_version="1.0.0",
            mode_name="test_mode",
            method_name="test_method",
            deprecations="",
            is_fake_success=False,
        )

    @pytest.fixture
    def unicode_renderer(self):
        """Renderer with Unicode theme."""
        return CLIRenderer(DisplayTheme.create(ascii_mode=False))

    @pytest.fixture
    def ascii_renderer(self):
        """Renderer with ASCII theme."""
        return CLIRenderer(DisplayTheme.create(ascii_mode=True))

    expected_info_banner = r"""
                         _
                        | |
        __      __ __ _ | | __ ___  _ __   _   _
        \ \ /\ / // _` || |/ // _ \| '_ \ | | | |
         \ V  V /| (_| ||   <|  __/| |_) || |_| |
          \_/\_/  \__,_||_|\_\\___|| .__/  \__, |
         v.1.0.0                   | |      __/ |
                                   |_|     |___/ 
 ┏━━ Mode: test_mode ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
 ┃                                                      ┃
 ┃  [✔] Programs keep running                           ┃
 ┃  [ ] Display kept on, screenlock disabled            ┃
 ┃                                                      ┃
 ┃   Method: test_method                                ┃
 ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛""".lstrip("\n")  # noqa: W291

    expected_info_banner_ascii = r"""
                         _
                        | |
        __      __ __ _ | | __ ___  _ __   _   _
        \ \ /\ / // _` || |/ // _ \| '_ \ | | | |
         \ V  V /| (_| ||   <|  __/| |_) || |_| |
          \_/\_/  \__,_||_|\_\\___|| .__/  \__, |
         v.1.0.0                   | |      __/ |
                                   |_|     |___/ 
 ┏━━ Mode: test_mode ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
 ┃                                                      ┃
 ┃  [x] Programs keep running                           ┃
 ┃  [ ] Display kept on, screenlock disabled            ┃
 ┃                                                      ┃
 ┃   Method: test_method                                ┃
 ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛""".lstrip("\n")  # noqa: W291

    @pytest.mark.parametrize(
        "ascii_mode,expected_info_banner",
        [
            (False, expected_info_banner),  # Unicode
            (True, expected_info_banner_ascii),  # ASCII
        ],
    )
    def test_render_info_banner_uses_correct_template(
        self, base_session_data, ascii_mode, expected_info_banner
    ):
        """Test that correct template is used for ASCII/Unicode mode."""
        theme = DisplayTheme.create(ascii_mode=ascii_mode)
        renderer = CLIRenderer(theme)

        output_banner = renderer.render_info_banner(base_session_data)

        assert output_banner == expected_info_banner

    @pytest.mark.parametrize(
        "deprecations,should_contain",
        [
            ("This feature is deprecated", True),
            ("", False),
        ],
    )
    def test_render_info_banner_deprecations(
        self, base_session_data, unicode_renderer, deprecations, should_contain
    ):
        """Test that deprecation warnings are included/excluded correctly."""
        session_data = replace(base_session_data, deprecations=deprecations)
        formatted = unicode_renderer.render_info_banner(session_data)

        if should_contain:
            assert "DEPRECATION NOTICE" in formatted
            assert deprecations in formatted
        else:
            assert "DEPRECATION NOTICE" not in formatted

    @pytest.mark.parametrize(
        "is_fake_success,should_contain",
        [
            (True, True),
            (False, False),
        ],
    )
    def test_render_info_banner_fake_success_warning(
        self, base_session_data, unicode_renderer, is_fake_success, should_contain
    ):
        """Test that fake success warning is shown/hidden correctly."""

        session_data = replace(base_session_data, is_fake_success=is_fake_success)
        formatted = unicode_renderer.render_info_banner(session_data)

        if should_contain:
            assert "WAKEPY_FAKE_SUCCESS" in formatted
            assert "WARNING" in formatted
        else:
            assert "WAKEPY_FAKE_SUCCESS" not in formatted

    def test_render_info_banner_truncates_long_names(self):
        """Test that mode and method names are truncated to max length."""

        base = string.ascii_letters + string.digits
        very_long_mode = "mode_" + base
        very_long_method = "method_" + base
        session_data = SessionData(
            wakepy_version="1.0.0",
            mode_name=very_long_mode,
            method_name=very_long_method,
            deprecations="",
            is_fake_success=False,
        )
        theme = DisplayTheme.create(ascii_mode=False)
        renderer = CLIRenderer(theme)

        formatted = renderer.render_info_banner(session_data)

        expected = r"""
                         _
                        | |
        __      __ __ _ | | __ ___  _ __   _   _
        \ \ /\ / // _` || |/ // _ \| '_ \ | | | |
         \ V  V /| (_| ||   <|  __/| |_) || |_| |
          \_/\_/  \__,_||_|\_\\___|| .__/  \__, |
         v.1.0.0                   | |      __/ |
                                   |_|     |___/ 
 ┏━━ Mode: mode_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKL ━┓
 ┃                                                      ┃
 ┃  [✔] Programs keep running                           ┃
 ┃  [ ] Display kept on, screenlock disabled            ┃
 ┃                                                      ┃
 ┃   Method: method_abcdefghijklmnopqrstuvwxyzABCDEFGHI ┃
 ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛""".lstrip("\n")  # noqa: W291
        assert formatted == expected

    def test_spinner_frames(self, unicode_renderer):
        """Test that spinner_frames generates correct frames."""
        theme = unicode_renderer.theme

        # Get the first few frames from the infinite generator
        frames = []
        for i, frame in enumerate(unicode_renderer.spinner_frames()):
            frames.append(frame)
            if i >= len(theme.spinner_symbols):
                # Get one full cycle plus one to verify it cycles
                break

        # Check that we got frames
        assert len(frames) > 0

        # Each frame should contain the "Press Ctrl+C to exit" message
        for frame in frames:
            assert "[Press Ctrl+C to exit]" in frame

        # The frames should cycle through the symbols
        # First frame should contain first symbol, etc.
        for i, symbol in enumerate(theme.spinner_symbols):
            assert symbol in frames[i]


class TestMain:
    """Test the main() entry point function."""

    def test_main_calls_run_wakepy(self):
        """Test that main() parses args and calls run_wakepy."""
        with patch("wakepy.__main__.CliApp") as mock_cli_app, patch(
            "wakepy.__main__.sys.argv", ["wakepy", "-v", "-p"]
        ), patch("wakepy.__main__.setup_logging"):
            main()
            # Verify run_wakepy was called (not run_wakepy_methods)
            mock_instance = mock_cli_app.return_value
            mock_instance.run_wakepy.assert_called_once()
            mock_instance.run_wakepy_methods.assert_not_called()

    def test_main_calls_run_wakepy_methods(self):
        """Test that main() calls run_wakepy_methods for 'methods' command."""
        with patch("wakepy.__main__.CliApp") as mock_cli_app, patch(
            "wakepy.__main__.sys.argv", ["wakepy", "methods", "-p"]
        ), patch("wakepy.__main__.setup_logging"):
            main()
            # Verify run_wakepy_methods was called (not run_wakepy)
            mock_instance = mock_cli_app.return_value
            mock_instance.run_wakepy_methods.assert_called_once()
            mock_instance.run_wakepy.assert_not_called()


class TestGetLoggingLevel:
    @pytest.mark.parametrize(
        "verbosity, expected_level",
        [
            (0, logging.WARNING),
            (1, logging.INFO),
            (2, logging.DEBUG),
            (3, logging.DEBUG),
        ],
    )
    def test_get_logging_level(self, verbosity, expected_level):
        assert get_logging_level(verbosity) == expected_level

    @pytest.mark.parametrize(
        "verbosity, expected_level",
        [
            (0, logging.WARNING),
            (1, logging.WARNING),  # -v only enables detailed output, not INFO
            (2, logging.INFO),
            (3, logging.DEBUG),
        ],
    )
    def test_get_logging_level_methods(self, verbosity, expected_level):
        assert get_logging_level(verbosity, command="methods") == expected_level


def test_setup_logging_calls_basic_config():
    with patch("wakepy.__main__.logging.basicConfig") as basic_config:
        setup_logging(verbosity=1, command="run")
        basic_config.assert_called_once()
