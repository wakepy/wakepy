# Lifecycle hooks: behavior → tests

Requirements: [issue #599](https://github.com/wakepy/wakepy/issues/599), [cleanup semantics](https://github.com/wakepy/wakepy/issues/599#issuecomment-4164433507), [state and repeated-call rules](https://github.com/wakepy/wakepy/issues/599#issuecomment-4164542622).

Test references below use exact `Class.test_function` names; parameter choices identify the relevant cases.

| File key | Relative source |
|---|---|
| H | [test_lifecycle_hooks.py](unit/test_core/test_mode/test_lifecycle_hooks.py) |
| E | [test_lifecycle_edge_cases.py](unit/test_core/test_mode/test_lifecycle_edge_cases.py) |
| T | [test_thread_lifecycle.py](unit/test_core/test_mode/test_thread_lifecycle.py) |
| M | [test_mode.py](unit/test_core/test_mode.py) |
| D | [test_lifecycle_hooks_thread_safety.py](unit/test_e2e/test_lifecycle_hooks_thread_safety.py) |
| V | [test_event_driven_lifecycle.py](unit/test_e2e/test_event_driven_lifecycle.py) |

## States and ownership

`U`: unentered, `active is None`; `A`: entered, `active is True`; `F`: entered, `active is False` (activation failed). A context owner/token is separate: explicit `exit()` inside `with` reaches U while that context still owns its token until `__exit__`.

| Behavior / transition | Exact tests |
|---|---|
| U → A or F: before_enter → activation → matching result hook → after_enter | E: `TestCompleteStateTransitions.test_state_transition` (`entered=False`, all entry policies); H: `TestLifecycleHookInvocationOrder.test_hook_invocation_order_success`, `TestLifecycleHookInvocationOrder.test_hook_invocation_order_fail` |
| A/F → A/F on duplicate explicit entry: pass is silent, warn warns, error raises; hooks skipped, existing result preserved | E: `TestCompleteStateTransitions.test_state_transition` (`entered=True`, pass/warn/error); H: `TestHookNotCalledOnDoubleEnter.test_hooks_not_called_on_double_enter` |
| Duplicate explicit entry defaults to warn | M: `TestModeEnterExit.test_enter_twice_warns_by_default` |
| U/A/F → U on exit; both exit hooks always run; only A deactivates | E: `TestCompleteStateTransitions.test_state_transition` (`operation="exit"`); H: `TestLifecycleFailureCleanup.test_repeated_exit_calls_hooks_without_repeated_deactivation` (never entered / already exited) |
| Reentry after exit creates a new result; result and historical method survive exit, active method clears; later failed entry preserves historical method | M: `TestModeEnterExit.test_enter_returns_same_result_instance_when_already_active`; E: `TestCompleteStateTransitions.test_success_then_failure_reentry` |
| Context entry rejects an already explicitly entered A/F without hooks or cleanup | E: `TestContextOwnership.test_context_rejects_explicitly_entered_mode` |
| Live context token rejects another context entry, including after explicit exit; original owner/state survives; token clears and later context reuse succeeds | E: `TestContextOwnership.test_context_token_has_one_owner` (`manual_exit=False/True`, same/other thread) |
| Explicit exit/reentry inside a context preserves its owner/token; outer exit clears both | E: `TestContextOwnership.test_explicit_reentry_keeps_context_owner` (success/failure) |
| Nested distinct contexts restore outer current mode; global count returns to zero, including failures | H: `TestHooksWithContextManager.test_nested_contexts_with_hooks`, `TestLifecycleFailureCleanup.test_enter_failure`, `TestLifecycleFailureCleanup.test_exit_failure`, `TestLifecycleFailureCleanup.test_body_failure`; E: `TestContextOwnership.test_context_token_has_one_owner` |
| Explicit entry appears in global mode tracking; visibility crosses threads; defensive removal before exit is safe | M: `TestModeThreadSafety.test_global_modes_reflects_manual_enter`, `TestModeThreadSafety.test_global_modes_visible_from_other_thread`, `TestModeEnterExit.test_exit_when_not_in_all_modes` |

## Hook contract and syntax

| Behavior | Exact tests |
|---|---|
| Both running/presenting factories forward all six callbacks for explicit/context/decorator syntax and success/failure | E: `TestHookContracts.test_factory_forwards_all_hooks` (full parameter matrix) |
| Mode hooks receive the executing Mode; result hooks receive ActivationResult; normal callback return values are ignored; before_enter sees None, after_enter/before_exit see success, after_exit sees None | E: `TestHookContracts.test_factory_forwards_all_hooks`; H: `TestLifecycleHookInvocationOrder.test_hook_invocation_order_success`, `TestLifecycleHookInvocationOrder.test_hook_invocation_order_fail` |
| Public ModeHook/ResultHook aliases exported from wakepy and wakepy.core | E: `TestHookContracts.test_public_aliases` |
| on_fail accepts None, warn, error, callable; callable identity retained; invalid strings rejected | M: `TestResolveOnFail.test_none_returns_none`, `TestResolveOnFail.test_warn_returns_callable_that_issues_activation_warning`, `TestResolveOnFail.test_error_returns_callable_that_raises_activation_error`, `TestResolveOnFail.test_callable_which_accepts_activation_result`, `TestResolveOnFail.test_invalid_string_raises_value_error` |
| Removed on_fail='pass' rejected by both factories; no public Mode.on_fail attribute | E: `TestHookContracts.test_removed_on_fail_api` |
| None allows F; ordinary warn warns and leaves F; error raises and requires explicit cleanup | H: `TestStateTransitions.test_exit_does_nothing_when_not_active`; M: `TestModeEnterExit.test_enter_on_fail_warn_succeeds`, `TestModeEnterExit.test_enter_on_fail_error_succeeds` |
| ActivationWarning points to the external caller for all three syntaxes | E: `TestHookContracts.test_activation_warning_points_to_caller` |
| Decorator hooks run on each call; failures inspect the actual clone, whose state/lock resets | H: `TestHooksWithDecorator.test_decorator_fires_hook_on_call`, `TestLifecycleFailureCleanup.test_enter_failure`, `TestLifecycleFailureCleanup.test_exit_failure` (`syntax="decorator"`) |
| Hook-driven UI status updates on disable-before-enable → enable → disable are None → True → None | V: `TestEventDrivenLifecycle.test_sync_callbacks_update_status_through_async_dispatch` (Android/Flet synchronous handlers within async dispatch; synchronous wakepy API) |

## Failures and cleanup

For every entry-hook row below, H `TestLifecycleFailureCleanup.test_enter_failure` covers explicit/context/decorator syntax and HookTestError, KeyboardInterrupt, SystemExit, ModeExit. Explicit callers supply `finally: exit()`; context/decorator entry failures automatically run both exit hooks, skip the body, restore outer context, reset the executing instance, and release its lock.

| Failure point | State immediately after failed explicit enter / cleanup outcome | Exact tests |
|---|---|---|
| before_enter | U; activation/result/after_enter skipped; exit hooks still run | H: `TestLifecycleFailureCleanup.test_enter_failure` (`hook_name="before_enter"`) |
| on_success | A until caller exits; after_enter skipped; cleanup deactivates | H: `TestLifecycleFailureCleanup.test_enter_failure` (`hook_name="on_success"`) |
| on_fail callback | F until caller exits; after_enter skipped; cleanup needs no deactivation | H: `TestLifecycleFailureCleanup.test_enter_failure` (`hook_name="on_fail"`) |
| after_enter | A or F until caller exits; cleanup deactivates only A | H: `TestLifecycleFailureCleanup.test_enter_failure` (`hook_name="after_enter"`, both outcomes) |
| Built-in on_fail='error', or 'warn' promoted to error | after_enter/body skipped; explicit caller or context/decorator runs exit hooks | H: `TestLifecycleFailureCleanup.test_builtin_on_fail_skips_after_enter` (all syntaxes) |
| before_exit | Deactivation/reset/after_exit still run; U after error | H: `TestLifecycleFailureCleanup.test_exit_failure` (`hook_name="before_exit"`, all syntaxes and four exception types) |
| after_exit | Deactivation/reset already complete; U after error | H: `TestLifecycleFailureCleanup.test_exit_failure` (`hook_name="after_exit"`, same matrix) |
| before_exit and/or after_exit in U/F | Both hooks attempted, no deactivation, U and unlocked; final hook error wins | E: `TestCompleteStateTransitions.test_exit_failures_from_inactive_states` |
| Method deactivation | Reset/after_exit/context restoration still run; ordinary Exception wrapped in RuntimeError with cause retained in __context__; KeyboardInterrupt/SystemExit propagate unchanged | H: `TestLifecycleFailureCleanup.test_exit_failure` (`hook_name="deactivate"`, same matrix) |
| Body | Exit hooks/deactivation run; context restored; ModeExit swallowed, other tested BaseExceptions propagated | H: `TestLifecycleFailureCleanup.test_body_failure` (context/decorator, four exception types) |
| Multiple entry/body/exit/deactivation failures | Last cleanup exception propagates, earlier errors chained in reverse occurrence order; reset/context restoration/unlock still complete | H: `TestLifecycleFailureCleanup.test_multiple_failures_are_chained` (eight selected failure combinations) |

## Recursion and threading

| Guarantee / scenario | Exact tests |
|---|---|
| Same-mode enter/exit from before_enter/after_enter/before_exit/after_exit raises RuntimeError | H: `TestRecursionGuard.test_entry_hook_recursive_call_raises`, `TestRecursionGuard.test_exit_hook_recursive_call_raises` |
| Same-mode enter/exit/context entry from either result hook raises RuntimeError; context entry cleans up | E: `TestHookContracts.test_result_hooks_reject_same_mode_recursion` |
| A result hook may enter another Mode | H: `TestRecursionAllowedAcrossModes.test_entering_different_mode_from_hook_is_allowed` |
| Lifecycle lock held throughout each mode hook | H: `TestThreadSafetyLockOrdering.test_lock_acquired_before_before_enter_hook`, `TestThreadSafetyLockOrdering.test_lock_acquired_before_after_enter_hook`, `TestThreadSafetyLockOrdering.test_lock_acquired_before_before_exit_hook`, `TestThreadSafetyLockOrdering.test_lock_acquired_before_after_exit_hook` |
| Normal and exceptional enter/exit release the lock | H: `TestThreadSafetyLockOrdering.test_lock_released_after_enter`, `TestThreadSafetyLockOrdering.test_lock_released_after_exit`, `TestThreadSafetyLockOrdering.test_lock_released_after_enter_raises`, `TestThreadSafetyLockOrdering.test_lock_released_after_exit_raises`; `TestLifecycleFailureCleanup.test_enter_failure`, `TestLifecycleFailureCleanup.test_exit_failure` |
| Other threads' enter/exit wait while any of four mode hooks holds the same Mode lock; event order remains serialized | T: `TestSerializedLifecycle.test_same_mode_calls_wait_for_hooks` (four hooks × enter/exit) |
| Failed context entry and automatic cleanup use one uninterrupted lock acquisition, for every entry hook/outcome | T: `TestSerializedLifecycle.test_failed_context_entry_uses_one_lock_acquisition` |
| Entry arriving during failed-entry cleanup waits until cleanup completes | T: `TestSerializedLifecycle.test_failed_context_entry_cleans_up_before_waiting_enter` |
| Different Mode instances have independent locks | H: `TestThreadSafetyLockOrdering.test_different_modes_do_not_share_lifecycle_lock` |
| Concurrent decorator calls execute independent hook/body sequences on separate instances | D: `TestThreadSafety.test_hooks_independent_per_thread` (barrier-coordinated three workers, worker errors collected) |
| Contended explicit entry follows warn/pass policy; concurrent entry/exit completes without recorded errors | M: `TestModeThreadSafety.test_concurrent_enter_exactly_one_succeeds`, `TestModeThreadSafety.test_concurrent_enter_pass_no_warning`, `TestModeThreadSafety.test_concurrent_enter_and_exit_no_crash` |
| Every contended exit invokes before_exit, including after prior deactivation | M: `TestModeThreadSafety.test_concurrent_exit_calls_before_exit_hook_for_each_call`; T: `TestSerializedLifecycle.test_same_mode_calls_wait_for_hooks` (exit/exit) |
| Explicit entry on one thread can exit on another | M: `TestModeThreadSafety.test_cross_thread_exit_does_not_crash` |

## Evidence limits

These tests use recording/fake methods: successful reset does not establish that a native OS inhibitor was released after native deactivation failure. Thread tests exercise selected coordinated schedules, not every possible interleaving. Failure chaining tests cover selected combinations, not every Cartesian combination. The event regression models callback dispatch and status hooks; it does not run Android/Flet or add an async wakepy API.
