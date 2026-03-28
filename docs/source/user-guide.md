(user-guide-page)=
# User Guide

## What are Modes and Methods?
The core concept of wakepy are different keepawake [Modes](#wakepy-modes). The Modes are *states* that are activated and deactivated and which keep your system awake. Each Mode is implemented by multiple [Methods](#wakepy-methods), and the particular Method that will be used depends on the operating system, Desktop Environment and their versions (among other things).  For example the [keep.presenting](#keep-presenting-mode) mode is implemented by [org.gnome.SessionManager](#org-gnome-sessionmanager) on Linux with GNOME DE, [SetThreadExecutionState](#windows-stes) on Windows and [caffeinate](#macos-caffeinate) on MacOS. In most cases, wakepy does nothing but calls an executable (caffeinate), a DLL function call (SetThreadExecutionState) or a D-Bus method (org.gnome.SessionManager). Wakepy helps in this by providing a coherent API which should just work™ on any system. Or, at least that is the vision of wakepy.

# Basic Usage

{func}`keep.running() <wakepy.keep.running>` and {func}`keep.presenting() <wakepy.keep.presenting>` return {class}`Mode <wakepy.Mode>` instances which can be used as [decorators](#decorator-syntax), as [context managers](#context-manager-syntax), or with the [explicit enter/exit syntax](#explicit-enter-exit-syntax).


(decorator-syntax)=
## Decorator syntax
```{versionadded} 1.0.0
```

The simplest way for using wakepy modes like  [`keep.running`](#keep-running-mode) and [`keep.presenting`](#keep-presenting-mode) is the decorator syntax, like this:

```{code-block} python
from wakepy import keep

@keep.running
def long_running_function():
    # Do something that takes a long time
```

**Notes**:
- It does not matter if you use the parenthesis or not if you're not using any input [arguments](#possible-arguments); `@keep.running()` is identical to `@keep.running`.
- If you want to get access to the current [Mode instance](#mode-instances) when using the decorator
syntax, you should use {func}`current_mode() <wakepy.current_mode>`, as that is
the [multi-threading safe](#multithreading-multiprocessing) way for doing it.
- Using the [decorator syntax](#decorator-syntax)  is functionally equivalent of using the [context managers](#context-manager-syntax); the decorated function will create a new {class}`Mode <wakepy.Mode>` instance under the hood every time you call the decorated function, and will use it as a context manager automatically.

(context-manager-syntax)=
## Context Managers

Because [`keep.running()`](#keep-running-mode) or [`keep.presenting()`](#keep-presenting-mode)  return Mode instances which are [context managers](https://peps.python.org/pep-0343/), they can be used with the `with` statement:

```{code-block} python
from wakepy import keep

with keep.running():
    # Do something that takes a long time
```

 When entering the context, a [Mode instance](#mode-instances) (`m`) is returned:

```{code-block} python
with keep.running() as m:
    ...
```

```{seealso}
[Mode instances](#mode-instances) and the API reference for {class}`~wakepy.Mode`
```


(explicit-enter-exit-syntax)=
## Explicit enter/exit syntax
```{versionadded} 2.0.0
```

In event-driven applications or GUI frameworks where activation and deactivation happen in separate callbacks (e.g. button clicks), the context manager is impractical. In these cases, use {meth}`Mode.enter() <wakepy.Mode.enter>` and {meth}`Mode.exit() <wakepy.Mode.exit>` explicitly:

```{code-block} python
from wakepy import keep

mode = keep.running()
try:
    mode.enter()
    # your event loop, GUI mainloop, etc.
finally:
    mode.exit()  # safe even if enter() failed or was never called
```

```{warning}
When using the explicit enter syntax, the caller is responsible for ensuring `exit()` is called. Always call `exit()` in a `finally` block (or equivalent cleanup handler) to guarantee the mode is deactivated even if an exception occurs.
```

**Notes**:
- `exit()` is always safe to call — even if `enter()` was never called, failed, or was already called once before. No guard like `if mode.active: mode.exit()` is needed.
- For most use cases, the [context manager](#context-manager-syntax) or [decorator](#decorator-syntax) syntax are preferred, as they handle cleanup automatically.
- If `enter()` is accidentally called twice on the same Mode instance, a `UserWarning` is issued by default. Pass `if_already_entered="pass"` to silence it or `if_already_entered="error"` to raise {class}`~wakepy.ContextAlreadyEnteredError`.

```{seealso}
{meth}`Mode.enter() <wakepy.Mode.enter>` and {meth}`Mode.exit() <wakepy.Mode.exit>`
```


(mode-instances)=
## Mode instances

 When entering the context, a {class}`~wakepy.Mode` instance (`m`) is returned:

```{code-block} python
with keep.running() as m:
    ...
```

You can also get access to the Mode instance at any part of the call stack using the {func}`current_mode() <wakepy.current_mode>` function:


```{code-block} python

@keep.running
def long_running_function():
    otherfunc()

def otherfunc():
    # Gets access to the Mode instance (of the @keep.running mode)
    m = current_mode()

```

The Mode has following important attributes:

- {attr}`m.active <wakepy.Mode.active>`: `True` if activating mode was successful. `False` if activation was attempted but failed. When using the context manager or decorator syntax, this is always `True` or `False` during the active scope (inside the `with` block or the decorated function). Before activation or after deactivation, the value is `None`. Can be [faked in CI](./tests-and-ci.md#wakepy_fake_success).
- {attr}`m.method <wakepy.Mode.method>`: Information about the used method. Unlike the `active_method`, will be available *also* after the deactivating the mode. (Type: {class}`~wakepy.MethodInfo`)
- {attr}`m.active_method <wakepy.Mode.active_method>`: Information about the *active* method. Will be `None` after deactivating the mode. (Type: {class}`~wakepy.MethodInfo`)
- {attr}`m.result <wakepy.Mode.result>`: An {class}`~wakepy.ActivationResult` instance which gives more detailed information about the activation process.

# Possible Arguments

(on-fail-action)=
## Controlling the on-fail action
```{versionadded} 0.8.0
```
```{versionchanged} 0.10.0
`on_fail` defaults to "warn" instead of "error". See: [wakepy/#376](https://github.com/wakepy/wakepy/issues/376).
```

The wakepy Modes (e.g. [`keep.running`](#keep-running-mode) and  [`keep.presenting`](#keep-presenting-mode)) also take an `on_fail` input argument which may be used to alter the behavior. Example:

```{code-block} python
from wakepy import keep

with keep.running(on_fail="warn"):
    # do something
```

(on-fail-actions-section)=
### on-fail actions

| `on_fail`                | What happens? |
| ------------------------ | ------------ |
| `None` | Does nothing |
| "warn" (default) | Issues an {class}`~wakepy.ActivationWarning` |
| "error" | Raises an {class}`~wakepy.ActivationError`        |
| Callable | The callable is called with one argument: the result of the activation which is <br> a instance of {class}`~wakepy.ActivationResult`. The call occurs before the with block is entered. |

#### Example: Notify user with a custom callable

This is what you could do if you want to inform the user that the activation of the mode was not successful, but still want to continue to run the task:

```{code-block} python
from wakepy import keep, ActivationResult

def react_on_failure(result: ActivationResult):
    print(f'Failed to keep system awake using {result.mode_name} mode')

def run_long_task():
    print('Running a long task')

with keep.running(methods=[], on_fail=react_on_failure):
    print('started')
    run_long_task()
```

- The `on_fail` parameter to {func}`keep.running() <wakepy.keep.running>` is a callable which gets called with an {class}`~wakepy.ActivationResult` when the activation of the mode fails.
- Here we use empty list in `methods` to force failure

Example output:

```
Failed to keep system awake using keep.running mode
started
Running a long task
```

#### Example: Notify user and exit

This is what you could do if you want to inform the user that the activation of the mode was not successful, and then exit from the with block:

```{code-block} python
from wakepy import keep, ActivationResult, ModeExit

def react_on_failure(result: ActivationResult):
    print(f'Failed to keep system awake using {result.mode_name} mode')

def run_long_task():
    print('Running a long task')

with keep.running(methods=[], on_fail=react_on_failure) as m:
    print('started')

    if not m.active:
        print('exiting')
        raise ModeExit

    run_long_task()
```

- The difference to the previous example is the {class}`ModeExit <wakepy.ModeExit>` which is used to exit the with block, if the {attr}`Mode.active <wakepy.Mode.active>` is not `True`.


Example output (notice that `run_long_task` was never called):

```
Failed to keep system awake using keep.running mode
started
exiting
```

(how-to-white-or-blacklist-methods)=
## Controlling the Methods to be tried

```{versionadded} 0.8.0
```

Wakepy tries in order a list of different [Methods](#wakepy-methods). By default this is of methods are all the Methods which implement the selected wakepy Mode. If you do not want to try all the methods, you can 

- Blacklist methods with the `omit` parameter
- Whitelist methods with the `methods` parameter

Only either `omit` or `methods` may be given (not both).

### Example: whitelisting methods

This would try the methods called `org.gnome.SessionManager` and `SomeOtherMethod`, but never any other methods. Note that the order is *not* defined by the whitelist.

```{code-block} python
from wakepy import keep

with keep.running(methods=['org.gnome.SessionManager', 'SomeOtherMethod']):
    ...
```

### Example: blacklisting methods

This would *never* try the methods called `org.gnome.SessionManager` and `SomeOtherMethod`, but only any other methods implementing the selected Mode.

```{code-block} python
from wakepy import keep

with keep.running(omit=['org.gnome.SessionManager', 'SomeOtherMethod']):
    ...
```


```{seealso}
`omit` and `methods` parameter of {func}`keep.running() <wakepy.keep.running>`  and {func}`keep.presenting() <wakepy.keep.presenting>`
```

(how-to-control-order-of-methods)=
## Controlling the order of Methods to be tried

```{versionadded} 0.8.0
```

To control the order of the methods to be tried, you may use the `methods_priority` argument. The argument should be a list of priority groups. Each group is a method name or set of method names. Each item within a priority group is considered as "equal priority" and wakepy's automatic logic will order the methods within the sets. An asterisk (`*`) may be used to denote "any other methods" and can be used once (and only once) within `methods_priority`.


### Example: prioritizing methods

This would put `MethodA` and `MethodB` to be in the highest priority group, and wakepy's automatic prioritization logic would determine which one of the methods should be tried first. It would also put the `MethodF` to have the least priority and that method would only be tried after trying any other methods have failed.

```{code-block} python
from wakepy import keep

with keep.running(methods_priority=[{"MethodA", "MethodB"}, "*", "MethodF"]):
    ...
```


```{seealso}
`methods_priority` parameter of {func}`keep.running() <wakepy.keep.running>`  and {func}`keep.presenting() <wakepy.keep.presenting>`
```

```{admonition} experimental feature
:class: note

The `methods_priority` is still an experimental feature and may change or be removed without further notice.

```

(lifecycle-hooks-section)=
## Lifecycle Hooks

```{versionadded} 2.0.0
```

Lifecycle hooks let you run callbacks at specific points in a Mode's lifecycle. Hooks work with all three usage syntaxes (context manager, decorator, explicit enter/exit).

### Available Hooks

**Mode hooks** — receive the {class}`~wakepy.Mode` instance:

| Hook | When Called |
|------|-------------|
| `before_enter` | Before entering the mode |
| `after_enter` | After entering the mode (after `on_success` or `on_fail`) |
| `before_exit` | Before exiting the mode |
| `after_exit` | After exiting the mode |

**Result hooks** — receive the {class}`~wakepy.ActivationResult` instance:

| Hook | When Called |
|------|-------------|
| `on_success` | When activation succeeds |
| `on_fail` | When activation fails (if set to a callable; see also [on-fail actions](#on-fail-actions-section)) |

### Example

```{code-block} python
from wakepy import keep, ActivationResult, Mode

def on_success(result: ActivationResult):
    print(f"Active with: {result.method}")

def on_fail(result: ActivationResult):
    print(f"Could not activate {result.mode_name}")

def after_enter(mode: Mode):
    print(f"Starting {mode.name} task (active: {mode.active})")

def after_exit(mode: Mode):
    print(f"Exited {mode.name} mode")

@keep.running(
    on_success=on_success,
    on_fail=on_fail,
    after_enter=after_enter,
    after_exit=after_exit,
)
def long_running_task():
    print("Running...")
```

Output (success):

```
Active with: org.gnome.SessionManager
Starting keep.running task (active: True)
Running...
Exited keep.running mode
```

```{seealso}
- [Mode Lifecycle: Lifecycle Hooks](./wakepy-mode-lifecycle.md#lifecycle-hooks) — execution timeline and thread safety details
- {class}`~wakepy.ActivationResult` — ActivationResult documentation
```

# Recipes

## Using similar keepawake in multiple places

In most of the cases, it is advisable to just have a single keepawake like [`keep.running()`](#keep-running-mode) or [`keep.presenting()`](#keep-presenting-mode) near the top level of your application. However, sometimes you might need to make multiple {class}`Mode <wakepy.Mode>` instances with similar keyword arguments. In that case, you can use a factory function like this:


```{code-block} python
from wakepy import keep, Mode

def keepawake() -> Mode:
    return keep.presenting(methods=["org.gnome.SessionManager"])

```

and use it like this:

```python
def somefunc():
    with keepawake() as m:
        ...

def otherfunc():
    with keepawake() as m:
        ...

@keepawake()
def do_something_useful():
    ...

@keepawake()
def do_something_else():
    ...
```

