# Codebase Concerns

**Analysis Date:** 2026-02-19

## Tech Debt

**Incomplete Heartbeat Implementation:**
- Issue: The Heartbeat class is a stub implementation that always returns True. Real periodic heartbeat functionality is not implemented.
- Files: `src/wakepy/core/heartbeat.py`
- Impact: Modes cannot maintain activation state with periodic calls. Methods that require continuous heartbeat signals (like some D-Bus methods) cannot properly sustain their state.
- Fix approach: Implement actual threading-based heartbeat mechanism. See GitHub issue #109 for design details. Should accept heartbeat interval configuration and execute method-specific heartbeat calls on schedule.

**Duplicate Method Selection Logic:**
- Issue: In `get_selected_methods()` function, `select_methods()` is called twice (lines 184 and 197 in mode.py) - once inside a try/except, then again unconditionally. The first call's result is discarded.
- Files: `src/wakepy/core/mode.py` (lines 177-212)
- Impact: Unnecessary computation on every mode activation. If methods are numerous this could cause performance degradation.
- Fix approach: Remove the redundant call on line 197. Keep only the first call inside the try/except block that handles UnrecognizedMethodNames.

**Incomplete Method Arguments Feature:**
- Issue: Method class has commented placeholder for `method_kwargs` dictionary (lines 125-136, 143-144 in method.py). Feature is blocked and waiting for GitHub issue #256.
- Files: `src/wakepy/core/method.py`
- Impact: Methods cannot accept runtime configuration arguments. All behavior must be hardcoded in Method subclasses.
- Fix approach: Implement method_kwargs system as part of issue #256 resolution. Requires updating __init__ signature handling and documentation.

## Known Issues with Mitigations

**Thread Safety Warning Not Enforced:**
- Issue: ThreadSafetyWarning is issued if Mode is used across threads (line 931 in mode.py), but usage is still allowed to proceed. No hard safety guarantees.
- Files: `src/wakepy/core/mode.py` (lines 923-932)
- Impact: Users can accidentally share Mode instances across threads, causing undefined behavior. ContextVar assumes thread-safety but actual locking may not be sufficient.
- Current mitigation: Warning is logged and printed. Context separation via ContextVar reduces cross-thread contamination.
- Recommendations: Consider making this a hard error instead of warning, or provide thread-safe Mode wrapper class. Document thread requirements clearly in user API.

**Windows Thread Timeout Edge Case:**
- Issue: If SetThreadExecutionState worker thread timeout is too small, queue may contain multiple responses, triggering warning (line 85-92 in windows.py).
- Files: `src/wakepy/methods/windows.py` (lines 85-92)
- Trigger: Setting `_release_event_timeout` to very low values in tests
- Workaround: Increase timeout values or avoid manipulating private _release_event_timeout attribute
- Recommendations: Make timeout configurable via environment variable or class parameter for robustness.

**Platform Detection for Unknown Systems:**
- Issue: When current platform is UNKNOWN, platform support checks do not fail activation (lines 870-876 in mode.py). Methods proceed even if unsupported.
- Files: `src/wakepy/core/mode.py`, `src/wakepy/core/method.py` (lines 111-113)
- Impact: On exotic or unidentified platforms, activation may silently fail without informing user of platform mismatch.
- Recommendations: Log explicit warning when platform is UNKNOWN. Provide diagnostic info in activation result.

## Performance Bottlenecks

**Lock Contention in Global Mode Registry:**
- Problem: All threads acquiring/releasing `_mode_lock` for appending/removing modes (lines 719-756 in mode.py). Uses manual acquire/release pattern instead of context manager.
- Files: `src/wakepy/core/mode.py` (lines 319-345, 728-756)
- Cause: Manual lock management with try/finally, repeated lock/unlock for multiple operations
- Improvement path:
  1. Convert to `with _mode_lock:` context manager syntax (cleaner, less error-prone)
  2. Batch operations: combine _set_current_mode and _unset_current_mode operations to reduce lock acquisitions
  3. Consider RWLock (read-write lock) if read operations (global_modes, modecount) are more frequent than writes

**D-Bus Connection Reuse Not Optimized:**
- Problem: DBusAdapter caches connection per instance, but new connections opened/closed frequently
- Files: `src/wakepy/dbus_adapters/jeepney.py` (lines 34-72)
- Cause: DBusAdapter.process() calls _get_connection() which may open new connection each time
- Improvement path:
  1. Profile D-Bus call frequency to understand cost
  2. Consider connection pooling for rapid successive calls
  3. Cache adapter instance at module level rather than per-Method

**No Resource Cleanup on Activation Failure:**
- Problem: If method activation fails partway through (during heartbeat setup), resources may not be freed
- Files: `src/wakepy/core/method.py` (activate_method function around line 657-703)
- Cause: Method.enter_mode() should clean up on error, but no guarantee if heartbeat.start() fails
- Improvement path: Wrap heartbeat startup in try/except. Ensure deactivate is called on failure.

## Fragile Areas

**Windows SetThreadExecutionState Threading Model:**
- Files: `src/wakepy/methods/windows.py`
- Why fragile: Complex multi-threaded coordination with Queue-based IPC, timeout-based waits, and Event signaling. Thread lifecycle (start/join/timeout) has multiple failure modes.
- Safe modification:
  1. Only change timeout values via class attributes, never in enter_mode/exit_mode
  2. Add comprehensive logging around thread state transitions
  3. Test with multiple concurrent Mode instances to catch race conditions
  4. Never remove the timeout parameters - they prevent indefinite hangs
- Test coverage: Good coverage exists (tests/unit/test_methods/) but should add stress tests with rapid activation/deactivation cycles

**D-Bus Adapter Initialization Path:**
- Files: `src/wakepy/core/dbus.py` (lines 361-376)
- Why fragile: get_dbus_adapter() catches broad Exception to handle missing imports and failed connections. Silent fallback to None if any error occurs (lines 361-370).
- Safe modification:
  1. Log specific exception types that are caught
  2. Distinguish "library not available" from "connection failed" for better diagnostics
  3. Add unit tests for each failure mode separately
- Test coverage: Need tests for each adapter type missing vs connection failure

**Mode Method Selection with Empty/Invalid Inputs:**
- Files: `src/wakepy/core/mode.py` (lines 177-212)
- Why fragile: Multiple validation steps (UnrecognizedMethodNames exception handling) with complex error message formatting
- Safe modification:
  1. Add explicit validation of use_only/omit parameters before processing
  2. Test with edge cases: empty methods list, all methods filtered out, methods with special characters
  3. Ensure error messages are consistent and actionable
- Test coverage: Good coverage exists but add explicit edge case tests

## Scaling Limits

**Global Mode Registry Memory:**
- Current capacity: Unbounded list `_all_modes` grows with each active Mode
- Limit: If thousands of Modes created in same process, list becomes large. Lock contention increases with number of threads.
- Scaling path:
  1. For typical usage (few concurrent modes per process), current implementation is fine
  2. For applications creating Mode instances dynamically over lifetime, consider cleanup mechanism
  3. Weak references could help: use WeakSet instead of List to auto-remove garbage-collected modes
  4. Monitor with `modecount()` to detect accumulation

**D-Bus Session Bus Timeouts:**
- Current capacity: Hard-coded 2 second timeout in JeepneyDBusAdapter
- Limit: On slow systems or busy D-Bus daemons, 2s timeout may be insufficient
- Scaling path:
  1. Make timeout configurable per DBusAdapter instance
  2. Implement exponential backoff retry for transient failures
  3. Add diagnostic metrics to track D-Bus call latencies

## Dependencies at Risk

**Jeepney D-Bus Library:**
- Risk: Optional dependency. If not installed, D-Bus methods fail silently with no clear error message.
- Impact: GNOME, KDE, Freedesktop methods cannot work without jeepney. User sees "activation failed" without diagnosis.
- Migration plan:
  1. Consider alternative: dbus-python (deprecated but more stable) or python-dbus-next
  2. Add explicit import-time check with helpful error message when jeepney is unavailable
  3. Document jeepney as required for Linux/BSD systems in README

**Ctypes Windows API (not a dependency but platform coupling):**
- Risk: kernel32.dll behavior varies across Windows versions. SetThreadExecutionState flags interpretation may change.
- Impact: If Microsoft changes kernel32 behavior in future Windows versions, inhibition may silently fail.
- Recommendations:
  1. Add Windows version detection and version-specific flag handling if needed
  2. Add test on multiple Windows versions (WinServer 2022, Win11, Win10)
  3. Consider using ctypes.windll.kernel32 error codes for better diagnostics

## Test Coverage Gaps

**D-Bus Adapter Failure Modes:**
- What's not tested: Connection failures (bus unavailable), timeout behavior, malformed responses
- Files: `src/wakepy/dbus_adapters/jeepney.py`, `src/wakepy/core/dbus.py`
- Risk: D-Bus methods fail in ways not caught by existing tests. Freedesktop/GNOME methods may not handle connection issues gracefully.
- Priority: High - D-Bus failures are common in desktop environments

**Heartbeat Lifecycle:**
- What's not tested: heartbeat.start() and heartbeat.stop() actual behavior (both are stubs)
- Files: `src/wakepy/core/heartbeat.py`
- Risk: Once heartbeat is implemented, issues may hide for months before users encounter them in real activation scenarios
- Priority: High - heartbeat must be implemented and tested thoroughly before use

**Cross-Platform Mode Switching:**
- What's not tested: Rapid activation/deactivation of different mode types on same system
- Files: `src/wakepy/core/mode.py` (Mode class entire activation lifecycle)
- Risk: ContextVar and threading issues may only manifest under stress
- Priority: Medium - add stress tests with 10+ rapid mode cycles

**Windows Thread Queue Exhaustion:**
- What's not tested: Scenarios where _queue_from_thread.get() blocks (timeout exceeded)
- Files: `src/wakepy/methods/windows.py`
- Risk: If worker thread dies unexpectedly, blocking forever on queue.get() (line 107)
- Priority: Medium - add test for thread death scenarios

**Missing Validation Tests:**
- What's not tested: Invalid dbus_adapter parameter types, out-of-range timeout values
- Files: `src/wakepy/core/mode.py` (__init__ parameter validation)
- Risk: Bad parameters silently ignored or cause cryptic errors
- Priority: Low-Medium - add parameter validation tests

---

*Concerns audit: 2026-02-19*
