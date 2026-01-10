(wakepy-methods)=
# Wakepy Methods

**What are wakepy Methods?**
Methods are different ways of entering in (or keeping a) Mode. A Method may support one or more platforms, and may have one or more requirements for software it should be able to talk to or execute. For example, on Linux, using the Inhibit method of the [org.gnome.SessionManager](#org-gnome-sessionmanager) D-Bus service is one way of entering the [`keep.running`](#keep-running-mode) mode, and it requires D-Bus and (a certain version of) GNOME. The following methods exist (⌛: [`keep.running`](#keep-running-mode), 🖥️: [`keep.presenting`](#keep-presenting-mode)): 

| Method                                                             | Modes |
| ------------------------------------------------------------------ | ----- |
| [caffeinate](#macos-caffeinate)                                    | ⌛ 🖥️   |
| [org.freedesktop.PowerManagement](org-freedesktop-powermanagement) | ⌛     |
| [org.freedesktop.ScreenSaver](org-freedesktop-screensaver)         | 🖥️     |
| [org.gnome.SessionManager](org-gnome-sessionmanager)               | ⌛🖥️    |
| [SetThreadExecutionState](windows-stes)                            | ⌛🖥️    |


(macos-caffeinate)=
## caffeinate

- **Name**: `caffeinate`
- **Modes**: [`keep.running`](#keep-running-mode), [`keep.presenting`](#keep-presenting-mode)
- **Introduced in**: wakepy 0.3.0
- **How it works**: It calls the `caffeinate` command to activate the keep.running mode and add the `-d` flag ("Create an assertion to prevent the display from sleeping.") for keep.presenting mode. See docs at [ss64.com](https://ss64.com/mac/caffeinate.html) or at archives from [developer.apple.com](https://web.archive.org/web/20140604153141/https://developer.apple.com/library/mac/documentation/Darwin/Reference/ManPages/man8/caffeinate.8.html)
- **Multiprocess safe?**: Yes
- **What if the process holding the lock dies?**: The lock is automatically removed.
- **How to check it?**: You should be able to see a process with a command `/bin/bash caffeinate` or similar associated with it using a task manager.
- **Requirements**: Mac OS X 10.8 Mountain Lion (July 2012) or newer.


(org-freedesktop-powermanagement)=
## org.freedesktop.PowerManagement
- **Name**: `org.freedesktop.PowerManagement`
- **Modes**: [`keep.running`](#keep-running-mode)
- **Introduced in**: wakepy 0.9.0
- **How it works**: Uses the Inhibit method of the org.freedesktop.PowerManagement D-Bus service when activating and saves the returned cookie on the Method instance. Uses UnInhibit method of the same service with the cookie when deactivating. The org.freedesktop.PowerManagement is an obsolete spec, but certain Desktop Environments provide that as the only option for inhibiting the suspend action. The documentation was previously hosted on [freedesktop.org](https://www.freedesktop.org/wiki/Specifications/power-management-spec/) but the links on the page are dead. The spec has three versions: 0.1, 0.2 and 0.3. The 0.3 is not found anywhere but the version 0.2 of the spec can be read in the [Internet Archive](https://web.archive.org/web/20090417010057/http://people.freedesktop.org/~hughsient/temp/power-management-spec-0.2.html)
- **Multiprocess safe?**: Yes
- **What if the process holding the lock dies?**: The lock is automatically removed.
- **How to check it?**:  You may check if there are *any* inhibitors using the HasInhibit method of the `/org/freedesktop/PowerManagement/Inhibit` object on the `org.freedesktop.PowerManagement.Inhibit` interface. Note that updating the inhibit flag from `false` to `true` may take a few seconds. A good tool for this is [D-Spy](https://apps.gnome.org/Dspy/). Alternatively, you could monitor your inhibit call with [`dbus-monitor`](https://dbus.freedesktop.org/doc/dbus-monitor.1.html).
- **Requirements**: D-Bus + KDE Plasma >=5.12.90 or other DE which implements this older freedesktop D-Bus interface. Exception: Xfce is not supported.
- **About unsupported DEs** Older versions of KDE Plasma had a bug which also prevented the screenlock/screesaver activation. The bug was fixed in [D11182](https://phabricator.kde.org/D11182), commit  [152400c1b688](https://phabricator.kde.org/R122:152400c1b6880506ee1395011686c2b191f419a0) and was part of the KDE Plasma 5.12.90 ( = 5.13 Beta) [release](https://kde.org/announcements/changelogs/plasma/5/5.12.5-5.12.90/). This Method is not supported either on Xfce as it has similar bug which prevents also the automatic screenlock/screensaver (See: [xfce4-power-manager/#65](https://gitlab.xfce.org/xfce/xfce4-power-manager/-/issues/65)), hence, wakepy refuses to use org.freedesktop.PowerManagement as method for keep.running mode on KDE < 5.12.90 and on any version of Xfce.
- **Post Keepawake Behavior**:  [Resetting](#idle-timer-resetting) type on KDE (KDE Plasma 5.27.11, tested by [reidswanson](https://github.com/reidswanson) on [#366](https://github.com/wakepy/wakepy/discussions/366#discussioncomment-9797027)).
- **Tested on**:  openSUSE 15.5 with KDE Plasma 5.27.9 ([Comment in #310](https://github.com/wakepy/wakepy/issues/310#issuecomment-2140156882) by [fohrloop](https://github.com/fohrloop/)).

(org-freedesktop-screensaver)=
## org.freedesktop.ScreenSaver
- **Name**: `org.freedesktop.ScreenSaver`
- **Modes**: [`keep.presenting`](#keep-presenting-mode)
- **Introduced in**: wakepy 0.6.0
- **How it works**: Uses the Inhibit method of [org.freedesktop.ScreenSaver](https://people.freedesktop.org/~hadess/idle-inhibition-spec/re01.html) D-Bus service when activating and saves the returned cookie on the Method instance. Uses the org.freedesktop.ScreenSaver.UnInhibit method with the cookie when deactivating. The org.freedesktop.ScreenSaver can only be used to prevent idle; that is why there is no "keep.running" mode counterpart.
- **Multiprocess safe?**: Yes
- **What if the process holding the lock dies?**: The lock is automatically removed.
- **How to check it?**:  The org.freedesktop.ScreenSaver does not expose a method for listing the inhibitors, but you could monitor your inhibit call with [`dbus-monitor`](https://dbus.freedesktop.org/doc/dbus-monitor.1.html).
- **Requirements**: D-Bus, and a [freedesktop.org compliant desktop environment](https://www.freedesktop.org/wiki/Desktops/), which should implement the org.freedesktop.ScreenSaver.Inhibit method.
- **Post Keepawake Behavior**:  [Resetting](#idle-timer-resetting) type on GNOME 47 ([#471](https://github.com/wakepy/wakepy/issues/471)). The behavior is likely to depend on the used DE.
- **Tested on**:  Ubuntu 22.04 with GNOME 42.9 ([wakepy/#171](https://github.com/wakepy/wakepy/pull/171)) and openSUSE 15.5 with KDE Plasma 5.27.9 ([wakepy/#310](https://github.com/wakepy/wakepy/issues/310#issuecomment-2135512139)) by [fohrloop](https://github.com/fohrloop/).


(org-gnome-sessionmanager)=
## org.gnome.SessionManager
- **Name**: `org.gnome.SessionManager`
- **Modes**: [`keep.running`](#keep-running-mode), [`keep.presenting`](#keep-presenting-mode)
- **Introduced in**: wakepy 0.8.0
- **How it works**: Uses the [Inhibit](https://lira.no-ip.org:8443/doc/gnome-session/dbus/gnome-session.html#org.gnome.SessionManager.Inhibit) method of [org.gnome.SessionManager](https://lira.no-ip.org:8443/doc/gnome-session/dbus/gnome-session.html#org.gnome.SessionManager) D-Bus service when activating and saves the returned cookie on the Method instance. For [`keep.running`](#keep-running-mode) mode uses flag 4 ("Inhibit suspending the session or computer"), and in [`keep.presenting`](#keep-presenting-mode) mode uses the flag 8 ("Inhibit the session being marked as idle"). To deactivate the mode, calls the [Uninhibit](https://lira.no-ip.org:8443/doc/gnome-session/dbus/gnome-session.html#org.gnome.SessionManager.Uninhibit) method of the org.gnome.SessionManager with the cookie.
- **Multiprocess safe?**: Yes
- **What if the process holding the lock dies?**: The lock is automatically removed.
- **How to check it?**:  You may check the list of inhibitors using the [GetInhibitors](https://lira.no-ip.org:8443/doc/gnome-session/dbus/gnome-session.html#org.gnome.SessionManager.GetInhibitors) method, which gives you list of object paths like `["/org/gnome/SessionManager/Inhibitor20"]`. Then you can use the [GetAppId](https://lira.no-ip.org:8443/doc/gnome-session/dbus/gnome-session.html#org.gnome.SessionManager.Inhibitor.GetAppId), [GetFlags](https://lira.no-ip.org:8443/doc/gnome-session/dbus/gnome-session.html#org.gnome.SessionManager.Inhibitor.GetFlags) and [GetReason](https://lira.no-ip.org:8443/doc/gnome-session/dbus/gnome-session.html#org.gnome.SessionManager.Inhibitor.GetReason) methods on the [org.gnome.SessionManager.Inhibitor](https://lira.no-ip.org:8443/doc/gnome-session/dbus/gnome-session.html#org.gnome.SessionManager.Inhibitor) interface of the listed objects on the org.gnome.SessionManager service to translate that into something meaningful. A good tool for this is [D-Spy](https://apps.gnome.org/Dspy/). Alternatively, you could monitor your inhibit call with [`dbus-monitor`](https://dbus.freedesktop.org/doc/dbus-monitor.1.html).
- **Requirements**: D-Bus, GNOME Desktop Environment with gnome-session running. The exact version of required GNOME is unknown, but this should work from GNOME 2.24 ([2008-09-23](https://gitlab.gnome.org/GNOME/gnome-session/-/tags/GNOME_SESSION_2_24_0)) onwards. See [version history of org.gnome.SessionManager.xml](https://gitlab.gnome.org/GNOME/gnome-session/-/commits/main/gnome-session/org.gnome.SessionManager.xml). At least [this](https://fedoraproject.org/wiki/Desktop/Whiteboards/InhibitApis) and [this](https://bugzilla.redhat.com/show_bug.cgi?id=529287#c3) mention GNOME 2.24.
- **Post Keepawake Behavior**:  [Resetting](#idle-timer-resetting) type (GNOME 47, [#471](https://github.com/wakepy/wakepy/issues/471)).
- **Tested on**:  Ubuntu 22.04.3 LTS with GNOME 42.9 ([PR #138](https://github.com/wakepy/wakepy/pull/138) by [fohrloop](https://github.com/fohrloop/)).

````{admonition} May slow down system if called repeatedly
:class: info

If used thousands of times really fast, may slow down system. See: [wakepy/#277](https://github.com/wakepy/wakepy/issues/277)
````


(windows-stes)=
## SetThreadExecutionState

````{admonition} Windows will not lock the screen automatically if Screen Saver settings do not require it
:class: warning

Since this method prevents sleep, screen can be only locked automatically if a screen saver is enabled and it set to ask for password. See [this](#checking-if-windows-will-lock-screen-automatically) for details.

````

- **Name**: `SetThreadExecutionState`
- **Modes**: [`keep.running`](#keep-running-mode), [`keep.presenting`](#keep-presenting-mode)
- **Introduced in**: wakepy 0.1.0
- **How it works**: It calls the [SetThreadExecutionState](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setthreadexecutionstate) function from the Kernel32.dll with ES_CONTINUOUS and ES_SYSTEM_REQUIRED flags when activating [`keep.running`](#keep-running-mode) mode, and additionally ES_DISPLAY_REQUIRED flag when activating [`keep.presenting`](#keep-presenting-mode) mode. It then uses the ES_CONTINUOUS flag for deactivating.
- **Wakepy specialities**: Starting with wakepy 0.9.1 you can have multiple modes (same or different) activated within the same python thread without them interfering with each other on activation or deactivation, as wakepy creates a *separate worker thread* for the single purpose of setting and keeping the thread execution flag each time you activate a mode with the `SetThreadExecutionState` wakepy.Method.
- **Multiprocess safe?**: Yes
- **What if the process holding the lock dies?**: The lock is automatically removed.
- **How to check it?**: Run `powercfg /requests` in an elevated cmd or Powershell.
- **Requirements**: Windows XP or higher (client), Windows Server 2003 or higher (server), as mentioned [here](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setthreadexecutionstate).
- **Post Keepawake Behavior**:  **Up to Windows 10**: [Non-Resetting](#idle-timer-non-resetting) with about 2 minutes of [Post-Exit Inhibit](#post-exit-inhibit). The post-exit inhibit time seems to be a bit random, but it's very likely that any post-exit inhibit duration is between 1:30min and 3:30min (See: [#450](https://github.com/wakepy/wakepy/issues/450#issuecomment-3074518760)). **Starting from Windows 11**: Just [Non-Resetting](#idle-timer-non-resetting), without post-exit inhibit. The post-exit inhibit behavior is also "documented" on [this question](https://learn.microsoft.com/en-us/answers/questions/999348/setthreadexecutionstate-without-es-continuous-does) on learn.microsoft.com (Sep 8, 2022), where the answer said: *"Prior to Windows 11 power requests were held an additional 2 minutes after they were dropped by the application. [...] This behavior was removed in Windows 11 and now systems are eligible to sleep as soon as the last power request is dropped"*.
- **Tested on**:  Windows 10 Pro version 22H2 build 19045.332 with and without Screen Saver + ScreenSaverIsSecure set in settings, Windows 10 Enterprise version 22H2 build 19045.3803 with Group Policies enforcing ScreenSaverIsSecure ([Issue #169](https://github.com/wakepy/wakepy/issues/169) by [fohrloop](https://github.com/fohrloop/)). 


 (checking-if-windows-will-lock-screen-automatically)=
````{admonition} How to check if Windows will lock the screen automatically when using SetThreadExecutionState
:class: info

There are two ways how a Windows system might automatically set a screen lock
1. When resuming from sleep, if "Require sign-in when PC wakes up from sleep" -setting is set.
2. When Screen Saver idle timeout is reached *and it has set to have password protection in the Lock Screen Setting or that is enforced by a Group Policy*.

if you want to check if your system will sleep automatically when using this method, you may either check the  `ScreenSaverIsSecure`, `ScreenSaveActive` and `ScreenSaveTimeout` from  "HKCU:\Control Panel\Desktop" and "HKCU:\Software\Policies\Microsoft\Windows\Control Panel\Desktop", or use the following python snippet:

```{code-block} python
import ctypes

SPI_GETSCREENSAVESECURE = 0x0076
SPI_GETSCREENSAVEACTIVE = 0x0010
SPI_GETSCREENSAVETIMEOUT = 0x000E

retval = ctypes.c_long()
pvparam = ctypes.byref(retval)

result = ctypes.windll.user32.SystemParametersInfoW(SPI_GETSCREENSAVEACTIVE, 0, pvparam, 0)
print('SPI_GETSCREENSAVEACTIVE', retval.value)

result = ctypes.windll.user32.SystemParametersInfoW(SPI_GETSCREENSAVESECURE, 0, pvparam, 0)
print('SPI_GETSCREENSAVESECURE', retval.value)

result = ctypes.windll.user32.SystemParametersInfoW(SPI_GETSCREENSAVETIMEOUT, 0, pvparam, 0)
print('SPI_GETSCREENSAVETIMEOUT', retval.value)
```


````




