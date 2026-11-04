"""ActivationWarning source locations through public mode entry styles."""

from __future__ import annotations

import os
import runpy
import subprocess
import sys
import warnings
from pathlib import Path
from textwrap import dedent
from typing import Callable, Iterator, List

import pytest

import wakepy.core.mode as _mode_module
from wakepy import ActivationWarning


class TestActivationWarningLocation:
    """Identify entry lines and framework calls for deferred work."""

    @pytest.mark.parametrize("as_module", [True, False])
    def test_main_subprocess(
        self, write_script: Callable[[str, str], Path], as_module: bool
    ) -> None:
        """Activation failure must not crash an application launched with -m.

        CPython gh-123011 makes warn_explicit raise ImportError when given
        __main__ globals whose loader belongs to the original module name.
        A real subprocess exercises that loader/name mismatch, which mocked
        frames or runpy.run_path would miss. Direct script execution covers
        the entry point without a spec loader. Both must continue, display
        the user's source line, and preserve duplicate-warning suppression.

        https://github.com/python/cpython/issues/123011
        """
        script = write_script(
            """
            from wakepy import keep

            for _ in range(2):
                with keep.running():
                    print("continued")
            """,
            "my_app.py",
        )
        args = ["-m", "my_app"] if as_module else [str(script)]
        # Preserve cwd so subprocess coverage finds the project's config,
        # including platform exclusions. Make the test module importable.
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join(
            filter(None, [str(script.parent), env.get("PYTHONPATH", "")])
        )
        result = subprocess.run(  # noqa: S603 - Execute our test script.
            [sys.executable, "-W", "default", *args],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.splitlines() == ["continued", "continued"]
        assert result.stderr.count("ActivationWarning:") == 1
        assert f"{script}:4: ActivationWarning:" in result.stderr
        assert "\n  with keep.running():\n" in result.stderr

    @pytest.fixture(autouse=True)
    def force_activation_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("WAKEPY_FORCE_FAILURE", "1")
        monkeypatch.delenv("WAKEPY_FAKE_SUCCESS", raising=False)

    @pytest.fixture
    def write_script(self, tmp_path: Path) -> Callable[[str, str], Path]:
        def write(source: str, filename: str) -> Path:
            script = tmp_path / filename
            script.parent.mkdir(parents=True, exist_ok=True)
            script.write_text(dedent(source).lstrip(), encoding="utf-8")
            return script

        return write

    @pytest.fixture
    def captured_warnings(self) -> Iterator[List[warnings.WarningMessage]]:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ActivationWarning)
            yield caught

    @pytest.fixture
    def assert_warning_locations(
        self, captured_warnings: List[warnings.WarningMessage]
    ) -> Callable[[Path], None]:
        """Compare all ActivationWarnings with the script's # warning lines."""

        def check(script: Path) -> None:
            expected = [
                (str(script), line_number)
                for line_number, line in enumerate(
                    script.read_text(encoding="utf-8").splitlines(), 1
                )
                if "# warning" in line
            ]
            actual = [
                (warning.filename, warning.lineno)
                for warning in captured_warnings
                if issubclass(warning.category, ActivationWarning)
            ]
            assert expected, "The script must mark at least one warning location"
            assert actual == expected

        return check

    @pytest.mark.parametrize(
        "filename",
        [
            "warning_script.py",
            "importlib_tools/worker.py",
            "model_bootstrap/worker.py",
            "ordinary/_bootstrap_worker.py",
            "importlib_tools/_bootstrap_worker.py",
            "model_bootstrap/importlib_tools/worker.py",
        ],
    )
    @pytest.mark.parametrize(
        "source",
        [
            pytest.param(
                """
                from wakepy import keep

                with keep.running():  # warning
                    pass
                """,
                id="module-context",
            ),
            pytest.param(
                """
                from wakepy import keep

                def invoke():
                    with keep.running():  # warning
                        pass

                invoke()
                """,
                id="function-context",
            ),
            pytest.param(
                """
                from wakepy import keep

                mode = keep.running()
                try:
                    mode.enter()  # warning
                finally:
                    mode.exit()
                """,
                id="module-enter",
            ),
            pytest.param(
                """
                from wakepy import keep

                def invoke():
                    mode = keep.running()
                    try:
                        mode.enter()  # warning
                    finally:
                        mode.exit()

                invoke()
                """,
                id="function-enter",
            ),
            pytest.param(
                """
                from wakepy import keep

                @keep.running
                def invoke():
                    pass

                invoke()  # warning
                """,
                id="bare-decorator",
            ),
            pytest.param(
                """
                from wakepy import keep

                @keep.running()
                def invoke():
                    pass

                invoke()  # warning
                """,
                id="decorator-with-parentheses",
            ),
            pytest.param(
                """
                from contextlib import ExitStack
                from wakepy import keep

                with ExitStack() as stack:
                    stack.enter_context(keep.running())  # warning
                """,
                id="ExitStack",
            ),
        ],
    )
    def test_warning_points_to_user_call(
        self,
        write_script: Callable[[str, str], Path],
        assert_warning_locations: Callable[[Path], None],
        source: str,
        filename: str,
    ) -> None:
        """Keep entry locations correct across filenames and entry styles."""
        script = write_script(source, filename)
        runpy.run_path(str(script))
        assert_warning_locations(script)

    @pytest.mark.parametrize(
        "source",
        [
            pytest.param(
                """
                from contextlib import contextmanager
                from wakepy import keep

                @contextmanager
                def stay_awake():
                    with keep.running():  # warning
                        yield

                with stay_awake():
                    pass
                """,
                id="user-contextmanager-with-block",
            ),
            pytest.param(
                """
                from contextlib import contextmanager
                from wakepy import keep

                @contextmanager
                def stay_awake():
                    with keep.running():  # warning
                        yield

                @stay_awake()
                def work():
                    pass

                work()
                """,
                id="user-contextmanager-as-decorator",
            ),
            pytest.param(
                """
                from contextlib import ContextDecorator
                from wakepy import keep

                class StayAwake(ContextDecorator):
                    def __init__(self):
                        self.mode = keep.running()

                    def __enter__(self):
                        return self.mode.__enter__()  # warning

                    def __exit__(self, *exc_info):
                        return self.mode.__exit__(*exc_info)

                @StayAwake()
                def work():
                    pass

                work()
                """,
                id="user-ContextDecorator-subclass",
            ),
            pytest.param(
                """
                from contextlib import ExitStack, contextmanager
                from wakepy import keep

                @contextmanager
                def stay_awake():
                    with ExitStack() as stack:
                        stack.enter_context(keep.running())  # warning
                        yield

                with stay_awake():
                    pass
                """,
                id="user-contextmanager-with-ExitStack",
            ),
        ],
    )
    def test_user_contextlib_wrapper_preserves_its_entry_line(
        self,
        write_script: Callable[[str, str], Path],
        assert_warning_locations: Callable[[Path], None],
        source: str,
    ) -> None:
        """Skip contextlib delegation frames, never the user's wrapper.

        The warning belongs inside stay_awake/StayAwake where it enters
        wakepy, rather than at the outer with statement or decorated call.
        """
        script = write_script(source, "application.py")
        runpy.run_path(str(script))
        assert_warning_locations(script)

    # Regression cases: https://github.com/wakepy/wakepy/issues/548
    def test_warning_points_to_module_level_with_statement(
        self,
        write_script: Callable[[str, str], Path],
        assert_warning_locations: Callable[[Path], None],
    ) -> None:
        script = write_script(
            """
            from wakepy import keep

            with keep.running() as mode:  # warning
                pass
            """,
            "foo.py",
        )
        runpy.run_path(str(script))
        assert_warning_locations(script)

    def test_warning_points_to_with_statement_inside_function(
        self,
        write_script: Callable[[str, str], Path],
        assert_warning_locations: Callable[[Path], None],
    ) -> None:
        script = write_script(
            """
            from wakepy import keep

            def first():
                with keep.running():  # warning
                    pass

            first()
            """,
            "foo.py",
        )
        runpy.run_path(str(script))
        assert_warning_locations(script)

    def test_warning_points_to_call_of_function_with_bare_decorator(
        self,
        write_script: Callable[[str, str], Path],
        assert_warning_locations: Callable[[Path], None],
    ) -> None:
        script = write_script(
            """
            from wakepy import keep

            @keep.running
            def second():
                pass

            second()  # warning
            """,
            "foo.py",
        )
        runpy.run_path(str(script))
        assert_warning_locations(script)

    def test_warning_points_to_call_of_function_with_decorator_parentheses(
        self,
        write_script: Callable[[str, str], Path],
        assert_warning_locations: Callable[[Path], None],
    ) -> None:
        script = write_script(
            """
            from wakepy import keep

            @keep.running()
            def third():
                pass

            third()  # warning
            """,
            "foo.py",
        )
        runpy.run_path(str(script))
        assert_warning_locations(script)

    def test_internal_helper_in_another_module(
        self,
        monkeypatch: pytest.MonkeyPatch,
        write_script: Callable[[str, str], Path],
        assert_warning_locations: Callable[[Path], None],
    ) -> None:
        """Simulate a refactor; the warning should skip the internal helper."""
        helper = write_script(
            """
            from wakepy.core.mode import handle_activation_fail as original

            def forward(on_fail, result):
                return original(on_fail, result)
            """,
            "activation_helper.py",
        )
        namespace = runpy.run_path(
            str(helper), run_name="wakepy.core.activation_helper"
        )
        monkeypatch.setattr(
            _mode_module, "handle_activation_fail", namespace["forward"]
        )
        script = write_script(
            """
            from wakepy import keep

            with keep.running():  # warning
                pass
            """,
            "application.py",
        )
        runpy.run_path(str(script))
        assert_warning_locations(script)

    @pytest.mark.parametrize(
        "module_name", ["application", "contextlib", "wakepy_consumer"]
    )
    def test_application_globals_named_contextlib(
        self,
        write_script: Callable[[str, str], Path],
        assert_warning_locations: Callable[[Path], None],
        module_name: str,
    ) -> None:
        """Synthetic name collision, not a failure of stock contextlib.

        The actual contextlib module remains untouched. Only application
        globals use its name, exposing name equality versus module identity.
        """
        script = write_script(
            """
            from wakepy import keep

            with keep.running():  # warning
                pass
            """,
            "application.py",
        )
        exec(  # noqa: S102 - Deliberately execute with synthetic module globals.
            compile(script.read_text(encoding="utf-8"), str(script), "exec"),
            {"__name__": module_name},
        )
        assert_warning_locations(script)

    @pytest.mark.parametrize(
        ("source", "framework_filename"),
        [
            pytest.param(
                """
                from threading import Thread
                from wakepy import keep

                @keep.running()
                def work():
                    pass

                thread = Thread(target=work)  # scheduling site
                thread.start()
                thread.join(timeout=5)
                if thread.is_alive():
                    raise RuntimeError("thread did not stop")
                """,
                "threading.py",
                id="thread",
            ),
            pytest.param(
                """
                import asyncio
                from wakepy import keep

                @keep.running()
                def work():
                    pass

                loop = asyncio.new_event_loop()
                try:
                    loop.call_soon(work)  # scheduling site
                    loop.run_until_complete(asyncio.sleep(0))
                finally:
                    loop.close()
                """,
                "events.py",
                id="asyncio",
            ),
        ],
    )
    def test_deferred_callback_reports_framework_call(
        self,
        write_script: Callable[[str, str], Path],
        captured_warnings: List[warnings.WarningMessage],
        source: str,
        framework_filename: str,
    ) -> None:
        """Scheduling sites are outside the active callback stack.

        Verify the actual invocation instead of inventing a scheduling
        origin. Reporting the scheduling site needs a separate explicit API.
        """
        script = write_script(source, "application.py")
        runpy.run_path(str(script))
        activation_warnings = [
            warning
            for warning in captured_warnings
            if issubclass(warning.category, ActivationWarning)
        ]
        assert len(activation_warnings) == 1
        warning = activation_warnings[0]
        assert Path(warning.filename).name == framework_filename
        assert warning.lineno > 0
