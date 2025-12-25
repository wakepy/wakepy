wakepy: Cross-platform Python tool for preventing system suspend via native OS/DE APIs. No persistent settings modified.

ARCHITECTURE:
- Modes (user API): keep.running (sleep prevention), keep.presenting (sleep+screen lock prevention)
- Methods: Platform implementations (Windows SetThreadExecutionState, macOS caffeinate, GNOME/Freedesktop D-Bus)
- Modes use context managers/decorators

KEY FILES:
src/wakepy/__init__.py - Public API exports
src/wakepy/__main__.py - CLI (375 lines)
src/wakepy/modes/keep.py - User API (273 lines)
src/wakepy/core/constants.py - Enums: IdentifiedPlatformType, PlatformType, ModeName, BusType, StageName
src/wakepy/core/mode.py - Mode logic (925 lines)
src/wakepy/core/method.py - Method base (703 lines)
src/wakepy/core/activationresult.py - ActivationResult, MethodActivationResult dataclasses
src/wakepy/core/registry.py - Method discovery/registration
src/wakepy/core/prioritization.py - Method selection logic
src/wakepy/core/platform.py - Platform detection
src/wakepy/core/dbus.py - D-Bus abstractions (370 lines)
src/wakepy/methods/{windows,macos,gnome,freedesktop}.py - Platform methods
src/wakepy/dbus_adapters/jeepney.py - Linux/BSD D-Bus adapter
pyproject.toml - Build config, dependencies, tool settings
tasks.py - Invoke commands: format, check, docs, test
tests/conftest.py - Global pytest fixtures
tests/unit/ - Mocked unit tests
tests/integration/ - Platform integration tests

REQUIREMENTS:
- Python 3.7+
- mypy strict mode (fully typed)
- 100% test coverage
- pytest with classes/fixtures
- Top-level functions before subfunctions
- Test specific functions first, not full suite

