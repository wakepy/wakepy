# Architecture

**Analysis Date:** 2026-03-22 (updated from 2026-02-19)

## Pattern Overview

**Overall:** Plugin-based method registry with context manager/decorator-driven mode activation.

**Key Characteristics:**
- Mode-Method separation: Modes represent user intent (keep.running, keep.presenting); Methods implement platform-specific solutions
- Automatic method discovery via class registration during module import
- Platform-agnostic user API backed by platform-specific implementations
- Result objects provide detailed activation/failure diagnostics
- Thread-safe mode tracking using ContextVar for current mode and locks for global modes

## Layers

**User API Layer:**
- Purpose: Public interface for end users
- Location: `src/wakepy/modes/keep.py`, `src/wakepy/__init__.py`
- Contains: Factory functions (keep.running, keep.presenting) that create Mode instances
- Depends on: Mode, constants, D-Bus adapters
- Used by: User code (scripts, applications)

**Core Mode/Method Layer:**
- Purpose: Manages mode activation lifecycle and method orchestration
- Location: `src/wakepy/core/mode.py`, `src/wakepy/core/method.py`
- Contains: Mode class (context manager/decorator), Method base class, activation state management
- Depends on: Registry, prioritization, platform detection, D-Bus
- Used by: User API layer, method implementations

**Method Registry & Discovery:**
- Purpose: Automatic Method class registration and lookup
- Location: `src/wakepy/core/registry.py`
- Contains: _method_registry (global dict), register_method, get_method, get_methods_for_mode
- Depends on: Constants (ModeName)
- Used by: Method.__init_subclass__, Mode initialization

**Method Prioritization:**
- Purpose: Order methods by platform support and user preferences
- Location: `src/wakepy/core/prioritization.py`
- Contains: order_methods_by_priority function, priority group sorting logic
- Depends on: Platform detection
- Used by: Mode activation flow

**Platform Detection:**
- Purpose: Identify current platform (Windows, Linux, macOS, FreeBSD, Unknown)
- Location: `src/wakepy/core/platform.py`
- Contains: get_current_platform, get_platform_supported, platform constants
- Depends on: Constants
- Used by: Registry filtering, Method platform checks, prioritization

**Method Implementations:**
- Purpose: Platform-specific/DE-specific mode activation
- Location: `src/wakepy/methods/{windows,macos,gnome,freedesktop}.py`, `src/wakepy/methods/_testing.py`
- Contains: Method subclasses (e.g., WindowsSetThreadExecutionState, FreedesktopInhibitor)
- Depends on: Method base class, D-Bus abstractions, platform constants
- Used by: Mode activation logic

**D-Bus Abstraction:**
- Purpose: Decouple D-Bus implementation from Method code
- Location: `src/wakepy/core/dbus.py`, `src/wakepy/dbus_adapters/jeepney.py`
- Contains: DBusAdapter base class, DBusAddress, DBusMethod, DBusMethodCall, concrete Jeepney adapter
- Depends on: Constants
- Used by: Freedesktop/GNOME methods

**Activation Result Layer:**
- Purpose: Capture and expose method activation outcomes
- Location: `src/wakepy/core/activationresult.py`
- Contains: ActivationResult, MethodActivationResult, ProbingResults dataclasses
- Depends on: Constants (StageName)
- Used by: Mode.result attribute, diagnostic methods

**CLI Layer:**
- Purpose: Command-line interface for mode activation
- Location: `src/wakepy/__main__.py`
- Contains: Argument parsing, mode selection, spinner animation, user feedback
- Depends on: Mode, ActivationResult, platform detection
- Used by: Terminal invocation (python -m wakepy or wakepy command)

## Data Flow

**Mode Activation Flow:**

1. User calls keep.running() or keep.presenting() factory function
2. Factory creates _ModeParams via create_mode_params()
3. Mode.__init__() receives params, gets methods for mode from registry
4. Mode.__enter__() (or decorator call, or explicit `mode.enter()`) triggers `enter()`
5. `enter()` acquires `self._lock`, then calls `_enter()`:
   - get_selected_methods() → filters by use_only/omit
   - order_methods_by_priority() → sorts by platform + user priority
   - For each Method: `_activate()` calls activate_method() / enter_mode()
6. First successful Method activation stops iteration
7. ActivationResult created with all MethodActivationResult records
8. on_fail handler triggered if activation fails
9. Mode.active set to True/False/None (None = not yet entered or already exited)
10. Mode.__exit__() (or explicit `mode.exit()`) calls `exit()` → deactivate_method()
11. Deactivate calls exit_mode() on active Method

**Explicit enter/exit pattern (v2.0.0+):**
```python
mode = keep.running()
try:
    mode.enter()          # also accepts if_already_entered="warn"|"pass"|"error"
    # event loop / GUI mainloop
finally:
    mode.exit()           # always safe, even if enter() was never called or failed
```

**State Management:**

- Per-thread/context: Mode instance stored in ContextVar(_current_mode)
- Global: All Mode instances tracked in _all_modes list (thread-safe via _mode_lock)
- Per-Mode: ActivationResult stores all MethodActivationResult records
- Per-Method: Instance holds state (e.g., inhibit_cookie for D-Bus methods, _release event for Windows)

**Method Selection Chain:**

1. Registry lookup: get_methods_for_mode(mode_name) → returns all Method classes for mode
2. User filtering: select_methods(use_only=..., omit=...) → narrows list
3. Platform filtering: Only methods with matching supported_platforms stay
4. Priority ordering: order_methods_by_priority(methods_list, methods_priority)
5. Activation attempt: Sequential activation with failure fallthrough

## Key Abstractions

**Mode:**
- Purpose: Represents a user-requested system state (sleep prevention with/without screen)
- Examples: `src/wakepy/core/mode.py` Mode class
- Pattern: Context manager + decorator + explicit `enter()`/`exit()` API
- State: `active` is three-state: `True` (active), `False` (activation failed), `None` (not yet entered or already exited)

**Method:**
- Purpose: Implements a mode on a specific platform or with specific technology
- Examples: `src/wakepy/methods/windows.py` WindowsSetThreadExecutionState, `src/wakepy/methods/freedesktop.py` FreedesktopInhibitor
- Pattern: ABC with enter_mode()/exit_mode() lifecycle, registration on subclass creation
- State: dbus_adapter, heartbeat, platform support metadata

**ActivationResult:**
- Purpose: Immutable summary of which methods succeeded/failed and why
- Examples: `src/wakepy/core/activationresult.py` ActivationResult, ProbingResults
- Pattern: Dataclass with query methods (list_methods, query, get_failure_text)
- Used: Accessible as Mode.result for diagnostics

**DBusAdapter:**
- Purpose: Abstract D-Bus communication, allow different backends (Jeepney, etc.)
- Examples: `src/wakepy/core/dbus.py` DBusAdapter base, `src/wakepy/dbus_adapters/jeepney.py` JeepneyDBusAdapter
- Pattern: Pluggable via Mode dbus_adapter parameter
- Used by: Methods that need D-Bus (all Freedesktop-based)

## Entry Points

**Library Entry (Public API):**
- Location: `src/wakepy/__init__.py`
- Triggers: User imports from wakepy (Mode, keep, ActivationError, etc.)
- Responsibilities: Re-export public API, lazy-load optional adapters (JeepneyDBusAdapter)

**Mode Factory Functions:**
- Location: `src/wakepy/modes/keep.py`
- Triggers: keep.running(), keep.presenting() calls
- Responsibilities: Parse user arguments (methods, omit, methods_priority, on_fail, dbus_adapter), create Mode

**CLI Entry:**
- Location: `src/wakepy/__main__.py`
- Triggers: python -m wakepy [args] or wakepy CLI command
- Responsibilities: Parse CLI args, select mode, activate with spinners, handle exit

**Method Registration:**
- Location: All `src/wakepy/methods/*.py` module imports
- Triggers: Method subclass definition (via __init_subclass__)
- Responsibilities: Auto-register each Method subclass to registry by mode_name

## Error Handling

**Strategy:** Layered exception handling with result-based diagnostics.

**Patterns:**

- **Activation Failures:** Methods raise exceptions in enter_mode(); caught by Mode.activate(), recorded in MethodActivationResult, aggregated into ActivationResult
- **On-Fail Actions:** Based on Mode.on_fail parameter:
  - "error" → raises ActivationError
  - "warn" → issues ActivationWarning
  - "pass" → silent failure
  - Callable → invoked with ActivationResult for custom handling
- **Platform Mismatch:** Silent (continue to next method) unless UNKNOWN platform
- **DBus Failures:** DBusCallError with detailed message about service/method/interface
- **Validation Errors:** UnrecognizedMethodNames when user specifies unknown method in use_only/omit

## Cross-Cutting Concerns

**Logging:** Uses Python logging module (getLogger(__name__) in each module), debug-level activation flow tracking

**Validation:**
- supported_platforms check in Method._check_supported_platforms()
- caniuse() method in Method subclasses for runtime checks
- User input validation for methods/omit/methods_priority parameters

**Authentication:**
- D-Bus methods implicit (SessionBus/SystemBus connection handled by DBusAdapter)
- No user auth; operates with current user's privileges

**Thread Safety:**
- ContextVar for per-thread current mode tracking
- Lock (`_mode_lock`) protecting `_all_modes` global list (accessed via `with _mode_lock:`)
- Per-instance `_lock = threading.Lock()` guards `enter()`/`exit()` against concurrent calls
- `ThreadSafetyWarning` and `_thread_check()` removed in v2.0.0 (no longer warn on cross-thread use)
- Windows methods use separate inhibitor threads to isolate SetThreadExecutionState flags

**Multi-threading Support:**
- Context managers create new Mode instance per thread (decorator pattern)
- Each thread has independent ContextVar, preventing cross-thread contamination
- `global_modes()` safe for multi-thread query
- `_all_modes` managed by `enter()`/`exit()` (not `_set_current_mode`/`_unset_current_mode`)
