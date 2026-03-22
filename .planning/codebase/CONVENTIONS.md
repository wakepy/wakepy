# Coding Conventions

**Analysis Date:** 2026-02-19

## Naming Patterns

**Files:**
- Module files use `snake_case`: `activationresult.py`, `constants.py`, `mode.py`
- Platform-specific method files: `windows.py`, `macos.py`, `gnome.py`, `freedesktop.py`
- Test files follow pattern: `test_*.py` or `*_test.py`
- Special test utilities: `conftest.py` for pytest fixtures, `testmethods.py` for test helpers

**Functions:**
- Lowercase with underscores: `activate_method()`, `get_platform_supported()`, `is_env_var_truthy()`
- Private functions prefixed with underscore: `_do_assert()`, `_check_supported_platforms()`
- Helper functions at module level before class definitions

**Variables:**
- Local variables: `snake_case` (e.g., `inhibit_cookie`, `method_inhibit`, `exit_event`)
- Constants: `UPPERCASE_WITH_UNDERSCORES` (e.g., `WAKEPY_FAKE_SUCCESS_METHOD`, `FALSY_ENV_VAR_VALUES`, `XDG_SESSION_DESKTOP`)
- Class variables use standard naming: `name`, `mode_name`, `supported_platforms` (matching enum member names)

**Types:**
- Classes: `PascalCase` (e.g., `Method`, `Mode`, `ActivationResult`, `DBusAdapter`)
- Enums: `PascalCase` (e.g., `IdentifiedPlatformType`, `PlatformType`, `ModeName`, `MethodOutcome`)
- Type aliases: `PascalCase` (e.g., `MethodCls = Type["Method"]`, `MethodOutcomeValue = Literal[...]`)
- Protocol/ABC classes: `PascalCase` (e.g., `Method`, `DBusAdapter`)

## Code Style

**Formatting:**
- Tool: `ruff` (with `fix = true` in `pyproject.toml`)
- Line length: 88 characters (Black standard)
- File imports at top in groups separated by blank lines
- Max docstring length: 79 characters

**Linting:**
- Tool: `ruff` with strict rules enabled
- Rules enforced: BLE, E, ERA, F, FIX (todo/fixme), FBT, I, S, W505, W291
- Special per-file rules:
  - Tests: S101 (assert), BLE (blind-except), FBT (boolean-trap) disabled
  - All pragmatic `# noqa` comments are acceptable with reasons

**Comments:**
- Mark pragma directives for platform/version-specific code:
  - `# pragma: no-cover-if-py-gte-38` - Skip coverage on Python >= 3.8
  - `# pragma: no-cover-if-py-lt-38` - Skip coverage on Python < 3.8
  - `# pragma: no-cover-if-no-dbus` - Skip on non-Linux (no D-Bus)
- These allow 100% coverage across all Python versions/platforms without false negatives

## Import Organization

**Order:**
1. `from __future__ import annotations` (always first for Python 3.7+ compatibility)
2. Standard library imports (`sys`, `os`, `typing`, `logging`, etc.) with `import` statements
3. Third-party imports (`pytest`, `jeepney`)
4. Local imports (relative or absolute `wakepy.*` imports)
5. `if typing.TYPE_CHECKING:` block for expensive/circular imports

**Path Aliases:**
- No path aliases configured; imports use absolute paths from package root
- Absolute imports preferred: `from wakepy.core import Method, Mode`
- Relative imports in tests: `from tests.unit.test_core.testmethods import TestMethod`

**Example from `src/wakepy/core/mode.py`:**
```python
from __future__ import annotations

import logging
import threading
import typing
import warnings
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import wraps

from wakepy.core.constants import WAKEPY_FAKE_SUCCESS_METHOD, StageName
from wakepy.core.platform import CURRENT_PLATFORM, get_platform_supported

from .activationresult import (
    ActivationResult,
    MethodActivationResult,
    ProbingResults,
)
from .dbus import DBusAdapter, get_dbus_adapter
from .heartbeat import Heartbeat
from .method import Method, MethodInfo, activate_method, deactivate_method
from .prioritization import order_methods_by_priority
from .registry import get_method, get_methods_for_mode
from .utils import is_env_var_truthy

if typing.TYPE_CHECKING:
    import sys
    from contextvars import Token
    from types import TracebackType
    from typing import Callable, List, Optional, Tuple, Type, Union
    # ... more TYPE_CHECKING imports
```

## Error Handling

**Patterns:**
- Custom exceptions inherit from standard library base classes:
  - `ActivationError(RuntimeError)` - For activation failures
  - `ActivationWarning(UserWarning)` - For activation warnings
  - `NoMethodsWarning(UserWarning)` - For missing methods
  - `ThreadSafetyWarning(UserWarning)` - For thread issues
  - `ModeExit(Exception)` - For exiting mode blocks
  - `DBusCallError(RuntimeError)` - For D-Bus failures
  - `ContextAlreadyEnteredError(RuntimeError)` - For mode state issues

- Raise with descriptive messages including context:
  ```python
  raise RuntimeError(f"Could not get inhibit cookie from {self.name}")
  raise ValueError("Methods without a name may not be used to activate modes!")
  ```

- Use `pytest.raises()` context manager in tests with specific exception matching:
  ```python
  with pytest.raises(ValueError, match=re.escape("Methods without a name...")):
      activate_method(method)
  ```

- Platform-specific exceptions caught by D-Bus adapters:
  ```python
  try:
      # D-Bus call
  except Exception:
      # Log and handle gracefully
  ```

## Logging

**Framework:** `logging` standard library

**Pattern:**
- Module-level logger: `logger = logging.getLogger(__name__)`
- Use debug level for:
  - Platform detection steps: `logger.debug("Platform debug info...")`
  - D-Bus adapter initialization: `logger.debug("Could not initialize DBusAdapter...")`
  - Environment variable checks: `logger.debug("'%s' is not set.", env_var_name)`
  - Method activation: `logger.debug("Got inhibit cookie from %s: %s", self.name, retval[0])`
- Use error level for:
  - Unexpected errors during execution: `logger.error("Error in creating platform debug info", exc_info=True)`
- Never use `print()` - always use logger

**Files with logging:**
- `src/wakepy/core/platform.py` - Platform detection debugging
- `src/wakepy/core/mode.py` - Mode lifecycle events
- `src/wakepy/core/dbus.py` - D-Bus adapter initialization
- `src/wakepy/core/utils.py` - Environment variable processing
- `src/wakepy/methods/freedesktop.py` - Freedesktop method operations

## Type Hints

**All code is fully typed with mypy strict mode:**
- `mypy` configured in `pyproject.toml` with strict settings: `check_untyped_defs = true`, `disallow_untyped_defs = true`, `disallow_any_generics = true`, `no_implicit_optional = true`
- Tests relax type requirements: `disallow_untyped_defs = false` for `tests.*`
- Every function parameter and return type annotated
- Use `Optional[X]` or `X | None` for nullable types
- Use `Union` for multiple types, or `|` operator (Python 3.10+)
- Use `TYPE_CHECKING` block to avoid circular imports:
  ```python
  if typing.TYPE_CHECKING:
      from typing import Optional, Tuple
      from wakepy.core import DBusAdapter
  ```

- For Python 3.7 compatibility, import `Literal` from `typing_extensions` when needed:
  ```python
  if sys.version_info < (3, 8):
      from typing_extensions import Literal
  else:
      from typing import Literal
  ```

**Example from `src/wakepy/core/method.py`:**
```python
def __init__(self, **kwargs: object) -> None:
    self.dbus_adapter = cast("DBusAdapter | None", kwargs.pop("dbus_adapter", None))
    self._check_supported_platforms()

def process_dbus_call(self, call: "DBusMethodCall") -> object:
    # Returns object or None
```

## Function Design

**Size:**
- Functions are kept relatively small and focused
- Complex logic is split into helper functions
- Examples:
  - `activate_method()` - ~50 lines
  - `try_enter_and_heartbeat()` - ~80 lines (complex heartbeat logic)
  - Helper functions like `has_enter()`, `has_exit()`, `has_heartbeat()` - 5-10 lines

**Parameters:**
- Keyword-only arguments preferred for clarity: `def __init__(self, **kwargs: object)`
- Methods typically have few parameters
- D-Bus methods pass arguments as dictionaries: `args=dict(application_name="wakepy", reason_for_inhibit="wakelock active")`
- Test methods accept fixtures: `def test_something(self, monkeypatch: pytest.MonkeyPatch, method1: Method)`

**Return Values:**
- Functions return tuples when multiple values needed:
  ```python
  res, heartbeat = activate_method(method)  # Returns (ActivationResult, Optional[Heartbeat])
  ```
- Dataclasses used for structured returns: `ActivationResult`, `MethodActivationResult`
- `None` explicitly returned for no-op branches: `return` or implicit None

## Module Design

**Exports:**
- Public API defined in `src/wakepy/__init__.py` and `src/wakepy/core/__init__.py`
- Use explicit `as` re-exports for clarity:
  ```python
  # In src/wakepy/core/__init__.py
  from .activationresult import ActivationResult as ActivationResult
  from .mode import Mode as Mode
  ```
- Allows consumers to do: `from wakepy import Mode, ActivationResult`

**Barrel Files:**
- `src/wakepy/__init__.py` - Main public API
- `src/wakepy/core/__init__.py` - Core module re-exports
- `src/wakepy/methods/__init__.py` - Method registration (empty, methods auto-register via `__init_subclass__`)
- `src/wakepy/dbus_adapters/__init__.py` - D-Bus adapters (empty, adapters auto-registered)

**Method Registration:**
- Methods automatically registered via `__init_subclass__()`:
  ```python
  def __init_subclass__(cls, **kwargs: object) -> None:
      register_method(cls)
      return super().__init_subclass__(**kwargs)
  ```
- No explicit imports needed; registration happens on class definition

## Docstring Style

**Format:** Google/NumPy-style docstrings with RST cross-references

**Example from `src/wakepy/core/mode.py`:**
```python
class ActivationError(RuntimeError):
    """Raised if the activation of a :class:`Mode` is not successful and the
    on-fail action is to raise an Exception. See the ``on_fail`` parameter of
    the ``Mode`` constructor. This is a subclass of `RuntimeError <https://\
    docs.python.org/3/library/exceptions.html#RuntimeError>`_.
    """

class Mode:
    """Methods are objects that are used to implement modes. The
    :class:`Method` class is an advanced topic in wakepy and typically users of
    wakepy do not need to interact with it directly. Instead, users will
    interact with the read-only :class:`MethodInfo` instances.

    The different phases of using a Method for activating / keeping /
    deactivating a Mode are:

    1) enter into a mode by calling :meth:`enter_mode`
    2) keep into a mode by calling :meth:`heartbeat` periodically
    3) exit from a mode by calling :meth:`exit_mode`
    """
```

**Attributes:**
- Class attributes documented with inline comments:
  ```python
  mode_name: ModeName | str
  """A name for the mode which the Method implements. The name can be
  basically anything, and is typically used when you create :class:`Mode`
  instances using the :meth:`Mode._from_name`."""
  ```

---

*Convention analysis: 2026-02-19*
