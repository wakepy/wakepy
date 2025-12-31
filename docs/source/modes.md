(wakepy-modes)=
# Wakepy Modes

Wakepy Modes are states that you activate, and while the mode is active, wakepy keeps the system awake (inhibits suspend/sleep). In the end you deactivate the mode. Each Mode is implemented with multiple [Methods](#wakepy-methods) which support different platforms. Wakepy selects the used Method automatically, but it may also be selected by the user. The available modes are

| Wakepy mode              | [keep.running](#keep-running-mode) | [keep.presenting](#keep-presenting-mode)|
| ------------------------ | ------------ | --------------- |
| Sleep is prevented       | Yes          | Yes             |
| Screenlock is prevented  | No[^win-slock]          | Yes             |
| Screensaver is prevented | No          | Yes             |

[^win-slock]: Depending on system settings, it is possible that Windows will not automatically lock the system, because Windows will lock the screen either when (1) returning from suspend (which is now inhibited) or (2) when returning from Screen Saver, *if ScreenSaverIsSecure is set or enforced by a Group Policy (GPO)*.  See: [wakepy/#169](https://github.com/wakepy/wakepy/issues/169)

```{note}
The table above only considers the *automatic* actions (go to sleep, start screenlock, start screensaver), which are based on the *idle timer*; It is still possible to put system to sleep by selecting Suspend/Sleep from a menu, closing the laptop lid or pressing a power key, for example. It is also possible to manually lock the session/screen or start screensaver.
```

(keep-running-mode)=
## keep.running

While `keep.running` mode is activated, the system may not automatically go to sleep (or suspend) meaning that programs will continue running and can use CPU.

**Python example: Decorator syntax**
```{code-block} python
from wakepy import keep

@keep.running
def long_running_task():
    # Do something that takes a long time. The system may start screensaver
    # / screenlock or blank the screen, but CPU will keep running.
```


**Python example: Context Manager syntax**
```{code-block} python
from wakepy import keep

with keep.running():
    # Do something that takes a long time. The system may start screensaver
    # / screenlock or blank the screen, but CPU will keep running.
```

```{admonition} See also
:class: seealso

See the [User Guide](#user-guide) and the API Reference for {func}`keep.running() <wakepy.keep.running>` for more details.
```

**CLI**
```{code-block}
wakepy
```


Can I lock my computer after entered `keep.running` mode?
: Yes, and you probably should, if you're not near your computer. The program will
continue execution regardless of the lock.

What about automatic lockscreen / screensaver in `keep.running` mode??
: The system may still automatically log out user, enable lockscreen or turn off the
display. Automatic lock screen is not guaranteed, but it is  not prevented in any way. Most systems are configured to automatically lock the session after a timeout. One exception is Windows which will lock the screen only either when (1) returning from suspend (which is now inhibited) or (2) when returning from Screen Saver, *if ScreenSaverIsSecure is set or enforced by a Group Policy (GPO)*.  See: [wakepy/#169](https://github.com/wakepy/wakepy/issues/169)

(keep-presenting-mode)=
## keep.presenting

While `keep.presenting` mode is activated, the system may not automatically go to sleep (or suspend) meaning that programs will continue running and can use CPU. In addition to that, automatic start of screensaver & screenlock are prevented, meaning that you can
show content in the `keep.presenting` mode.

**Python example: Decorator syntax**
```{code-block} python
from wakepy import keep

@keep.presenting
def long_running_task():
    # Do something that takes a long time and requires the screen to be awake
```

**Python example: Context Manager syntax**
```{code-block} python
from wakepy import keep

with keep.presenting():
    # Do something that takes a long time and requires the screen to be awake
```

```{admonition} See also
:class: seealso

See the [User Guide](#user-guide) and the API Reference for {func}`keep.presenting() <wakepy.keep.presenting>` for more details.
```

**CLI**
```{code-block}
wakepy -p
```



Can I manually start lockscreen / screensaver in `keep.presenting` mode?
: Yes. Only the idle timer based screensaver / lockscreen is prevented. Note that
manually entering screensaver does not deactivate the mode.



## Wakepy Modes FAQ

What happens id the process holding the lock dies?
: The lock is automatically removed. Wakepy always leaves the system to a clean state, and does not do any kind of configuration changes or anything which would need manual reversal if the process is killed abruptly.


Does wakepy prevent manually putting system to sleep?
: Only the  automatic, idle timer timeout based sleep / suspend is prevented; Wakepy will not prevent user manually entering sleep from a menu, by closing a laptop lid or by pressing a power button, for example.


How to use wakepy in tests / CI
: One problem with tests and/or CI systems is that many times the environment is different, and preventing system going to sleep works differently there. To fake a successful inhibit lock in tests, you may set an environment variable: [`WAKEPY_FAKE_SUCCESS`](#WAKEPY_FAKE_SUCCESS) to a truthy value like `1`.