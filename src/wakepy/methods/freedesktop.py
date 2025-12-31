"""The Freedesktop.org related methods"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import typing

from wakepy.core import (
    BusType,
    DBusAddress,
    DBusMethod,
    DBusMethodCall,
    Method,
    ModeName,
    PlatformType,
)

if typing.TYPE_CHECKING:
    from typing import Optional, Tuple

logger = logging.getLogger(__name__)

XDG_SESSION_DESKTOP = "XDG_SESSION_DESKTOP"
"""The environment variable for the xdg desktop of the current session. Defined
in pam_systemd manual[1].

Note that there's also XDG_CURRENT_DESKTOP which contains a colon-separated
list of DEs, defined in [2]

[1]: https://www.freedesktop.org/software/systemd/man/pam_systemd.html
[2]: https://specifications.freedesktop.org/desktop-entry-spec/desktop-entry-spec-latest.html
"""

KDE = "KDE"
"""Constant for KDE desktop environment / KDE Plasma"""
XFCE = "XFCE"
"""Constant for Xfce desktop environemtn"""


class FreedesktopInhibitorWithCookieMethod(Method):
    """Base class for freedesktop.org D-Bus based methods."""

    service_dbus_address: DBusAddress
    supported_platforms = (PlatformType.UNIX_LIKE_FOSS,)

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.inhibit_cookie: Optional[int] = None

    def enter_mode(self) -> None:
        call = DBusMethodCall(
            method=self.method_inhibit,
            args=dict(
                application_name="wakepy",
                reason_for_inhibit="wakelock active",
            ),
        )

        retval = self.process_dbus_call(call)
        if retval is None:
            raise RuntimeError(f"Could not get inhibit cookie from {self.name}")

        logger.debug(
            "Got inhibit cookie from %s: %s",
            self.name,
            retval[0],
        )
        self.inhibit_cookie = retval[0]

    def exit_mode(self) -> None:
        if self.inhibit_cookie is None:
            # Nothing to exit from.
            return

        logger.debug(
            "Exiting %s using inhibit cookie: %s",
            self.name,
            self.inhibit_cookie,
        )
        call = DBusMethodCall(
            method=self.method_uninhibit,
            args=dict(cookie=self.inhibit_cookie),
        )
        self.process_dbus_call(call)
        self.inhibit_cookie = None

    @property
    def method_inhibit(self) -> DBusMethod:
        return DBusMethod(
            name="Inhibit",
            signature="ss",
            params=("application_name", "reason_for_inhibit"),
            output_signature="u",
            output_params=("cookie",),
        ).of(self.service_dbus_address)

    @property
    def method_uninhibit(self) -> DBusMethod:
        return DBusMethod(
            name="UnInhibit",
            signature="u",
            params=("cookie",),
        ).of(self.service_dbus_address)


class FreedesktopScreenSaverInhibit(FreedesktopInhibitorWithCookieMethod):
    """Method using org.freedesktop.ScreenSaver D-Bus API

    https://people.freedesktop.org/~hadess/idle-inhibition-spec/re01.html
    """

    name = "org.freedesktop.ScreenSaver"
    mode_name = ModeName.KEEP_PRESENTING

    service_dbus_address = DBusAddress(
        bus=BusType.SESSION,
        service="org.freedesktop.ScreenSaver",
        path="/org/freedesktop/ScreenSaver",
        interface="org.freedesktop.ScreenSaver",
    )


class FreedesktopPowerManagementInhibit(FreedesktopInhibitorWithCookieMethod):
    """Method using org.freedesktop.PowerManagement D-Bus API

    According to [1] and [2] this might be obsolete. The spec itself can be
    read in the internet archives[3]. Part of the spec (v0.2.0) copied here for
    convenience:

    DBUS Interface:     org.freedesktop.PowerManagement.Inhibit
    DBUS Path:          /org/freedesktop/PowerManagement/Inhibit

    When the power manager detects an idle session and system, it can perform a
    system suspend or hibernate, known as an idle sleep action. We can prevent
    the session power manager daemon from doing this action using the inhibit
    interface.

    An automatic inhibit should be taken by the file manager if there is a slow
    network copy that will take many minutes to complete.

    A cookie is a randomly assigned 32bit unsigned integer used to identify the
    inhibit. It is required as the same application may want to call inhibit
    multiple times, without managing the inhibit calls itself.

    Name        Input               Output      Error               Description
    -------     ------------------  -------     ------              -----------
    Inhibit     string application  uint cookie PermissionDenied    [D1]
                string reason
    UnInhibit   uint cookie                     CookieNotFound      [D2]
    HasInhibit  bool has_inhibit                                    [D3]

    [D1] Inhibits the computer from performing an idle sleep action. Useful if
    you want to do an operation of long duration without the computer
    suspending. Reason and application should be translated strings where
    possible.

    [D2] Allows the computer to perform the idle sleep or user action if the
    number of inhibit calls is zero. If there are multiple cookies outstanding,
    clearing one cookie does not allow the action to happen. If the program
    holding the cookie exits from the session bus without calling UnInhibit()
    then it is automatically removed.

    [D3] Returns false if we have no valid inhibits. This will return true if
    the number of inhibit cookies is greater than zero.

    [1] https://code.videolan.org/videolan/vlc/-/issues/25785
    [2] https://www.freedesktop.org/wiki/Specifications/power-management-spec/
    [3] https://web.archive.org/web/20090417010057/http://people.freedesktop.org/~hughsient/temp/power-management-spec-0.2.html

    """

    name = "org.freedesktop.PowerManagement"
    mode_name = ModeName.KEEP_RUNNING

    service_dbus_address = DBusAddress(
        bus=BusType.SESSION,
        service="org.freedesktop.PowerManagement",
        path="/org/freedesktop/PowerManagement/Inhibit",
        interface="org.freedesktop.PowerManagement.Inhibit",
    )

    _min_kde_plasma_version = (5, 12, 90)
    """The minimum KDE Plasma version which supports this method.

    In earlier versions of KDE Plasma, there was a bug which caused the
    PowerManagement.Inhibit to behave similarly to the
    org.freedesktop.ScreenSaver interface. This was fixed in commit
    152400c1b6880506ee1395011686c2b191f419a0 which was part of KDE Plasma
    5.12.90.
    """

    def caniuse(self) -> bool | None | str:
        current_de = _get_current_desktop_environment()
        logger.debug("Detected DE: %s", current_de)

        if current_de == KDE:
            kde_version = _get_kde_plasma_version()
            if kde_version is None:
                raise RuntimeError(
                    "Running on KDE but could not detect KDE Plasma version."
                )

            if kde_version < self._min_kde_plasma_version:
                min_version_str = ".".join(str(x) for x in self._min_kde_plasma_version)
                raise RuntimeError(
                    (f"{self.name} only supports KDE >= {min_version_str}")
                )
            # KDE Plasma with a supported version
            return True

        elif current_de == XFCE:
            raise RuntimeError(
                "org.freedesktop.PowerManagement does not support XFCE as it has a bug "
                "which prevents automatic screenlock / screensaver. See: "
                "https://gitlab.xfce.org/xfce/xfce4-power-manager/-/issues/65"
            )

        # Other DEs
        return True


def _get_current_desktop_environment() -> str | None:
    """Get the desktop environment of the current session. If the DE cannot be
    determined, return None"""
    if XDG_SESSION_DESKTOP not in os.environ:
        return None

    de_from_env_var = os.environ[XDG_SESSION_DESKTOP].upper()
    if de_from_env_var.upper() == KDE:
        return KDE
    elif de_from_env_var.upper() == XFCE:
        return XFCE
    return de_from_env_var


def _get_kde_plasma_version() -> Optional[Tuple[int, ...]]:
    """Get the KDE Plasma version as tuple.

    Returns
    -------
    versiontuple:
        The detected KDE Plasma version. For example: (5,27,9)
        If no KDE Plasma is found, returns None.

    """
    # returns for example 'plasmashell 5.27.9' but may also return some
    # additional text. See: https://github.com/wakepy/wakepy/issues/415
    # Skipping the warning. Tracking in https://github.com/wakepy/wakepy/issues/520
    output = subprocess.getoutput("plasmashell --version")  # noqa: S607, S605
    for line in output.splitlines():
        match = re.match(".*plasmashell ([0-9.]*).*", line)
        if match:
            break
    else:
        return None

    versionstring = match.group(1)
    versiontuple = tuple(int(x) for x in versionstring.split("."))
    return versiontuple
