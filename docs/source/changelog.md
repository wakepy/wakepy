# Changelog

## wakepy 1.0.0
🗓️ Unreleased

### ✨ Features
- Decorator syntax: `@keep.running` and `@keep.presenting` and the helper functions `current_mode()`, `global_modes()` and `modecount()` ([#477](https://github.com/wakepy/wakepy/pull/477))
- Update the wakepy CLI printout: Adds the used Method and activated Mode to the printout ([#434](https://github.com/wakepy/wakepy/pull/434))
- Added `-v` (INFO) and `-vv` (DEBUG) verbosity flags for the [wakepy CLI command](https://wakepy.readthedocs.io/stable/cli-api.html). ([#439](https://github.com/wakepy/wakepy/pull/439))
- Add [Mode.method](https://wakepy.readthedocs.io/stable/api-reference.html#wakepy.Mode.method), [ActivationResult.method](https://wakepy.readthedocs.io/stable/api-reference.html#wakepy.ActivationResult.method) and [MethodActivationResult.method](https://wakepy.readthedocs.io/stable/api-reference.html#wakepy.MethodActivationResult.method) attributes, which are instances of [MethodInfo](https://wakepy.readthedocs.io/stable/api-reference.html#wakepy.MethodInfo) ([#459](https://github.com/wakepy/wakepy/pull/459), [#460](https://github.com/wakepy/wakepy/pull/460), [#464](https://github.com/wakepy/wakepy/pull/464))
- Make [Mode.active_method](https://wakepy.readthedocs.io/stable/api-reference.html#wakepy.Mode.active_method) a [MethodInfo](https://wakepy.readthedocs.io/stable/api-reference.html#wakepy.MethodInfo) instance (was a string) ([#459](https://github.com/wakepy/wakepy/pull/459))

### 🌱 Minor Enhancements
- Better error messages: When selected Method is not part of the selected Mode ([#427](https://github.com/wakepy/wakepy/pull/427)) and when a D-Bus -based method fails ([#438](https://github.com/wakepy/wakepy/pull/438)). Also more human-readable output from [`ActivationResult.get_failure_text()`](https://wakepy.readthedocs.io/stable/api-reference.html#wakepy.ActivationResult.get_failure_text) ([#547](https://github.com/wakepy/wakepy/pull/547)).
- Enhance Mode Activation Observability. Add logging (DEBUG and INFO level) for different parts in the Mode activation process. Show which methods are to be tried, and log any success and failure of activating a Mode. Improved the `ActivationResult.get_failure_text()` output. Added `NoMethodsWarning` which is issued if trying to activate a Mode with an empty list of methods. ([#411](https://github.com/wakepy/wakepy/pull/411)) 
- Add logging to every Method activation and deactivation step ([#469](https://github.com/wakepy/wakepy/pull/469))
- Improve logging: org.gnome.Sessionmanager and freedesktop methods ([#474](https://github.com/wakepy/wakepy/pull/474))
- Make ActivationWarning use proper stacklevel, so that issued warnings point to user code, and not into wakepy source code. ([#432](https://github.com/wakepy/wakepy/pull/432))

### 🐞 Bug fixes
- Fix ResourceWarning with caffeinate Method on macOS ([#479](https://github.com/wakepy/wakepy/pull/479))
- Fix prioritized order of Methods ([#429](https://github.com/wakepy/wakepy/pull/429)).
- Raise ContextAlreadyEnteredError (subclass of RuntimeError) if trying to use context manager twice without exiting first ([#476](https://github.com/wakepy/wakepy/pull/476))

### 📖 Documentation
- Add [CONTRIBUTING.md](https://github.com/wakepy/wakepy/blob/main/CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](https://github.com/wakepy/wakepy/blob/main/CODE_OF_CONDUCT.md) ([#513](https://github.com/wakepy/wakepy/pull/513), [#515](https://github.com/wakepy/wakepy/pull/515))
- Documentation page for [Post Keepawake behavior](https://wakepy.readthedocs.io/stable/post-keepawake-behavior.html). Documented the behavior on Windows, KDE and GNOME ([#472](https://github.com/wakepy/wakepy/pull/472))
- Simplify and clarify the documentation of the [Mode](https://wakepy.readthedocs.io/stable/api-reference.html#wakepy.Mode) ([#458](https://github.com/wakepy/wakepy/pull/458))

### 🚨 Backwards incompatible changes
- Deprecate `Mode.used_method`. Use `Mode.method`, instead ([464](https://github.com/wakepy/wakepy/pull/464))
- Deprecate `Mode.activation_result`. Use `Mode.result`, instead ([464](https://github.com/wakepy/wakepy/pull/464))
- Deprecate `ActivationResult.active_method`. Use `ActivationResult.method`, instead ([464](https://github.com/wakepy/wakepy/pull/464))
- Make the `Mode._from_name()` and `Mode._method_classes` private; Not part of the public API anymore ([#458](https://github.com/wakepy/wakepy/pull/458))
- The `Mode.active_method`, `Mode.used_method`, are now instances of the new ModeInfo (previously strings) ([#460](https://github.com/wakepy/wakepy/pull/460))
- The `ActivationResult.mode_name` is now always a string (instead of being a ModeName) ([#462](https://github.com/wakepy/wakepy/pull/462))
- The `ActivationResult.list_methods()` arguments are now keyword only ([#547](https://github.com/wakepy/wakepy/pull/547))

### 👷 Maintenance
- Add basic spellchecking using [codespell](https://github.com/codespell-project/codespell) ([#539](https://github.com/wakepy/wakepy/pull/539))
- Add more ruff checks ([#524](https://github.com/wakepy/wakepy/pull/524), [#525](https://github.com/wakepy/wakepy/pull/525), [#526](https://github.com/wakepy/wakepy/pull/526))
- Switch from isort to ruff (Thanks to [@honerop](https://github.com/honerop) for [#531](https://github.com/wakepy/wakepy/issues/531))
- Switch from black to ruff ([#523](https://github.com/wakepy/wakepy/pull/523))
- Add AGENTS.md for AI coding assistants ([#508](https://github.com/wakepy/wakepy/pull/508))
- Replace invoke (tasks.py) with just (.justfile) ([#509](https://github.com/wakepy/wakepy/pull/509))
- Switch to uv and remove tox ([#499](https://github.com/wakepy/wakepy/pull/499))
- Split testing pipelines into [Fast Tests 🚀](https://github.com/wakepy/wakepy/actions/workflows/fast-tests.yml) and [Full Tests 🔬](https://github.com/wakepy/wakepy/actions/workflows/full-tests.yml). Fast tests run on every push to PR, and Full tests run after merging to main and before creating a release. ([#530](https://github.com/wakepy/wakepy/pull/530))
- Fix development environment setup instructions and requirements on Windows ([#445](https://github.com/wakepy/wakepy/pull/445))
- Make Run Tox fail on Windows pipelines if pytest fails ([#442](https://github.com/wakepy/wakepy/pull/442)). There was a bug in the workflow file which could make the tests pass on Windows even if pytest fails.
- Fix flaky tests on pypy+windows ([#447](https://github.com/wakepy/wakepy/pull/447))
- Remove the AttributeError traceback when building docs on Windows/MacOS ([#449](https://github.com/wakepy/wakepy/pull/449))
- PyPy3.11, CPython 3.14, CPython 3.14t, CPython 3.15 and CPython 3.15t (free-threaded) tests in pipelines ([#482](https://github.com/wakepy/wakepy/pull/482), [#501](https://github.com/wakepy/wakepy/pull/501))
- Fix freezing of CLI when running pytest with --pdb on CPython 3.13.x and 3.14.0 ([#512](https://github.com/wakepy/wakepy/pull/512))

## wakepy 0.10.2
🗓️ 2025-04-21

### 🐞 Bug fixes
- Fix keep.running mode on KDE Plasma 6.x.x, when `plasmashell --version` output contained extra lines, such as "QThreadStorage: entry 3 destroyed before end of thread 0x61b4ee73d540" ([#417](https://github.com/wakepy/wakepy/pull/417)). Thanks to [@materemias](https://github.com/materemias) for [#415](https://github.com/wakepy/wakepy/issues/415).

### 👷 Maintenance
- Fix CI pipelines for Python 3.7 on linux ([#419](https://github.com/wakepy/wakepy/pull/419))
- Disallow TODO comments ([#410](https://github.com/wakepy/wakepy/pull/410))
- Fix: Cannot install -r requirements/requirements-test.txt ([#403](https://github.com/wakepy/wakepy/pull/403))

### 📖 Documentation
- Add manual testing instructions for Xfce ([#405](https://github.com/wakepy/wakepy/pull/405))
- Readme updates ([#412](https://github.com/wakepy/wakepy/pull/412) & [#413](https://github.com/wakepy/wakepy/pull/413))

## wakepy 0.10.1
🗓️ 2024-09-20

### 🐞 Bug fixes
- Fix the wakepy logo/text printed to CLI ([#400](https://github.com/wakepy/wakepy/pull/400))

## wakepy 0.10.0
🗓️ 2024-09-20

### 🏆 Highlights
- Wakepy has been available in conda-forge since 0.9.1. Now it's also documented.
- Warn instead of raise Exception by default if activating a Mode fails.


### ✨ Features
- Change default `on_fail` action to be "warn" instead of "error" (in {func}`keep.running <wakepy.keep.running>` and {func}`keep.presenting <wakepy.keep.presenting>` modes). ([#388](https://github.com/wakepy/wakepy/pull/388))
- Add support for BSD and other non-Linux Unix-like FOSS desktop systems. All systems running a supported Desktop Environment (currently: KDE, Gnome + other freedesktop compliant DEs) should be supported. ([#379](https://github.com/wakepy/wakepy/pull/379), [#385](https://github.com/wakepy/wakepy/pull/385))
- Add support for PyPy ([#393](https://github.com/wakepy/wakepy/pull/393),  [#396](https://github.com/wakepy/wakepy/pull/396))
- When running on an *unknown* platform, do not fail any Methods in the platform check phase anymore, but try to use each Method. This means for example that any system running GNOME that is not Linux (or BSD) could still use wakepy with the [org.gnome.SessionManager](https://wakepy.readthedocs.io/stable/methods-reference.html#org-gnome-sessionmanager) ([#379](https://github.com/wakepy/wakepy/pull/379))
- 🚨 CLI arguments: Change `-k, --keep-running` to be `-r, --keep-running` and `-p, --presentation` to be `-p, --keep-presenting`; Be more consistent with the naming of the [Modes](#wakepy-modes). The old alternatives are deprecated and will be removed in a future release. ([#356](https://github.com/wakepy/wakepy/pull/356))
- 🚨 Renamed [`PlatformName`](https://wakepy.readthedocs.io/v0.9.0.post1/api-reference.html#wakepy.core.constants.PlatformName) to [`PlatformType`](https://wakepy.readthedocs.io/v0.10.0/api-reference.html#wakepy.core.constants.PlatformType) and added new types: `ANY`, which means "any platform", `BSD`, meaning "any BSD system" in the future, but currently just FreeBSD / GhostBSD, and  `UNIX_LIKE_FOSS`, which means "Unix-like desktop environment, but FOSS". Includes: Linux and BSD. Excludes: Android (mobile), MacOS (non-FOSS), ChromeOS (non-FOSS). Only affects you if you have created custom [Method](https://wakepy.readthedocs.io/v0.9.0.post1/api-reference.html#wakepy.Method) subclasses.  ([#379](https://github.com/wakepy/wakepy/pull/379))
- Improve warnings and errors if platform is not supported ([#383](https://github.com/wakepy/wakepy/pull/383))

### 👷 Maintenance
- Fixed GitHub Release pipeline: Creates releases only from tags. Added automatic titles. Cannot accidentally publish with "main" tag. ([#328](https://github.com/wakepy/wakepy/pull/328), [#346](https://github.com/wakepy/wakepy/pull/346))
- Fixed: Tests failing on Fedora 40 ([#381](https://github.com/wakepy/wakepy/pull/381))
- Update various development time dependencies ([#389](https://github.com/wakepy/wakepy/pull/389))

### 📖 Documentation
- Update Installing instructions. Wakepy is available in conda-forge starting from version 0.9.1. ([#390](https://github.com/wakepy/wakepy/pull/390) + Thanks to [@thewchan](https://github.com/thewchan) for [wakepy-feedstock](https://github.com/conda-forge/wakepy-feedstock))
- Add Roadmap and improve the Supported Platforms docs ([#365](https://github.com/wakepy/wakepy/pull/365))
- Add logos and banners ([#370](https://github.com/wakepy/wakepy/pull/370), [#371](https://github.com/wakepy/wakepy/pull/371))

## wakepy 0.9.1
🗓️ 2024-06-04

### 🐞 Bug fixes
- The [SetThreadExecutionState](#windows-stes) Method may now have multiple modes (same or different) activated within the same python thread without them interfering with each other on activation or deactivation, as wakepy creates a *separate worker thread* for the single purpose of setting and keeping the thread execution flag each time you activate a mode with the `SetThreadExecutionState` wakepy.Method. ([#342](https://github.com/wakepy/wakepy/pull/342))
- Importing wakepy (0.8.0 and 0.9.0) messed up logging. In particular, the logging level was changed to WARNING due to direct call to `logging.debug()` instead of `logger.debug()`. ([#344](https://github.com/wakepy/wakepy/pull/344)). Thanks to [@reidswanson](https://github.com/reidswanson) for reporting it.
- 👷 Fixed running the dev command `inv test` on Windows ([#339](https://github.com/wakepy/wakepy/pull/339), [#341](https://github.com/wakepy/wakepy/pull/341))


## wakepy 0.9.0.post1
🗓️ 2024-06-01

### 📖 Documentation
- Update docs and README after 0.8.0 & 0.9.0 releases ([#331](https://github.com/wakepy/wakepy/pull/331))


## wakepy 0.9.0
🗓️ 2024-05-31

### ✨ Features
- Support keep.running mode in KDE Plasma 5.12.90 and newer through the [org.freedesktop.PowerManagement](#org-freedesktop-powermanagement) method. It may also be used on other DEs which implement this older freedesktop.org D-Bus interface (but not Xcfe). ([#324](https://github.com/wakepy/wakepy/pull/324))
- Cooler CLI spinner ([#309](https://github.com/wakepy/wakepy/pull/309), [#323](https://github.com/wakepy/wakepy/pull/323))

### 📖 Documentation
- Document that the [org.freedesktop.ScreenSaver](org-freedesktop-screensaver) method for keep.presenting mode also supports KDE Plasma. ([#324](https://github.com/wakepy/wakepy/pull/324))
- Update dev docs ([#308](https://github.com/wakepy/wakepy/pull/308))
- Mention that shell should be restarted for wakepy CLI tool ([#321](https://github.com/wakepy/wakepy/pull/321))
- Fix: Supported Platforms table background does not support dark mode ([#316](https://github.com/wakepy/wakepy/pull/316))

## wakepy 0.8.0
🗓️ 2024-05-26

### 🏆 Highlights
- This is a basically a complete rewrite of wakepy. It adds support for keep.running mode on Gnome, on-fail action, possibility to control the used methods and their priority, more information about the used methods and the activation process and possibility to exit the mode early. In addition, testing and CI pipelines were updated to ease maintenance.

### ✨ Features
- Modes support [on-fail actions](#on-fail-action) ("error", "warn", "pass" or a callable). ([#182](https://github.com/wakepy/wakepy/pull/182))
- It is now possible to [select the used wakepy.Methods](#how-to-white-or-blacklist-methods) with `methods` and  `omit` and to [change the priority order](#how-to-control-order-of-methods) of methods with `methods_priority`. ([#75](https://github.com/wakepy/wakepy/issues/75))
- Added [org.gnome.SessionManager](#org-gnome-sessionmanager) method which adds support for keep.running mode for users with Gnome Desktop Environment. ([#51](https://github.com/wakepy/wakepy/pull/51), [#138](https://github.com/wakepy/wakepy/pull/138), [#278](https://github.com/wakepy/wakepy/pull/278), [#282](https://github.com/wakepy/wakepy/pull/282))
- {class}`ActivationResult <wakepy.ActivationResult>` objects ([#57](https://github.com/wakepy/wakepy/pull/57), [#258](https://github.com/wakepy/wakepy/pull/258), [#270](https://github.com/wakepy/wakepy/pull/270)) in {attr}`Mode.activation_result <wakepy.Mode.activation_result>` which give more detailed information about the activation process.
- Possibility to exit from a mode context manager early with {class}`ModeExit <wakepy.ModeExit>`  ([#72](https://github.com/wakepy/wakepy/pull/72))
- It's now possible to check the active and used method from the Mode instance using the {attr}`Mode.active_method <wakepy.Mode.active_method>` and  {attr}`Mode.used_method <wakepy.Mode.used_method>` ([#268](https://github.com/wakepy/wakepy/pull/268))
- Added possibility to use any dbus python implementation through the {class}`DBusAdapter <wakepy.DBusAdapter>`. By default uses jeepney through {class}`JeepneyDBusAdapter <wakepy.JeepneyDBusAdapter>`  (See: [#45](https://github.com/wakepy/wakepy/issues/45))
### 🚨 Backwards incompatible
- Removed `set_keepawake` and `unset_keepawake functions` and the `keepawake` context manager. These were deprecated in 0.7.0 and are replaced with the new api: {func}`keep.running() <wakepy.keep.running>` and {func}`keep.presenting() <wakepy.keep.presenting>` context managers. ([#85](https://github.com/wakepy/wakepy/pull/85))
- Renamed the CLI argument `-s, --keep-screen-awake` to `-p, --presentation`. The old ones were deprecated in 0.7.0. ([#179](https://github.com/wakepy/wakepy/pull/179/))
- If Mode activation fails, raise {class}`ActivationError <wakepy.ActivationError>` by default. Previously there was no "on fail" action, but users needed to check the `result.success` to make sure the activation was successful.
- The org.freedesktop.ScreenSaver based method is not used on keep.running mode. Systems supporting org.freedesktop.ScreenSaver which are not running Gnome will have no keep.running method until it gets implemented. By default wakepy will raise a wakepy.ActivationError if keep.running is used on such system. Either use keep.preseting mode, or wait or provide a PR.
- The [WAKEPY_FAKE_SUCCESS](#WAKEPY_FAKE_SUCCESS) check is done *before* trying any wakepy Methods (previously, it was used when all the tried methods have failed)
- Add [WAKEPY_FORCE_FAILURE](#WAKEPY_FORCE_FAILURE) environment variable which can be used to force activation failure (for testing/development) ([#542](https://github.com/wakepy/wakepy/pull/542))

### 🐞 Bug fixes
- The org.freedesktop.ScreenSaver based method is only used in keep.presenting mode. Previously, it was used on keep.running mode on Linux. ([#46](https://github.com/wakepy/wakepy/issues/46), [#136](https://github.com/wakepy/wakepy/issues/136))
- Still going to sleep - running Fedora 36 ([#18](https://github.com/wakepy/wakepy/issues/18))

### 📖 Documentation
- Rewritten the docs ([#193](https://github.com/wakepy/wakepy/pull/193), [#194](https://github.com/wakepy/wakepy/pull/194), [#196](https://github.com/wakepy/wakepy/pull/196), [#197](https://github.com/wakepy/wakepy/pull/197), [#198](https://github.com/wakepy/wakepy/pull/198), [#200](https://github.com/wakepy/wakepy/pull/200), [#244](https://github.com/wakepy/wakepy/pull/244), [#271](https://github.com/wakepy/wakepy/pull/271), [#272](https://github.com/wakepy/wakepy/pull/272), [#285](https://github.com/wakepy/wakepy/pull/285), [#286](https://github.com/wakepy/wakepy/pull/286))
- Remove /en/ from the URL and rename latest to stable ([#250](https://github.com/wakepy/wakepy/pull/250))

### 👷 Maintenance
- Made the CI tests mandatory for every PR (previously manual) ([#191](https://github.com/wakepy/wakepy/pull/191))
- 100% test coverage + use branch coverage instead of line coverage + enforce 100% coverage ([#221](https://github.com/wakepy/wakepy/pull/221), [#222](https://github.com/wakepy/wakepy/pull/222))
- Run black+isort+ruff also on tests ([#224](https://github.com/wakepy/wakepy/pull/224))
- Run mypy also on tests + fix the new mypy issues ([#227](https://github.com/wakepy/wakepy/pull/227))
- Add tests for Python 3.12 and 3.13. Now test all supported versions of python on linux, and oldest and newest supported versions on MacOS and Windows.  ([#160](https://github.com/wakepy/wakepy/pull/160), [#236](https://github.com/wakepy/wakepy/pull/236), [#273](https://github.com/wakepy/wakepy/pull/273))
- Pin docs and tests dependencies ([#220](https://github.com/wakepy/wakepy/pull/220))
- Build docs in CI tests to prevent breaking docs ([#211](https://github.com/wakepy/wakepy/pull/211))
- Run tox and pipeline tests against build wheel instead of the source tree ([#231](https://github.com/wakepy/wakepy/pull/231), [#236](https://github.com/wakepy/wakepy/pull/236))
- Build both, sdist (tar.gz) and wheel (.whl). 0.7.x had just wheels and <=0.6.x just dist. Start using setuptools-scm and switch from flit to setuptools ([#235](https://github.com/wakepy/wakepy/pull/235)).
- Add invoke commands ([#223](https://github.com/wakepy/wakepy/pull/223))
- Add automatic publishing GitHub workflow ([#238](https://github.com/wakepy/wakepy/pull/238))
- Limit docstrings and comments to 79 characters ([#207](https://github.com/wakepy/wakepy/pull/207))
- WakepyFakeSuccess Method ([#152](https://github.com/wakepy/wakepy/pull/152)) instead of using some custom logic with `WAKEPY_FAKE_SUCCESS`.
- Split package extras: dev, doc, test and check (was: doc, dev) ([#213](https://github.com/wakepy/wakepy/pull/213)) and start using requirements-*.txt instead of misusing extras ([#228](https://github.com/wakepy/wakepy/pull/228))
- Ruff: Update from 0.0.270 to 0.3.2 ([#206](https://github.com/wakepy/wakepy/pull/206)), use `--no-fix` in tox ([#208](https://github.com/wakepy/wakepy/pull/208)), Stricter ruff rules: W291 ([#209](https://github.com/wakepy/wakepy/pull/209))
- Black: Update from 23.3.0 to 24.2.0 and reformat ([#217](https://github.com/wakepy/wakepy/pull/217))
- Isort: Update from 5.12.0 to 5.13.2 ([#218](https://github.com/wakepy/wakepy/pull/218))
- Mypy: Update from 1.3.0 to 1.9.0 ([#219](https://github.com/wakepy/wakepy/pull/219)), stricter settings; `disallow_untyped_defs = true` ([#242](https://github.com/wakepy/wakepy/pull/242)), `disallow_any_unimported = true` and `warn_unused_ignores = true` ([#243](https://github.com/wakepy/wakepy/pull/243))
- Make wakepy statically typed: Add py.typed ([PEP 561](https://peps.python.org/pep-0561/)) to advertise that wakepy is a fully typed package ([#232](https://github.com/wakepy/wakepy/pull/232)), add mypy checks on 3.7-3.12 ([#265](https://github.com/wakepy/wakepy/pull/265))
- Other tox improvements ([#233](https://github.com/wakepy/wakepy/pull/233))
- Convert from flat layout to src layout ([#234](https://github.com/wakepy/wakepy/pull/234))
- Cleanup .gitignore ([#237](https://github.com/wakepy/wakepy/pull/237))

## wakepy 0.7.2
🗓️ 2023-09-27

### 🐞 Bug fixes
- The CLI API on python 3.7 and python 3.8. Thanks to [Aymane11](https://github.com/Aymane11) for [PR #50](https://github.com/wakepy/wakepy/pull/50)

## wakepy 0.7.1
🗓️ 2023-06-11

### 🐞 Bug fixes
- `keep.running` and `keep.presenting` return an object `m` with `success` value of `True`.

## wakepy 0.7.0
🗓️ 2023-06-11

### ✨ Features
- New API: `keep.running()` and `keep.presenting()` context managers. These are currently simple wrappers of the old methods but the internals will be re-written in a future version.
- The context managers now return the result of the action, `m`. Users may check with `m.success` if changing the mode was successful.
- Possibility to fake successful change of mode with `WAKEPY_FAKE_SUCCESS` (for CI / tests).
### 🐞 Bug fixes
- No exceptions anymore on import-time. All exceptions should be handled now gracefully, and user is informed if switching to a `keep.running` or `keep.presenting` mode failed.

### ⚠️ Deprecations
- Old Python API:  The `keepawake()`, `set_keepawake` and `unset_keepwake`. These will be removed in a future version of wakepy. Use `keep.running()`or `keep.presenting()`, instead.
- The `-s, --keep-screen-awake` option of the `wakepy` CLI command. Use `-p, --presentation ` option, instead.

### 📖 Documentation
- Created Readthedocs pages

### 👷 Maintenance
- Added manual CI tests
- Start using tox
- Enforce pass in isort, black, ruff and mypy in tests

## wakepy 0.6.0
🗓️ 2023-02-27

### ✨ Features
- Support for using wakepy without sudo on linux! There are now D-bus solutions (1) using  jeepney and (2) using dbus-python (libdbus). Thanks to [Stehlampe2020](https://github.com/Stehlampe2020) for the dbus-python based solution ([PR #22](https://github.com/np-8/wakepy/pull/22)) and [NicoWeio](https://github.com/NicoWeio) for raising  [Issue #17](https://github.com/np-8/wakepy/issues/17).
- Linux+systemd approach has sudo check. The program won't start without `SUDO_UID` environment variable set.

## wakepy 0.5.0
🗓️ 2021-12-15

### ✨ Features
- wakepy ascii art text, version and options will be printed in console if wakepy launched with the CLI
- The `wakepy` executable for CLI is installed when `wakepy` is installed with `pip`.

## wakepy 0.4.4
🗓️ 2021-08-30

### 🐞 Bug fixes
- Keeping screen awake on Mac ([#13](https://github.com/np-8/wakepy/issues/13)). Fixed in [PR #15](https://github.com/np-8/wakepy/pull/15). Thanks to [mikeckennedy](https://github.com/mikeckennedy).

## wakepy 0.4.3
🗓️ 2021-08-28

### 🐞 Bug fixes
- Raising `TypeError: a bytes-like object is required, not 'str'` if trying to use on MacOS (Python 3.9) ([#11](https://github.com/np-8/wakepy/issues/11)). Thanks to [mikeckennedy](https://github.com/mikeckennedy) for [PR #12](https://github.com/np-8/wakepy/pull/12).

## wakepy 0.4.2
🗓️ 2021-08-10

### 🐞 Bug fixes
- Raising `FileNotFoundError` if trying to use on MacOS. Previous implementation had a bug ([#9](https://github.com/np-8/wakepy/issues/9)). Thanks to [matacoder](https://github.com/matacoder) for [PR #10](https://github.com/np-8/wakepy/pull/10).

## wakepy 0.4.1
🗓️ 2021-06-15

### 🐞 Bug fixes
- Raising `NotImplementedError` if trying to use on Linux without `systemctl`. Previous implementation had a bug. ([#8](https://github.com/np-8/wakepy/issues/8))


## wakepy 0.4.0
🗓️ 2021-06-09

### ✨ Features
- `keepawake` context manager. ([#6](https://github.com/np-8/wakepy/pull/6)). Thanks to [HoustonFortney](https://github.com/HoustonFortney).

## wakepy 0.3.2
🗓️ 2021-06-06

### 🐞 Bug fixes
- Raising `NotImplementedError` if trying to use on Linux without `systemctl`. ([#3](https://github.com/np-8/wakepy/pull/3))

## wakepy 0.3.1
🗓️ 2021-06-02

### 🐞 Bug fixes
- The package in PyPI did not have any content

## wakepy 0.3.0
🗓️ 2021-05-05

### ✨ Features
- Linux & OSX support. Thanks for [rileyyy](https://github.com/rileyyy).