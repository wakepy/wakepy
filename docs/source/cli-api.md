# CLI API

It is possible to start wakepy from the command line either by running

```{code-block} text
wakepy
```

or

```{code-block} text
python -m wakepy
```

This starts wakepy in the *default mode* (`-r`), which corresponds to a [`keep.running`](#keep-running-mode) mode with default arguments. The available options are:

```{code-block} output
usage: wakepy [-h] [-r] [-p] [-v] {methods} ...

positional arguments:
  {methods}              Available commands
    methods              List all available wakepy Methods for the selected
                         mode in priority order

options:
  -h, --help             show this help message and exit
  -r, --keep-running     Keep programs running (DEFAULT); inhibit automatic
                         idle timer based sleep / suspend. If a screen lock
                         (or a screen saver) with a password is enabled,
                         your system *may* still lock the session
                         automatically. You may, and probably should, lock
                         the session manually. Locking the workstation does
                         not stop programs from executing.
  -p, --keep-presenting  Presentation mode; inhibit automatic idle timer
                         based sleep, screensaver, screenlock and display
                         power management.
  -v, --verbose          Increase verbosity level (-v for INFO, -vv for
                         DEBUG). Default is WARNING, which shows only really
                         important messages.
```


````{admonition} Command "wakepy" not found?
:class: note

If you just installed `wakepy`, you might need to restart shell / terminal application to add it to the PATH.
````

```{versionchanged} 0.10.0
Renamed `-k` to `-r` and `--presentation` to `--keep-presenting` ([wakepy/#355](https://github.com/wakepy/wakepy/issues/355)).
```

(wakepy-methods-cli)=
## wakepy methods

```{versionadded} 1.0.0

```

Lists all available [wakepy Methods](methods-reference.md#wakepy-methods) for the selected mode in priority order, showing which ones work on the current system and which ones don't.

**Usage:**
- `wakepy methods` - List methods for keep.running mode (default, compact output)
- `wakepy methods -p` - List methods for keep.presenting mode
- `wakepy methods -v` - Show detailed output with failure reasons
- `wakepy methods -vv` - Enable INFO logging
- `wakepy methods -vvv` - Enable DEBUG logging

**Available options:**

```{code-block} output
usage: wakepy methods [-h] [-r] [-p] [-v]

options:
  -h, --help             show this help message and exit
  -r, --keep-running     Keep programs running (DEFAULT); inhibit automatic
                         idle timer based sleep / suspend. If a screen lock
                         (or a screen saver) with a password is enabled, your
                         system *may* still lock the session automatically.
                         You may, and probably should, lock the session
                         manually. Locking the workstation does not stop
                         programs from executing.
  -p, --keep-presenting  Presentation mode; inhibit automatic idle timer based
                         sleep, screensaver, screenlock and display power
                         management.
  -v, --verbose          Increase verbosity level (-v for detailed output, -vv
                         for INFO logging, -vvv for DEBUG logging). Default
                         shows only method names and status.
```

**Example output (default):**

```{code-block} output
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                      keep.running
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. org.freedesktop.PowerManagement          FAIL
  2. org.gnome.SessionManager                 SUCCESS
  3. caffeinate                               *
  4. SetThreadExecutionState                  *
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Example output (with `-v`):**

```{code-block} output
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                                  keep.running
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. org.freedesktop.PowerManagement
     FAIL: DBusCallError("DBus call of method 'Inhibit' on interface
     'org.freedesktop.PowerManagement.Inhibit' with args ('wakepy', 'wakelock
     active') failed with message: [org.freedesktop.DBus.Error.ServiceUnknown]
     ('The name org.freedesktop.PowerManagement was not provided by any .service
     files',)")

  2. org.gnome.SessionManager
     SUCCESS

  3. caffeinate
     UNSUPPORTED: caffeinate is not supported on LINUX. The supported platforms
     are: MACOS

  4. SetThreadExecutionState
     UNSUPPORTED: SetThreadExecutionState is not supported on LINUX. The
     supported platforms are: WINDOWS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```