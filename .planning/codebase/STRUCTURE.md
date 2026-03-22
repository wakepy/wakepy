# Codebase Structure

**Analysis Date:** 2026-02-19

## Directory Layout

```
wakepy/
├── src/wakepy/                    # Main package
│   ├── __init__.py                # Public API exports, lazy loader
│   ├── __main__.py                # CLI entry point
│   ├── _version.py                # Version info (generated)
│   ├── core/                      # Core mode/method infrastructure
│   │   ├── __init__.py            # Core API re-exports
│   │   ├── activationresult.py    # ActivationResult, MethodActivationResult, ProbingResults
│   │   ├── constants.py           # Enums: IdentifiedPlatformType, PlatformType, ModeName, BusType, StageName
│   │   ├── dbus.py                # D-Bus abstractions: DBusAdapter, DBusAddress, DBusMethod, DBusMethodCall
│   │   ├── heartbeat.py           # Heartbeat mechanism (placeholder)
│   │   ├── method.py              # Method base class (703 lines) and MethodOutcome enum
│   │   ├── mode.py                # Mode class (925 lines), context manager/decorator logic
│   │   ├── platform.py            # Platform detection: get_current_platform, PlatformType mapping
│   │   ├── prioritization.py      # Method prioritization logic
│   │   ├── registry.py            # Method registration/discovery
│   │   ├── strenum.py             # String Enum utility base
│   │   └── utils.py               # Utility functions (env var checking, etc.)
│   ├── dbus_adapters/             # D-Bus implementation plugs
│   │   ├── __init__.py            # Lazy loading interface
│   │   └── jeepney.py             # Jeepney D-Bus adapter
│   ├── methods/                   # Platform-specific method implementations
│   │   ├── __init__.py            # Imports all method modules (triggers registration)
│   │   ├── _testing.py            # WakepyFakeSuccess (test method)
│   │   ├── freedesktop.py         # Freedesktop.org D-Bus methods (PowerManagement, ScreenSaver)
│   │   ├── gnome.py               # GNOME D-Bus methods (SessionManager)
│   │   ├── macos.py               # macOS method (caffeinate)
│   │   └── windows.py             # Windows method (SetThreadExecutionState)
│   └── modes/                     # Mode factory functions
│       ├── __init__.py            # Empty (re-export happens at package level)
│       └── keep.py                # keep.running(), keep.presenting() factories (273 lines)
├── tests/                         # Test suite
│   ├── conftest.py                # Global pytest fixtures
│   ├── helpers.py                 # Test utilities
│   ├── unit/                      # Unit tests (mocked)
│   │   ├── conftest.py            # Unit test fixtures
│   │   ├── test_keep.py           # Tests for keep.running/keep.presenting
│   │   ├── test_core/             # Core module tests
│   │   │   ├── test_dbus.py       # D-Bus abstractions
│   │   │   ├── test_platform.py   # Platform detection
│   │   │   ├── test_strenum.py    # String enum utility
│   │   │   └── test_method/       # Method class tests
│   │   │       ├── test_method.py # Method base class
│   │   │       └── test_activation.py  # Activation result handling
│   │   ├── test_methods/          # Method implementation tests
│   │   │   ├── test_freedesktop.py
│   │   │   ├── test_gnome.py
│   │   │   ├── test_macos.py
│   │   │   └── test_windows.py
│   │   └── test_e2e/              # End-to-end tests
│   │       └── test_in_async_tasks.py  # Async context tests
│   └── integration/               # Integration tests (real D-Bus, system Python)
│       ├── test_dbus/             # D-Bus integration tests
│       │   ├── conftest.py        # D-Bus test fixtures
│       │   ├── dbus_service.py    # Mock D-Bus service
│       │   └── test_dbus_adapters.py
│       ├── test_systempython/     # Tests with system Python interpreter
│       └── test_macos.py          # macOS integration tests
├── docs/                          # Sphinx documentation
│   ├── source/                    # .rst source files
│   └── build/                     # Rendered HTML (generated)
├── pyproject.toml                 # Build config, dependencies, tool settings
├── uv.lock                        # uv dependency lock file
├── .justfile                      # Just commands: format, check, docs, test, build
├── AGENTS.md                      # Project instructions for AI agents
├── README.md                      # Project overview
├── CONTRIBUTING.md                # Contribution guidelines
└── .planning/codebase/            # GSD planning documents (this directory)
```

## Directory Purposes

**src/wakepy/:**
- Purpose: Main package containing all source code
- Contains: Core logic, methods, modes, public API
- Key files: `__init__.py` (exports), `__main__.py` (CLI)

**src/wakepy/core/:**
- Purpose: Core infrastructure for modes and methods
- Contains: Mode lifecycle, Method base class, registry, activation results, platform detection, D-Bus abstractions
- Key files: `mode.py` (925 lines, main orchestration), `method.py` (703 lines, base class)

**src/wakepy/methods/:**
- Purpose: Platform-specific and technology-specific method implementations
- Contains: Windows (SetThreadExecutionState), macOS (caffeinate), Freedesktop (PowerManagement, ScreenSaver), GNOME (SessionManager), testing stub
- Key files: All module files (windows.py, macos.py, freedesktop.py, gnome.py)
- Auto-registration: `__init__.py` imports all modules, triggering Method.__init_subclass__

**src/wakepy/modes/:**
- Purpose: User-facing factory functions for creating modes
- Contains: keep.running(), keep.presenting() overloads and implementations
- Key files: `keep.py` (273 lines)

**src/wakepy/dbus_adapters/:**
- Purpose: Pluggable D-Bus implementations
- Contains: Abstract DBusAdapter, concrete Jeepney adapter
- Key files: `jeepney.py` (Jeepney library integration)

**tests/unit/:**
- Purpose: Mocked unit tests (no external dependencies)
- Structure: Mirrors src/ directory structure with test_* prefix
- Key files: `test_core/test_method/` (Method behavior), `test_methods/` (each method implementation)

**tests/integration/:**
- Purpose: Integration tests with real D-Bus, system interpreters
- Structure: Separate from unit tests; requires Linux/D-Bus available
- Key files: `test_dbus/` (real D-Bus operations), `test_systempython/` (subprocess tests)

## Key File Locations

**Entry Points:**

- `src/wakepy/__init__.py`: Package initialization, public API exports (Mode, keep, exceptions)
- `src/wakepy/__main__.py`: CLI entry (python -m wakepy [args])
- `src/wakepy/modes/keep.py`: User API (keep.running(), keep.presenting() factory functions)

**Configuration:**

- `pyproject.toml`: Build system (hatch), dependencies, tool config (ruff, mypy, pytest, sphinx)
- `uv.lock`: Dependency versions (uv package manager)
- `.justfile`: Development commands (format, check, docs, test, build)

**Core Logic:**

- `src/wakepy/core/mode.py`: Mode class (context manager, decorator, lifecycle)
- `src/wakepy/core/method.py`: Method base class (ABC for platform implementations)
- `src/wakepy/core/registry.py`: Method discovery (_method_registry, register_method, get_methods_for_mode)
- `src/wakepy/core/activationresult.py`: Diagnostic classes (ActivationResult, MethodActivationResult)
- `src/wakepy/core/platform.py`: Platform detection (get_current_platform, CURRENT_PLATFORM singleton)
- `src/wakepy/core/constants.py`: Enums (IdentifiedPlatformType, PlatformType, ModeName, BusType, StageName)

**Method Implementations:**

- `src/wakepy/methods/windows.py`: WindowsSetThreadExecutionState (keep.running, keep.presenting)
- `src/wakepy/methods/macos.py`: MacOSCaffeinate (keep.running, keep.presenting)
- `src/wakepy/methods/freedesktop.py`: FreedesktopInhibitor subclasses (PowerManagement, ScreenSaver, Systemd)
- `src/wakepy/methods/gnome.py`: GNOMESessionManager (keep.running, keep.presenting)

**Testing:**

- `tests/conftest.py`: Global pytest fixtures (fixtures available to all tests)
- `tests/unit/conftest.py`: Unit test-specific fixtures
- `tests/unit/test_core/test_method/test_activation.py`: Mode activation tests
- `tests/integration/test_dbus/` : Real D-Bus integration tests

## Naming Conventions

**Files:**

- `*.py`: Python source files
- `test_*.py`: Test modules (pytest will discover these)
- `conftest.py`: Pytest configuration files (special name, auto-discovered)
- Module names: lowercase with underscores (e.g., `activationresult.py`, `prioritization.py`)
- Method files match technology names (e.g., `windows.py`, `freedesktop.py`)

**Directories:**

- `src/wakepy/core/`: Core infrastructure
- `src/wakepy/methods/`: Method implementations
- `src/wakepy/modes/`: Mode factories
- `tests/unit/`: Mocked unit tests
- `tests/integration/`: Integration tests
- `test_*/*.py`: Test module structure mirrors source structure

**Classes:**

- PascalCase (e.g., Mode, Method, ActivationResult, MethodInfo)
- Method subclasses: [Platform][Technology]MethodName (e.g., WindowsSetThreadExecutionState, GNOMESessionManager, FreedesktopPowerManagement)
- Exceptions: PascalCase ending in "Error" or "Warning" (e.g., ActivationError, DBusCallError, ActivationWarning)

**Functions:**

- snake_case (e.g., get_current_platform, create_mode_params, order_methods_by_priority)
- Public functions: Exported in __init__.py or module __all__
- Private functions: Leading underscore (e.g., _get_success_method, _sort_methods_to_priority_groups)

**Constants:**

- SCREAMING_SNAKE_CASE (e.g., ES_CONTINUOUS, WAKEPY_FAKE_SUCCESS_METHOD, FALSY_ENV_VAR_VALUES)
- Module-level enums: PascalCase class, members SCREAMING_SNAKE_CASE (IdentifiedPlatformType.WINDOWS, StageName.ACTIVATION)

## Where to Add New Code

**New Method (Platform Implementation):**

1. Create file: `src/wakepy/methods/{technology_name}.py`
2. Import: `from wakepy.core import Method, ModeName, PlatformType`
3. Subclass Method, set:
   - `mode_name`: "keep.running" or "keep.presenting"
   - `supported_platforms`: Tuple of PlatformType values
   - `name`: Unique method name (registered in registry)
   - Implement: `caniuse()`, `enter_mode()`, `exit_mode()` methods
4. Register: Add import in `src/wakepy/methods/__init__.py`
5. Test: Create `tests/unit/test_methods/test_{technology_name}.py`

**New Mode:**

1. Define factory function in `src/wakepy/modes/keep.py` or new file in `src/wakepy/modes/`
2. Return Mode instance created via `Mode(create_mode_params(ModeName.YOUR_MODE, ...))`
3. Add ModeName enum value in `src/wakepy/core/constants.py`
4. Export in `src/wakepy/__init__.py`
5. Create methods implementing the mode (see "New Method" above)

**Utilities:**

- Shared helpers: `src/wakepy/core/utils.py`
- Constants: `src/wakepy/core/constants.py`
- Test fixtures: `tests/conftest.py` (global) or `tests/unit/conftest.py` (unit tests only)

**Tests:**

- Unit tests: Mirror `src/` structure under `tests/unit/`, use `conftest.py` fixtures
- Integration tests: Place in `tests/integration/` if requiring real external resources
- File naming: `test_*.py` for pytest discovery

## Special Directories

**src/wakepy/core/__pycache__/:**
- Purpose: Python bytecode cache
- Generated: Yes (automatically by Python)
- Committed: No (.gitignore)

**tests/integration/test_dbus/:**
- Purpose: Real D-Bus integration (requires D-Bus daemon running)
- Special: Contains `dbus_service.py` (mock D-Bus service for testing)
- Committed: Yes, but skipped if D-Bus unavailable

**.planning/codebase/:**
- Purpose: GSD codebase analysis documents
- Generated: Yes (by /gsd:map-codebase command)
- Committed: Yes (planning artifacts)

**htmlcov/, .coverage:**
- Purpose: Test coverage reports
- Generated: Yes (pytest-cov plugin)
- Committed: No (.gitignore)

**.mypy_cache/, .pytest_cache/, .ruff_cache/:**
- Purpose: Tool caches (type checking, testing, linting)
- Generated: Yes (mypy, pytest, ruff)
- Committed: No (.gitignore)

## Import Patterns

**Public API (from src/wakepy/__init__.py):**

```python
from wakepy import (
    Mode, ActivationError, ActivationWarning, ActivationResult,
    current_mode, global_modes, modecount,
    keep,  # modes.keep module
    ModeName, PlatformType, Method, MethodInfo,
    JeepneyDBusAdapter,  # Lazy-loaded
)
```

**Core Imports (internal):**

```python
from wakepy.core import Mode, Method, ActivationResult
from wakepy.core.constants import ModeName, PlatformType, StageName
from wakepy.core.registry import get_methods_for_mode, register_method
from wakepy.core.prioritization import order_methods_by_priority
from wakepy.core.platform import CURRENT_PLATFORM, get_platform_supported
from wakepy.core.dbus import DBusAdapter, DBusMethodCall, DBusAddress
```

**Method Implementation Pattern:**

```python
from wakepy.core import Method, ModeName, PlatformType
from wakepy.core.dbus import DBusMethodCall, DBusAddress

class MyMethod(Method):
    mode_name = ModeName.KEEP_RUNNING
    supported_platforms = (PlatformType.LINUX,)
    name = "my_method"

    def enter_mode(self) -> None:
        # Implementation
        pass
```

**Test Fixtures (pytest):**

```python
# In tests/conftest.py or tests/unit/conftest.py
@pytest.fixture
def mock_mode():
    return Mode(create_mode_params(ModeName.KEEP_RUNNING, ...))
```
