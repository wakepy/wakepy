from __future__ import annotations

import logging
import typing
from abc import ABC, abstractmethod
from io import IOBase
from subprocess import PIPE, Popen
from typing import cast

from wakepy.core import Method, ModeName, PlatformType

if typing.TYPE_CHECKING:
    from typing import List, Optional


class _MacCaffeinate(Method, ABC):
    """This is a method which calls the `caffeinate` command.

    Docs: https://ss64.com/osx/caffeinate.html
    Also: https://web.archive.org/web/20140604153141/https://developer.apple.com/library/mac/documentation/Darwin/Reference/ManPages/man8/caffeinate.8.html

    The caffeinate command was introduced in OS X 10.8 Mountain Lion (2012) [1]

    [1]: "Interesting new UNIX commands/binaries in OS X Mountain Lion",
          2012-07-27 by Patrick Seemann
          https://apple.blogoverflow.com/2012/07/interesting-new-unix-commandsbinaries-in-os-x-mountain-lion/
    """

    supported_platforms = (PlatformType.MACOS,)

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.logger = logging.getLogger(__name__)
        self._process: Optional[Popen[bytes]] = None

    def enter_mode(self) -> None:
        self.logger.debug('Running "%s"', " ".join(self.command))
        # command is a hardcoded list, safe from injection (-> skip S603)
        self._process = Popen(self.command, stdin=PIPE, stdout=PIPE)  # noqa: S603

    def exit_mode(self) -> None:
        if self._process is None:
            self.logger.debug("No need to terminate process (not started)")
            return
        self.logger.debug('Terminating process ("%s")', " ".join(self.command))

        # The pipes need to be closed before terminating the process, otherwise
        # will get ResourceWarning: unclosed file
        # See: https://stackoverflow.com/a/58696973/3015186 and
        # https://github.com/wakepy/wakepy/issues/478
        #
        # The cast is required because we know that these are not None, but
        # mypy doesn't, and using if statements would ruin test coverage.
        stdin = cast(IOBase, self._process.stdin)
        stdout = cast(IOBase, self._process.stdout)
        stdin.close()
        stdout.close()

        self._process.terminate()
        self._process.wait()

    @property
    @abstractmethod
    def command(self) -> List[str]: ...


class CaffeinateKeepRunning(_MacCaffeinate):
    mode_name = ModeName.KEEP_RUNNING

    # The cat command reads from stdin and echoes it to stdout. With no input,
    # it just waits indefinitely. This is a trick to force stop caffeinate if
    # the python process is killed abruptly. In this situation, the stdin pipe
    # will be closed by the OS, causing cat to exit, which in turn causes
    # caffeinate to exit as well. [1]
    #
    # Alternative option would be use -w PID, but that is not available on
    # OS X 10.8 Mountain Lion (2012)[2] or OS X 10.9 Mavericks (2013).[3]
    #
    # [1]: https://github.com/wakepy/wakepy/pull/572 and
    #      https://github.com/wakepy/wakepy/issues/571
    # [2]: OSX Daily 2022-08-03 article "Disable Sleep on a Mac from the
    #      Command Line with caffeinate".
    #      https://osxdaily.com/2012/08/03/disable-sleep-mac-caffeinate-command/
    # [3]: Mac OS X 10.9 manual.
    #      https://web.archive.org/web/20140604153141/https://developer.apple.com/library/mac/documentation/Darwin/Reference/ManPages/man8/caffeinate.8.html
    #      https://www.manpagez.com/man/8/caffeinate/osx-10.9.php

    command = ["caffeinate", "cat"]
    name = "caffeinate"


class CaffeinateKeepPresenting(_MacCaffeinate):
    mode_name = ModeName.KEEP_PRESENTING

    # About the "cat" command, see CaffeinateKeepRunning.
    # -d:  Create an assertion to prevent the display from sleeping.
    command = ["caffeinate", "-d", "cat"]
    name = "caffeinate"
