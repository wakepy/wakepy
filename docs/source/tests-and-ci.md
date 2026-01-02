# Wakepy in tests and CI

When using wakepy in tests, CI environments, or during development, you may need to control its behavior. CI systems typically lack Desktop Environments and system services that wakepy relies on, which can cause mode activation to fail even if it works on your development machine.

## Environment variables

Wakepy provides two environment variables to help you test different scenarios:

1. **[`WAKEPY_FAKE_SUCCESS`](#WAKEPY_FAKE_SUCCESS)** - Forces wakepy to always succeed in mode activation (no real system calls made)
2. **[`WAKEPY_FORCE_FAILURE`](#WAKEPY_FORCE_FAILURE)** - Forces wakepy to fail all mode activations (for testing error handling)

In most cases, it is recommended to use `WAKEPY_FAKE_SUCCESS` in unit tests and CI to ensure consistent test behavior.

```{admonition} Testing with real D-Bus on Unix
:class: note
If you need to test real wakepy operations on Unix systems that rely on D-Bus based methods like [`org.gnome.SessionManager`](#org-gnome-sessionmanager) or [`org.freedesktop.ScreenSaver`](#org-freedesktop-screensaver) (e.g. GNOME and KDE), you'll need the `DBUS_SESSION_BUS_ADDRESS` environment variable set. See [Tests using real D-Bus methods](#tests-without-using-faked-success) for details.
```

(truthy-and-falsy-values)=
## Truthy and falsy values

When setting environment variables for wakepy, the following rules apply for determining if a value is truthy or falsy:

- **Falsy values** (case-insensitive): `0`, `no`, `N`, `false`, `F`, and the empty string `""`
- **Truthy values**: *Any* other value, including `1`, `yes`, `Y`, `true`, `T`.

This applies to both `WAKEPY_FAKE_SUCCESS` and `WAKEPY_FORCE_FAILURE` environment variables.

(WAKEPY_FAKE_SUCCESS)=
## WAKEPY_FAKE_SUCCESS
To force wakepy to fake a successful mode activation, you may set an environment variable `WAKEPY_FAKE_SUCCESS` to a [truthy value](#truthy-and-falsy-values) like `yes` or `1`.  This makes all wakepy Modes to insert a special fake method called `WakepyFakeSuccess` as the first item in the list of Methods to try. This method is always the highest priority (tried first), and its activation is guaranteed to succeed. This works with any mode and on any platform. Since the `WakepyFakeSuccess` Method is tried *before* any other possible Methods, there will be no IO (except for the env var check), and no calling of any executables or 3rd party services when `WAKEPY_FAKE_SUCCESS` is used.

```{admonition} Distinguishing real activation success from a faked one
:class: tip

If you need to check if the activation was real or a faked one, you can use the {attr}`Mode.result <wakepy.Mode.result>` which is an {class}`ActivationResult <wakepy.ActivationResult>` instance, and check the {attr}`ActivationResult.real_success <wakepy.ActivationResult.real_success>` attribute.
```


### pytest

To set `WAKEPY_FAKE_SUCCESS` in a single test, you may use the [monkeypatch](https://docs.pytest.org/en/latest/how-to/monkeypatch.html) fixture:

```{code-block} python
def test_foo(monkeypatch):
    monkeypatch.setenv("WAKEPY_FAKE_SUCCESS", "yes")
    # ... the test code
```

### tox

If using [tox](https://tox.wiki/), use [`setenv`](https://tox.wiki/en/4.14.2/config.html#set_env) (aka. `set_env`) in your tox.ini:

```{code-block} ini
[testenv]
# ... other settings
setenv =
    WAKEPY_FAKE_SUCCESS = "yes"
```

### nox

If using [nox](https://nox.thea.codes/), set the `WAKEPY_FAKE_SUCCESS` environment variable by adding the key-value pair to `session.env` in your noxfile.py. For example:

```{code-block} python
@nox.session
def tests(session):
    session.env["WAKEPY_FAKE_SUCCESS"] = "yes"
    # ... run tests
```

(WAKEPY_FORCE_FAILURE)=
## WAKEPY_FORCE_FAILURE
To force wakepy to fail all mode activations (for testing error handling), you may set an environment variable `WAKEPY_FORCE_FAILURE` to a [truthy value](#truthy-and-falsy-values) like `yes` or `1`. This forces every wakepy Method to fail just before attempting activation, allowing you to test your error handling code paths.

This is useful when you want to test how your application behaves when wakepy is unable to prevent the system from sleeping or locking the screen.

```{admonition} Behavior when both environment variables are set
:class: warning
If you set both `WAKEPY_FAKE_SUCCESS` and `WAKEPY_FORCE_FAILURE` to [truthy values](#truthy-and-falsy-values), `WAKEPY_FORCE_FAILURE` takes precedence and activation is guaranteed to fail.

While this is allowed, it is **not recommended** to set both environment variables to truthy values at the same time, as it makes your intention less clear.
```



### pytest

To set `WAKEPY_FORCE_FAILURE` in a single test, you may use the [monkeypatch](https://docs.pytest.org/en/latest/how-to/monkeypatch.html) fixture:


```{code-block} python
def test_error_handling(monkeypatch):
    monkeypatch.setenv("WAKEPY_FORCE_FAILURE", "yes")
    # ... test that your code handles wakepy activation failure correctly
```


## Tests using real D-Bus methods

If you need to run tests without faking a success (i.e., testing real wakepy functionality), note that on Linux and BSD systems, wakepy might use D-Bus based methods like [`org.gnome.SessionManager`](#org-gnome-sessionmanager) or [`org.freedesktop.ScreenSaver`](#org-freedesktop-screensaver) (e.g. on GNOME and KDE) to inhibit screensaver or power management. For these methods to work, the `DBUS_SESSION_BUS_ADDRESS` environment variable must be set to point to the session D-Bus address.

In normal desktop sessions, this environment variable is automatically set by the desktop environment. However, test runners and CI environments may not preserve environment variables by default, which can cause D-Bus methods to fail even when a session bus is available.

To pass the `DBUS_SESSION_BUS_ADDRESS` with tox, one would use [`passenv`](https://tox.wiki/en/4.14.2/config.html#passenv):

```{code-block} ini
[testenv]
# ... other settings
passenv =
    DBUS_SESSION_BUS_ADDRESS
```