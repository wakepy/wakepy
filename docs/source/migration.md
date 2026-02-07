# Migration Guide
## Migration Guide: 1.0.0

### New decorator syntax

Wakepy 1.0.0 adds support for using `keep.running()` and `keep.presenting()` as [decorators](https://wakepy.readthedocs.io/latest/user-guide.html#decorator-syntax):

```{code-block} python
from wakepy import keep

#  Old way (wakepy < 1.0.0): only context-manager syntax
def long_running_function():
   with keep.presenting():
        do_something()


# New way (wakepy 1.0.0): decorator syntax
@keep.presenting
def another_long_running_function():
    do_something()
```

The existing context manager syntax continues to work as before, but the decorator syntax gives the possibility save one indentation level. If you need to access the current `Mode` when using the decorator syntax, use [`current_mode()`](https://wakepy.readthedocs.io/latest/api-reference.html#wakepy.current_mode).



### Property renames

Several properties have been renamed in wakepy 1.0.0. In addition, the `Mode.method` and `Mode.active_method` attributes are now {class}`MethodInfo <wakepy.MethodInfo>` instances. The old names are deprecated and will be removed in a future version. They still work but will issue {class}`DeprecationWarning`:

**Renamed properties:**
- {attr}`Mode.activation_result <wakepy.Mode.activation_result>` → {attr}`Mode.result <wakepy.Mode.result>`
- {attr}`Mode.used_method <wakepy.Mode.used_method>` → {attr}`Mode.method <wakepy.Mode.method>`
- {attr}`ActivationResult.active_method <wakepy.ActivationResult.active_method>` → {attr}`ActivationResult.method <wakepy.ActivationResult.method>`


**Example:**
```{code-block} python
from wakepy import keep

# Old way (wakepy < 1.0.0, deprecated)
with keep.running() as mode:
    result = mode.activation_result    # DeprecationWarning
    method = mode.used_method          # DeprecationWarning (str)


# New way (wakepy 1.0.0)
with keep.running() as mode:
    result = mode.result               # ActivationResult
    method = mode.method               # MethodInfo
    method_name = str(mode.method)     # str
```

### ActivationResult changes

#### active_method -> method

The {attr}`ActivationResult.active_method <wakepy.ActivationResult.active_method>` attribute has been replaced by {attr}`ActivationResult.method <wakepy.ActivationResult.method>`. The key difference is that `active_method` returns a string (the method name), while `method` returns a {class}`MethodInfo <wakepy.MethodInfo>` instance.

```{code-block} python
from wakepy import keep

with keep.running() as mode:
    result = mode.result

    # Old way (wakepy < 1.0.0, deprecated)
    method_name = result.active_method  # str or None

    # New way (wakepy 1.0.0)
    method_info = result.method         # MethodInfo or None
    method_name = str(result.method)    # str (if method is not None)
    method_name = result.method.name    # str (if method is not None)
```

#### mode_name type change

{attr}`ActivationResult.mode_name <wakepy.ActivationResult.mode_name>` is now always a string instead of {class}`ModeName <wakepy.ModeName>`:

```{code-block} python
from wakepy import keep, ModeName

with keep.running() as mode:
    result = mode.result

    # Old way (wakepy < 1.0.0)
    assert result.mode_name == ModeName.KEEP_RUNNING  # ModeName enum

    # New way (wakepy 1.0.0)
    assert result.mode_name == "keep.running"  # string
```

#### Keyword-only arguments and new style parameter

{meth}`ActivationResult.list_methods() <wakepy.ActivationResult.list_methods>` arguments are now keyword-only.

```{code-block} python
# Old way (wakepy < 1.0.0)
methods = result.list_methods(True, False)  # positional args

# New way (wakepy 1.0.0)
methods = result.list_methods(used=True, unused=False)  # keyword-only
```

#### get_failure_text defaults to "block"

{meth}`ActivationResult.get_failure_text() <wakepy.ActivationResult.get_failure_text>` now has a `style` parameter, and the default format has changed from single-line (inline) to multi-line (block) format.

```{code-block} python
from wakepy import keep

# Assuming activation fails
with keep.running() as mode:
    result = mode.result

    # Old way (wakepy < 1.0.0): always returned inline format
    failure_text = result.get_failure_text()  # single-line string

    # New way (wakepy 1.0.0): defaults to block format
    failure_text = result.get_failure_text()  # multi-line string (block format)

    # To get the old behavior, use style="inline"
    failure_text = result.get_failure_text(style="inline")  # single-line string
```

### Private API changes

The following are no longer part of the public API:

- `Mode._from_name()` (now private)
- `Mode._method_classes` (now private)

If you were using these, you should use the public API instead. For creating modes, use {func}`keep.running() <wakepy.keep.running>` or {func}`keep.presenting() <wakepy.keep.presenting>`.


### Wakepy CLI


Default mode for the wakepy CLI has changed from `keep.running` to `keep.presenting`.

**Before (wakepy < 1.0.0):**
```bash
wakepy              # keep.running mode (default)
wakepy -p           # keep.presenting mode
```

**After (wakepy 1.0.0):**
```bash
wakepy              # keep.presenting mode (default)
wakepy -r           # keep.running mode
```

## Migration Guide: 0.10.0

### on_fail action

As the previous default `on_fail` value of {func}`keep.running <wakepy.keep.running>` and {func}`keep.presenting <wakepy.keep.presenting>` was "error" (=raise Exception if activation fails) and the new default is "warn", *if you still wish to raise Exceptions*, use the following:

```{code-block} python
from wakepy import keep

with keep.running(on_fail="error"):
  do_something()
```


## Migration Guide: 0.8.0

### Decision when keepawake fails

The old way (wakepy <= 0.8.0) was:

```{code-block} python
from wakepy import keep

with keep.running() as m:
  if not m.success:
    # optional: signal to user?
  do_something()
```

On wakepy 0.8.0 one should use the `on_fail` parameter for controlling what to do if activation fails. See the [Controlling the on_fail action](#on-fail-action) in the [User Guide](#user-guide).  A minimum example would be:


```{code-block} python
from wakepy import keep

with keep.running(on_fail=react_on_failure) as m:   
    do_something()

def react_on_failure(result: ActivationResult):
    print(f'Failed to keep system awake using {result.mode_name} mode')
```

See the {class}`ActivationResult <wakepy.ActivationResult>` docs for more details on what's available on the `result` object. The `m.success` does not exist anymore, as the type of `m` is now an instance of {class}`Mode <wakepy.Mode>`. It has {attr}`Mode.active <wakepy.Mode.active>`. and {attr}`Mode.activation_result <wakepy.Mode.activation_result>`. as well as {attr}`Mode.active_method <wakepy.Mode.active_method>` and  {attr}`Mode.used_method <wakepy.Mode.used_method>`.

## Migration Guide: 0.7.0

- When migrating from wakepy <=0.6.0 to 0.7.0
-  `set_keepawake` and `unset_keepawake` and `keepawake`: Replace with `keep.running` or `keep.presenting`, whichever makes sense in the application.

### Python API
#### wakepy <=0.6.0
```{code-block} python
from wakepy import keepawake

with keepawake():
  do_something()
```

or

```{code-block} python
from wakepy import set_keepawake, unset_keepawake

set_keepawake()
do_something()
unset_keepawake()
```

#### wakepy 0.7.0
```{code-block} python
from wakepy import keep

with keep.running() as m:
  if not m.success:
    # optional: signal to user?
  do_something()
```

or

```{code-block} python
from wakepy import keep

with keep.presenting() as m:
  if not m.success:
    # optional: signal to user?
  do_something()
```

### CLI

- Replace `-s` / `--keep-screen-awake` with `-p` / `--presentation`;

### wakepy <= 0.6.0
```
wakepy -s
```
### wakepy 0.7.0
```
wakepy -p
```
