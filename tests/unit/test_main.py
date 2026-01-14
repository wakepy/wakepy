"""Unit tests for the __main__ module"""

import argparse
import logging
import string
from unittest.mock import Mock, patch

import pytest

from tests.helpers import get_method_info
from wakepy import ActivationResult, Method, ProbingResults
from wakepy.__main__ import (
    CliApp,
    DisplayTheme,
    get_deprecations,
    get_logging_level,
    get_mode_name,
    get_should_use_ascii_only,
    main,
    parse_args,
    render_activation_error,
    render_deprecations,
    render_fake_success_warning,
    render_info_box,
    render_logo,
    setup_logging,
    spinner_frames,
    wait_for_interrupt,
)
from wakepy.core import PlatformType
from wakepy.core.activationresult import MethodActivationResult
from wakepy.core.constants import IdentifiedPlatformType, ModeName, StageName

# OutputHandler abstraction removed - tests now use capsys or patch print()


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
        with pytest.raises(
            ValueError, match="Cannot use both --keep-running and --keep-presenting"
        ):
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


def test_wait_for_interrupt_handles_keyboard_interrupt(capsys):
    """Test that wait_for_interrupt handles KeyboardInterrupt gracefully."""

    def interrupting_frames():
        yield "x"
        raise KeyboardInterrupt

    wait_for_interrupt(interrupting_frames(), interval=0)
    captured = capsys.readouterr().out
    assert captured == "x"


def test_wait_for_interrupt_with_no_frames():
    """Test that wait_for_interrupt handles empty iterator."""
    wait_for_interrupt(iter(()), interval=0)


def test_handle_activation_error(capsys):
    """Test that handle_activation_error prints error message."""
    result = ActivationResult([])
    app = CliApp()
    app.handle_activation_error(result)
    printed_text = capsys.readouterr().out
    assert printed_text
    assert "Wakepy could not activate" in printed_text


class TestCliAppRunWakepy:
    """Tests the CliApp.run_wakepy() method from the __main__.py in a simple
    way. This is more of a smoke test. The functionality of the different parts
    is already tested in other unit tests."""

    def test_working_mode(self, method1, capsys):
        with (
            patch("wakepy.__main__.get_mode_name", return_value=method1.mode_name),
            patch("wakepy.__main__.wait_for_interrupt"),
        ):
            app = CliApp()
            args = parse_args([])
            mode = app.run_wakepy(args)
            assert mode.result.success is True
            # Verify something was printed
            assert capsys.readouterr().out

    def test_default_renderer(self):
        app = CliApp()
        assert isinstance(app.theme, DisplayTheme)

    def test_custom_renderer(self):
        theme = DisplayTheme.create(ascii_mode=True)
        app = CliApp(theme=theme)
        assert app.theme is theme

    def test_non_working_mode(self, method2_broken, monkeypatch, capsys):
        # need to turn off WAKEPY_FAKE_SUCCESS as we want to get a failure.
        monkeypatch.setenv("WAKEPY_FAKE_SUCCESS", "0")
        with (
            patch(
                "wakepy.__main__.get_mode_name", return_value=method2_broken.mode_name
            ),
            patch("wakepy.__main__.wait_for_interrupt"),
        ):
            app = CliApp()
            args = parse_args([])
            mode = app.run_wakepy(args)
            assert mode.result.success is False

            # the method2_broken enter_mode raises this:
            assert mode.result.query()[0].failure_reason == "RuntimeError('foo')"

    @pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
    def test_working_mode_with_deprecations(self, capsys):
        with (
            patch(
                "wakepy.__main__.get_deprecations",
                return_value="Using -k is deprecated",
            ),
            patch("wakepy.__main__.wait_for_interrupt"),
        ):
            app = CliApp()
            args = parse_args([])
            mode = app.run_wakepy(args)
            assert mode.result.success is True
            output = capsys.readouterr().out
            assert "DEPRECATION NOTICE" in output


class TestCliAppRunWakepyVerbose:
    """Tests for verbose output in run_wakepy()."""

    @pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
    def test_verbose_mode_with_methods(self, capsys):
        """Test verbose mode when methods text is available."""
        with (
            patch("wakepy.__main__.get_mode_name", return_value=ModeName.KEEP_RUNNING),
            patch(
                "wakepy.core.activationresult._BaseActivationResult.get_methods_text_detailed",
                return_value="method1: SUCCESS",
            ),
            patch("wakepy.__main__.wait_for_interrupt"),
        ):
            app = CliApp()
            args = parse_args(["-v"])
            mode = app.run_wakepy(args)
            assert mode.result.success is True

            output = capsys.readouterr().out
            assert "Wakepy Methods (in the order of attempt):" in output

    @pytest.mark.usefixtures("WAKEPY_FAKE_SUCCESS_eq_1")
    def test_verbose_mode_with_no_methods(self, capsys):
        """Test verbose mode when methods text is empty."""
        with (
            patch("wakepy.__main__.get_mode_name", return_value=ModeName.KEEP_RUNNING),
            patch(
                "wakepy.core.activationresult._BaseActivationResult.get_methods_text_detailed",
                return_value="   ",
            ),
            patch("wakepy.__main__.wait_for_interrupt"),
        ):
            app = CliApp()
            args = parse_args(["-v"])
            mode = app.run_wakepy(args)
            assert mode.result.success is True

            output = capsys.readouterr().out
            assert "Did not try any methods!" in output


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

    def test_non_verbose_output(self, probe_result: ProbingResults, capsys):
        args = argparse.Namespace(
            keep_running=False,
            k=False,
            keep_presenting=False,
            presentation=False,
            verbose=0,
        )

        app = CliApp()
        app.run_wakepy_methods(args, probe_runner=lambda _: probe_result)

        output = capsys.readouterr().out
        # Compare normalized output (strip trailing spaces per line)
        expected_lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "                      keep.running",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "  1. method-a                                 SUCCESS",
            "  2. method-b                                 FAIL",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
        ]
        output_lines = [line.rstrip() for line in output.splitlines()]
        assert expected_lines == output_lines

    def test_verbose_output(self, probe_result: ProbingResults, capsys):
        args = argparse.Namespace(
            keep_running=False,
            k=False,
            keep_presenting=False,
            presentation=False,
            verbose=1,
        )

        app = CliApp()
        app.run_wakepy_methods(args, probe_runner=lambda _: probe_result)

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

    def test_default_probe_runner_prints_output(self, probe_result, capsys):
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
        ):
            app = CliApp()
            app.run_wakepy_methods(args)

        assert capsys.readouterr().out

    def test_probe_runner_overrides_default(self, probe_result, capsys):
        args = argparse.Namespace(
            keep_running=False,
            k=False,
            keep_presenting=False,
            presentation=False,
            verbose=0,
        )

        app = CliApp()
        app.run_wakepy_methods(args, probe_runner=lambda _: probe_result)

        assert capsys.readouterr().out


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


class TestRendering:
    expected_logo = r"""
                         _
                        | |
        __      __ __ _ | | __ ___  _ __   _   _
        \ \ /\ / // _` || |/ // _ \| '_ \ | | | |
         \ V  V /| (_| ||   <|  __/| |_) || |_| |
          \_/\_/  \__,_||_|\_\\___|| .__/  \__, |
         v.1.0.0                   | |      __/ |
                                   |_|     |___/ """.lstrip("\n")  # noqa: W291

    expected_info_box_unicode = r"""
 ┏━━ Mode: test_mode ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
 ┃                                                      ┃
 ┃  [✔] Programs keep running                           ┃
 ┃  [ ] Display kept on, screenlock disabled            ┃
 ┃                                                      ┃
 ┃   Method: test_method                                ┃
 ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛""".lstrip("\n")  # noqa: W291

    expected_info_box_ascii = r"""
 ┏━━ Mode: test_mode ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
 ┃                                                      ┃
 ┃  [x] Programs keep running                           ┃
 ┃  [ ] Display kept on, screenlock disabled            ┃
 ┃                                                      ┃
 ┃   Method: test_method                                ┃
 ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛""".lstrip("\n")  # noqa: W291

    def test_render_logo(self):
        output_logo = render_logo("1.0.0")
        assert output_logo == self.expected_logo

    @pytest.mark.parametrize(
        "ascii_mode,expected_info_box",
        [
            (False, expected_info_box_unicode),  # Unicode
            (True, expected_info_box_ascii),  # ASCII
        ],
    )
    def test_render_info_box_uses_correct_template(self, ascii_mode, expected_info_box):
        theme = DisplayTheme.create(ascii_mode=ascii_mode)
        output_box = render_info_box(
            theme,
            "test_mode",
            "test_method",
            is_presentation_mode=False,
        )
        assert output_box == expected_info_box

    def test_render_deprecations(self):
        deprecations = "This feature is deprecated"
        formatted = render_deprecations(deprecations)

        assert "DEPRECATION NOTICE" in formatted
        assert deprecations in formatted

    def test_render_fake_success_warning(self):
        formatted = render_fake_success_warning()

        assert "WAKEPY_FAKE_SUCCESS" in formatted
        assert "WARNING" in formatted

    def test_render_info_box_truncates_long_names(self):
        base = string.ascii_letters + string.digits
        very_long_mode = "mode_" + base
        very_long_method = "method_" + base
        theme = DisplayTheme.create(ascii_mode=False)
        formatted = render_info_box(
            theme,
            very_long_mode,
            very_long_method,
            is_presentation_mode=False,
        )

        expected = r"""
 ┏━━ Mode: mode_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKL ━┓
 ┃                                                      ┃
 ┃  [✔] Programs keep running                           ┃
 ┃  [ ] Display kept on, screenlock disabled            ┃
 ┃                                                      ┃
 ┃   Method: method_abcdefghijklmnopqrstuvwxyzABCDEFGHI ┃
 ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛""".lstrip("\n")  # noqa: W291
        assert formatted == expected

    def test_spinner_frames(self):
        theme = DisplayTheme.create(ascii_mode=False)

        # Get the first few frames from the infinite generator
        frames = []
        for i, frame in enumerate(spinner_frames(theme)):
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

    def test_render_activation_error_default_system_info(self):
        result = ActivationResult([])
        formatted = render_activation_error(result)
        assert "Wakepy could not activate" in formatted


class TestMain:
    """Test the main() entry point function."""

    def test_main_calls_run_wakepy(self):
        """Test that main() parses args and calls run_wakepy."""
        mock_app = Mock()
        with patch("wakepy.__main__.setup_logging"):
            main(argv=["-v", "-p"], app=mock_app)
        mock_app.run_wakepy.assert_called_once()
        mock_app.run_wakepy_methods.assert_not_called()

    def test_main_default_app_and_argv(self):
        with patch("wakepy.__main__.setup_logging"), patch(
            "wakepy.__main__.CliApp"
        ) as mock_cli_app, patch("wakepy.__main__.sys.argv", ["wakepy", "-v", "-p"]):
            main()
            mock_instance = mock_cli_app.return_value
            mock_instance.run_wakepy.assert_called_once()
            mock_instance.run_wakepy_methods.assert_not_called()

    def test_main_calls_run_wakepy_methods(self):
        """Test that main() calls run_wakepy_methods for 'methods' command."""
        mock_app = Mock()
        with patch("wakepy.__main__.setup_logging"):
            main(argv=["methods", "-p"], app=mock_app)
        mock_app.run_wakepy_methods.assert_called_once()
        mock_app.run_wakepy.assert_not_called()


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
