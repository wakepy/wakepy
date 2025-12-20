# CLI API

It is possibe to start wakepy from the command line either by running

```{code-block} text
wakepy
```

or

```{code-block} text
python -m wakepy
```

This starts wakepy in the *default mode* (`-r`), which corresponds to a [`keep.running`](#keep-running-mode) mode with default arguments. The available options are:

```{code-block} output
usage: wakepy [-h] [-r] [-p] [-v]

options:
  -h, --help             show this help message and exit
  -r, --keep-running     Keep programs running (DEFAULT); inhibit automatic idle timer based
                         sleep / suspend. If a screen lock (or a screen saver) with a
                         password is enabled, your system *may* still lock the session
                         automatically. You may, and probably should, lock the session
                         manually. Locking the workstation does not stop programs from
                         executing.
  -p, --keep-presenting  Presentation mode; inhibit automatic idle timer based sleep,
                         screensaver, screenlock and display power management.
  -v, --verbose          Increase verbosity level (-v for INFO, -vv for DEBUG). Default is
                         WARNING, which shows only really important messages.
```


````{admonition} Command "wakepy" not found?
:class: note

If you just installed `wakepy`, you might need to restart shell / terminal application to make added to the PATH.
````

```{versionchanged} 0.10.0
Renamed `-k` to `-r` and `--presentation` to `--keep-presenting` ([wakepy/#355](https://github.com/wakepy/wakepy/issues/355)).
```