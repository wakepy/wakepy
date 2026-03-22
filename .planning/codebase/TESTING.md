# Testing Patterns

**Analysis Date:** 2026-02-19

## Test Framework

**Runner:**
- `pytest` >= 8.3.5 (for Python 3.13+, otherwise >= 6.2)
- Config: No `pytest.ini` or `setup.cfg` used; all config in `pyproject.toml`
- Coverage tool: `pytest-cov` (4.1.0 for Python 3.7, 5.0.0+ for Python 3.8+)
- Coverage plugin: `coverage-conditional-plugin` >= 0.9.0 for platform/version-specific coverage

**Assertion Library:**
- Native `assert` statements (no special library)
- Custom `do_assert()` fixture for type checking workarounds with mypy

**Run Commands:**
```bash
just test-cli ARGUMENTS              # Run tests (replaces pytest directly)
uv run pytest tests/                  # Run all tests
uv run pytest tests/unit/             # Run unit tests only
uv run pytest tests/integration/      # Run integration tests only
uv run pytest -v tests/               # Run with verbose output
uv run pytest --cov                   # Run with coverage report
```

**Important:** Always use `uv run pytest` or `just test-cli`, never `python -m pytest`

## Test File Organization

**Location:**
- Unit tests: `tests/unit/` - Mocked tests, no external dependencies
- Integration tests: `tests/integration/` - Real platform/D-Bus interactions
- D-Bus integration tests: `tests/integration/test_dbus/` - Custom D-Bus server fixtures
- Test helpers: `tests/helpers.py`, `tests/unit/test_core/testmethods.py`

**Naming:**
- Test modules: `test_*.py` pattern
- Test classes: `Test*` pattern (e.g., `TestProcessDBusCall`, `TestFreedesktopEnterMode`)
- Test functions: `test_*` pattern
- Example: `tests/unit/test_core/test_method/test_activation.py::TestActivateMethod::test_method_without_name`

**Structure:**
```
tests/
├── conftest.py                          # Global fixtures
├── helpers.py                           # Shared test utilities
├── unit/
│   ├── conftest.py                      # Unit test fixtures
│   ├── test_core/
│   │   ├── conftest.py                  # Core module fixtures
│   │   ├── test_method/
│   │   │   ├── test_method.py           # Method class tests
│   │   │   └── test_activation.py       # Method activation tests
│   │   └── test_*.py                    # Other core module tests
│   ├── test_methods/
│   │   ├── test_windows.py
│   │   ├── test_gnome.py
│   │   ├── test_freedesktop.py
│   │   └── test_macos.py
│   └── test_keep.py                     # Public API tests
└── integration/
    ├── test_dbus/
    │   ├── conftest.py                  # D-Bus service fixtures
    │   ├── dbus_service.py              # Test D-Bus service
    │   └── test_dbus_adapters.py        # D-Bus adapter tests
    └── test_macos.py                    # macOS-specific tests
```

## Test Structure

**Suite Organization (pytest with class-based tests):**

```python
class TestProcessDBusCall:
    def test_missing_dbus_adapter(self, dbus_method: DBusMethod):
        method = Method()
        # when there is no dbus adapter..
        assert method.dbus_adapter is None
        # we get RuntimeError
        with pytest.raises(RuntimeError, match=".*cannot process dbus method call.*"):
            method.process_dbus_call(DBusMethodCall(dbus_method))

    def test_error_when_calling_dbus_methods(self, dbus_method: DBusMethod):
        # Test setup with inline class definitions
        class MockedDBusAdapter(DBusAdapter):
            def process(self, _: DBusMethodCall) -> object:
                return "error"

        method = Method(dbus_adapter=MockedDBusAdapter())
        with pytest.raises(DBusCallError):
            method.process_dbus_call(DBusMethodCall(dbus_method))
```

**Patterns:**
- Docstrings on test methods explain the scenario:
  ```python
  def test_method_without_name(self):
      """Methods used for activation must have a name. If not, there should
      be a ValueError raised"""
  ```

- Comments mark test phases with "when", "then":
  ```python
  # when there is no dbus adapter..
  assert method.dbus_adapter is None
  # we get RuntimeError
  with pytest.raises(RuntimeError):
      ...
  ```

- Setup inline with class definitions for readability:
  ```python
  class WithEnterAndExit(TestMethod):
      def enter_mode(self):
          return

      def exit_mode(self):
          return

  method1 = WithEnterAndExit()
  assert has_enter(method1)
  ```

## Fixtures

**Global Fixtures (in `tests/conftest.py`):**
- `method1` - Basic `TestMethod()` instance
- `set_current_platform_to_linux` - Platform monkeypatch fixture
- `set_current_platform_to_windows` - Platform monkeypatch fixture
- `set_current_platform_to_unknown` - Platform monkeypatch fixture
- `do_assert()` - Custom assert function (returns callable)
- `assert_strenum_values()` - StrEnum validation (returns callable)
- `current_platform` - Parametrized platform fixture

**Unit Test Fixtures (in `tests/unit/conftest.py`):**
```python
class TestDBusAdapter(DBusAdapter):
    """A fake dbus adapter used in tests"""

@pytest.fixture(scope="session")
def fake_dbus_adapter():
    return TestDBusAdapter

@pytest.fixture(scope="function")
def empty_method_registry(monkeypatch):
    """Clear method registry keeping only WakepyFakeSuccess"""
    TestUtils.empty_method_registry(monkeypatch)

@pytest.fixture(scope="function", name="WAKEPY_FAKE_SUCCESS_eq_1")
def _wakepy_fake_success_fixture(monkeypatch):
    monkeypatch.setenv("WAKEPY_FAKE_SUCCESS", "1")
```

**Core Module Fixtures (in `tests/unit/test_core/conftest.py`):**
```python
@pytest.fixture(scope="function")
def provide_methods_different_platforms(monkeypatch, testutils):
    """Register test methods with different platform support"""
    testutils.empty_method_registry(monkeypatch)

    class WindowsA(TestMethod):
        name = "WinA"
        supported_platforms = (PlatformType.WINDOWS,)

    class LinuxA(TestMethod):
        name = "LinuxA"
        supported_platforms = (PlatformType.LINUX,)

@pytest.fixture(scope="function")
def provide_methods_a_f(monkeypatch, testutils):
    """Register methods A-F with various mode names"""
    testutils.empty_method_registry(monkeypatch)
    # ... define MethodA through MethodF
```

**D-Bus Integration Fixtures (in `tests/integration/test_dbus/conftest.py`):**
```python
@pytest.fixture(scope="session", autouse=True)
def private_bus():
    """Real dbus-daemon instance for testing. Runs in subprocess."""
    _start_cmd = "dbus-daemon --session --print-address"
    p = subprocess.Popen(...)
    bus_address = p.stdout.readline().decode("utf-8").strip()
    yield bus_address
    p.terminate()

@pytest.fixture(scope="session")
def dbus_calculator_service(calculator_service_addr, private_bus):
    """Provides a real D-Bus service for testing"""
    class TestCalculatorService(DBusService):
        addr = calculator_service_addr
        def handle_method(self, method: str, args):
            # ... implement service method

    yield from start_dbus_service(TestCalculatorService, bus_address=private_bus)
```

**Fixture Scopes:**
- `session` - D-Bus services, platform detection helpers, utilities (shared across all tests)
- `function` - Test methods, environment variables, monkeypatches (fresh per test)
- `class` - Not explicitly used; scope is typically function

## Mocking

**Framework:** `unittest.mock` standard library

**Patterns:**
```python
from unittest.mock import patch

# Simple mock inline:
class MockedDBusAdapter(DBusAdapter):
    def process(self, _: DBusMethodCall) -> object:
        return "error"

method = Method(dbus_adapter=MockedDBusAdapter())

# Monkeypatching via fixtures (pytest):
def test_something(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("wakepy.core.mode.CURRENT_PLATFORM", IdentifiedPlatformType.LINUX)
    monkeypatch.setenv("WAKEPY_FAKE_SUCCESS", "1")

# patch decorator:
@patch("subprocess.Popen")
def test_with_patch(mock_popen):
    # Use mock_popen
    pass
```

**What to Mock:**
- D-Bus adapters (custom test implementation)
- Platform detection (via monkeypatch fixtures)
- Subprocess calls (for Freedesktop methods that call `subprocess`)
- Environment variables (via `monkeypatch.setenv()`)
- External services (would use DBusService test harness)

**What NOT to Mock:**
- Method lifecycle (enter_mode, exit_mode, heartbeat)
- Mode activation logic
- Registry operations (use `empty_method_registry` fixture instead)
- File I/O or OS calls if testing those specifically (integration tests)

## Test Data & Factories

**Test Method Base Class (in `tests/unit/test_core/testmethods.py`):**
```python
class TestMethod(Method):
    """Base class for test methods"""
    name = "TestMethod"
    mode_name = ModeName.KEEP_RUNNING

def get_test_method_class(
    supported_platforms=...,
    enter_mode=...,
    exit_mode=...,
    heartbeat=...,
    caniuse=...
) -> Type[TestMethod]:
    """Factory function to create test method classes with custom behavior"""
    class CustomTestMethod(TestMethod):
        # ... customize behavior
    return CustomTestMethod
```

**Combinations Helper (in `tests/unit/test_core/testmethods.py`):**
```python
def combinations_of_test_methods(
    enters,      # List of (enter_value, description)
    exits,       # List of (exit_value, description)
    heartbeats,  # List of (heartbeat_value, description)
) -> Iterator[...]:
    """Generate all combinations of test method behaviors"""
    # Yields tuples of (method_class, description)
```

**Fixtures with Test Data:**
```python
@pytest.fixture(scope="function")
def provide_methods_a_f(monkeypatch, testutils):
    testutils.empty_method_registry(monkeypatch)
    FIRST_MODE = "first_mode"
    SECOND_MODE = "second_mode"

    class MethodA(TestMethod):
        name = "A"
        mode_name = SECOND_MODE

    class MethodB(TestMethod):
        name = "B"
        mode_name = FIRST_MODE
    # ... more methods
```

## Coverage

**Requirements:** 100% test coverage enforced

**Configuration (in `pyproject.toml`):**
```toml
[tool.coverage.run]
plugins = ["coverage_conditional_plugin"]
omit = ["tests/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if (?:typing\\.)?TYPE_CHECKING:",
    "@(abc\\.)?abstractmethod",
    "@(typing\\.)?overload",
    "raise NotImplementedError"
]

[tool.coverage.coverage_conditional_plugin.omit]
# Dbus adapters are only available on linux
"platform_system != 'Linux'" = "**/wakepy/dbus_adapters/*.py"
# Windows methods only need to be tested on Windows
"platform_system != 'Windows'" = "**/wakepy/methods/windows.py"
# MacOS methods only need to be tested on MacOS
"platform_system != 'Darwin'" = "**/wakepy/methods/macos.py"

[tool.coverage.coverage_conditional_plugin.rules]
no-cover-if-no-dbus = "platform_system != 'Linux' or not __import__('shutil').which('dbus-daemon')"
no-cover-if-py-gte-38 = "sys_version_info >= (3, 8)"
no-cover-if-py-lt-38 = "sys_version_info < (3, 8)"
no-cover-if-py-gte-310 = "sys_version_info >= (3, 10)"
no-cover-if-py-lt-310 = "sys_version_info < (3, 10)"
```

**View Coverage:**
```bash
uv run pytest --cov=wakepy --cov-report=html
# Coverage report at htmlcov/index.html
uv run pytest --cov=wakepy --cov-report=term-missing
```

**Pragma Directives for Cross-Platform Testing:**
- `# pragma: no-cover-if-py-gte-38` - Code only executed on Python < 3.8
- `# pragma: no-cover-if-py-lt-38` - Code only executed on Python >= 3.8
- `# pragma: no-cover-if-py-gte-310` - Code only executed on Python < 3.10
- `# pragma: no-cover-if-py-lt-310` - Code only executed on Python >= 3.10
- `# pragma: no-cover-if-no-dbus` - D-Bus code (Linux + dbus-daemon installed)

These allow 100% coverage on each platform without false gaps.

## Test Types

**Unit Tests (in `tests/unit/`):**
- Scope: Individual functions/methods
- Dependencies: Mocked (D-Bus adapters, subprocess, etc.)
- Approach: Fast, isolated, deterministic
- Example: `tests/unit/test_core/test_method/test_method.py::test_method_defaults`

**Integration Tests (in `tests/integration/`):**
- Scope: Component interaction or platform-specific behavior
- Dependencies: Real system calls, D-Bus daemon
- Approach: Slower but tests real behavior
- Example: `tests/integration/test_macos.py` (runs on macOS only)

**D-Bus Integration Tests (in `tests/integration/test_dbus/`):**
- Scope: D-Bus adapters against real services
- Setup: Custom D-Bus daemon in subprocess with test services
- Approach: Real D-Bus communication in isolated environment
- Example: `tests/integration/test_dbus/test_dbus_adapters.py`

## Common Patterns

**Async Testing (Thread-Based):**
```python
def test_decorator_syntax_thread_safety():
    exit_event = threading.Event()

    @keep.running(methods=["MethodForThreadSafety"])
    def long_running_function():
        exit_event.wait(WAIT_TIMEOUT)  # Wait until test is done

    threads = []
    for _ in range(3):
        thread = threading.Thread(target=long_running_function)
        thread.start()
        threads.append(thread)

    # Cleanup
    exit_event.set()
    for thread in threads:
        thread.join()

    # Assert
    assert len(MethodForThreadSafety.used_cookies) == 3
    assert len(set(MethodForThreadSafety.used_cookies)) == 3
```

**Error Testing:**
```python
def test_method_without_name(self):
    """Methods used for activation must have a name. If not, there should
    be a ValueError raised"""

    method = type("MyMethod", (Method,), {})()
    with pytest.raises(ValueError, match=re.escape("Methods without a name...")):
        activate_method(method)
```

**Parametrized Tests:**
```python
@pytest.mark.parametrize("current_platform,expected", [
    (IdentifiedPlatformType.LINUX, True),
    (IdentifiedPlatformType.WINDOWS, False),
])
def test_platform_specific(current_platform, expected, monkeypatch):
    set_current_platform(monkeypatch, current_platform)
    # ... test logic
```

**Mark Usage:**
```python
@pytest.mark.usefixtures("set_current_platform_to_linux")
def test_on_linux_only():
    """Test requiring Linux platform"""
    pass

@pytest.mark.usefixtures("empty_method_registry", "provide_methods_a_f")
def test_with_registered_methods():
    """Test with specific methods registered"""
    pass

@pytest.mark.skipif(sys.platform != "linux", reason="D-Bus is Linux-only")
def test_dbus_specific():
    """Skip this test on non-Linux platforms"""
    pass
```

**Exception Context Testing:**
```python
def test_method_caniuse_fails(self):
    # Case 1: Fail by returning False from caniuse
    method = get_test_method_class(caniuse=False)()
    res, heartbeat = activate_method(method)
    assert res.success is False
    assert res.failure_stage == StageName.REQUIREMENTS
    assert res.failure_reason == ""
    assert heartbeat is None

    # Case 2: Fail by returning error reason from caniuse
    method2 = get_test_method_class(caniuse="missing dependency")()
    res2, heartbeat2 = activate_method(method2)
    assert res2.success is False
    assert res2.failure_reason == "missing dependency"
```

## Testing Best Practices

**Do:**
- Use fixtures for shared test data and setup
- Test specific functions/methods first, not full suite
- Include descriptive docstrings on test methods
- Use `pytest.raises()` context manager for exception testing
- Group related tests in classes (`TestClassName`)
- Use monkeypatch for mocking in pytest
- Create inline test helper classes for clarity
- Mark platform/version-specific tests appropriately

**Don't:**
- Don't use `print()` for debugging; use logging or pytest capture
- Don't modify global state without cleanup via fixtures
- Don't test implementation details, test behavior
- Don't add comments where test names/docstrings are clear
- Don't skip cleanup (use fixtures with proper teardown)

---

*Testing analysis: 2026-02-19*
