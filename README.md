![GitHub tag (latest by date)](https://img.shields.io/github/v/tag/wakepy/wakepy)&nbsp;![PyPI](https://img.shields.io/pypi/v/wakepy)&nbsp;![PyPI - Downloads](https://img.shields.io/pypi/dm/wakepy)&nbsp;[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)&nbsp;![mypy](https://img.shields.io/badge/mypy-checked-blue)&nbsp;![coverage](https://img.shields.io/badge/coverage-100%25-32bb13)
[![pyversions](https://img.shields.io/pypi/pyversions/wakepy.svg)](https://pypi.python.org/pypi/wakepy)&nbsp;![License](https://img.shields.io/github/license/wakepy/wakepy)

![](./docs/source/img/wakepy-banner.svg)

Cross-platform wakelock / keep-awake / stay-awake written in Python.

<!-- wakepy readme beginning -->
## What is wakepy?

Wakepy is a package with an Python API and a CLI tool for *keeping a system awake*. It has two main modes:

⌛ **Keeping CPU awake**:  For long running tasks. Inhibit the automatic, timer based sleep or suspend action, but allow screenlock and screensaver turning on and monitor turning off. *E.g.* for training machine learning models, video encoding and web scraping. (See: <a href="https://wakepy.readthedocs.io/stable/modes.html#keep-running-mode"><b><code>keep.running</code></b></a>)

🖥️ **Keeping screen awake**:  For long running tasks which require also the screen on and screenlock and screensaver inhibited.  *E.g.* for showing a video and dashboard / monitoring apps. (See: <a href="https://wakepy.readthedocs.io/stable/modes.html#keep-presenting-mode"><b><code>keep.presenting</code></b></a>)

## Supported runtime environments

Wakepy may keep the following systems awake. ⌛: <a href="https://wakepy.readthedocs.io/stable/modes.html#keep-running-mode">keep.running</a> mode, 🖥️:<a href="https://wakepy.readthedocs.io/stable/modes.html#keep-presenting-mode">keep.presenting</a> mode.


<table class="wakepy-table">
  <colgroup>
    <col style="width: 31%;">
    <col style="width: 55%;">
    <col style="width: 14%;">
  </colgroup>
  <thead>
    <tr>
      <th>Runtime environment</th>
      <th>Methods</th>
      <th>Modes</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Windows<sup>[1]</sup></td>
      <td><a href="https://wakepy.readthedocs.io/stable/methods-reference.html#setthreadexecutionstate">SetThreadExecutionState</a></td>
      <td>⌛ 🖥️</td>
    </tr>
    <tr>
      <td>macOS<sup>[2]</sup></td>
      <td><a href="https://wakepy.readthedocs.io/stable/methods-reference.html#macos-caffeinate">caffeinate</a></td>
      <td>⌛ 🖥️</td>
    </tr>
    <tr>
      <td>Unix + <a href="https://en.wikipedia.org/wiki/GNOME">GNOME</a><sup>[3]</sup></td>
      <td><a href="https://wakepy.readthedocs.io/stable/methods-reference.html#org-gnome-sessionmanager">org.gnome.SessionManager</a><br>
      <a href="https://wakepy.readthedocs.io/stable/methods-reference.html#org-freedesktop-screensaver">org.freedesktop.ScreenSaver</a></td>
      <td>⌛ 🖥️</td>
    </tr>
    <tr>
      <td>Unix + <a href="https://en.wikipedia.org/wiki/KDE_Plasma">KDE Plasma</a><sup>[4]</sup></td>
      <td><a href="https://wakepy.readthedocs.io/stable/methods-reference.html#org-freedesktop-powermanagement">org.freedesktop.PowerManagement</a><br>
      <a href="https://wakepy.readthedocs.io/stable/methods-reference.html#org-freedesktop-screensaver">org.freedesktop.ScreenSaver</a></td>
      <td>⌛ 🖥️</td>
    </tr>
    <tr>
      <td>Unix + <a href="https://en.wikipedia.org/wiki/Freedesktop.org">Freedesktop.org</a> DE<sup>[5]</sup></td>
      <td>
      <a href="https://wakepy.readthedocs.io/stable/methods-reference.html#org-freedesktop-powermanagement">org.freedesktop.PowerManagement</a><br>
      <a href="https://wakepy.readthedocs.io/stable/methods-reference.html#org-freedesktop-screensaver">org.freedesktop.ScreenSaver</a>
      </td>
      <td>⌛ 🖥️</td>
    </tr>
  </tbody>
</table>

Unix above refers to any Unix-like systems which might use such DEs, e.g. Linux or FreeBSD. See also: [Wakepy roadmap](#wakepy-roadmap).

## Installing

Wakepy supports CPython 3.7 to 3.15 (including the free-threaded versions) and PyPy 3.8 to 3.11, and may be installed from [PyPI](https://pypi.org/project/wakepy/) with

```
pip install wakepy
```

Wakepy can also be installed from conda-forge with
```
conda install wakepy
```
For more details and install options, see: [Installing documentation](https://wakepy.readthedocs.io/stable/installing.html).

<!-- wakepy readme at install before note -->
> [!NOTE]
> To get the `wakepy` <a href="https://wakepy.readthedocs.io/stable/cli-api.html">CLI command</a> working, you might need to restart the shell / terminal application.
<!-- wakepy readme at install after note -->

## Why wakepy?
Here's some reasons why you might want to consider using wakepy:


<dl>
  <dt>🙅🏼‍♂️ Non-disruptive methods ✅</dt>
  <dd>No mouse wiggling or pressing random keys like F15. Wakepy is completely non-disruptive. It uses the APIs and programs the system provides for keeping a system awake.</dd>
  <dt>🛡️ Safe to crash 💥</dt>
  <dd>No changing of any system settings; killing the process abruptly will not leave the keepawake on, and will not require any manual clean-up.</dd>
  <dt>🚨 For security reasons 🔒</dt>
  <dd>With <a href="https://wakepy.readthedocs.io/stable/modes.html#keep-running-mode"><b><code>keep.running</code></b></a> mode you can disable <i>just</i> the automatic suspend and keep the automatic screen lock untouched.</dd>
  <dt>🌐 You need a cross-platform solution 🦸</dt>
  <dd>Same code works on Windows, macOS and Linux on multiple different Desktop Environments.</dd>
  <dt>💪 You want to have more control ⚙️</dt>
  <dd>It is possible to whitelist or blacklist the used wakepy Methods. It is also possible to prioritize them and define a on-fail action in case activating a wakepy mode fails.</dd>
  <dt>✂️ You want to keep the amount of dependencies low 📦</dt>
  <dd>If you're running wakepy on Linux,  <a href="https://jeepney.readthedocs.io/">jeepney</A> (a dependecy free package) is required for D-Bus based methods. On Python 3.9 and earlier,  <a href="https://pypi.org/project/typing-extensions/">typing-extensions</a> is needed for typing. Otherwise: wakepy has no python dependencies.</dd>
  <dt>⚖️ Package needs to have a permissive licence ✔️</dt>
  <dd>Wakepy is licenced under permissive <a href="https://github.com/wakepy/wakepy/blob/main/LICENSE.txt">MIT License</a>.</dd>
</dl>


## Command line interface (CLI)

To keep system from sleeping, run

```
wakepy
```

For presentation mode, add `-p` flag. See also: <a href="https://wakepy.readthedocs.io/stable/cli-api.html">CLI API</a>.

## Basic usage within Python

In the simplest case, keeping a system running long running task with wakepy would be in python (See: <a href="https://wakepy.readthedocs.io/stable/modes.html#keep-running-mode">keep.running</a>):


```python
from wakepy import keep

@keep.running
def long_running_task():
    # Do something that takes a long time
```

If you want to *also* prevent screen lock and screen blank, use the <a href="https://wakepy.readthedocs.io/stable/modes.html#keep-presenting-mode">keep.presenting</a> mode:

```python
from wakepy import keep

@keep.presenting
def long_running_task():
    # Do something that takes a long time AND requires the display to stay on
```

<!-- wakepy decorator syntax note start -->
> [!NOTE]
> The [decorator syntax](https://wakepy.readthedocs.io/latest/user-guide.html#decorator-syntax) was added in wakepy version 1.0.0
<!-- wakepy decorator syntax note end -->


It's also possible to use the <a href="https://wakepy.readthedocs.io/stable/modes.html#keep-running-mode">keep.running()</a> and <a href="https://wakepy.readthedocs.io/stable/modes.html#keep-presenting-mode">keep.presenting()</a> as [context managers](https://wakepy.readthedocs.io/latest/user-guide.html#context-managers), like this:


```python
from wakepy import keep

with keep.running()
    ...
```

<!-- wakepy readme basic usage before tip -->

> [!TIP]
> See the [User Guide](https://wakepy.readthedocs.io/stable/user-guide.html) and the available wakepy [Modes](https://wakepy.readthedocs.io/stable/modes.html) and [Methods](https://wakepy.readthedocs.io/stable/methods-reference.html)


<!-- wakepy readme where used -->
## Where wakepy is used?

- [aTrain](https://github.com/JuergenFleiss/aTrain) — transcription of speech recordings utilizing machine learning models.
- [mpc-autofill](https://github.com/chilli-axe/mpc-autofill) — Automating MakePlayingCards' online ordering system
- [LiveboxMonitor](https://github.com/p-dor/LiveboxMonitor) — Graphical user interface for routers (French project)
- [FOLON-FO4Downgrader](https://github.com/Fallout-London/FOLON-FO4Downgrader) — Tool for reverting to a previous version of a game (Fallout 4)
- [BD_to_AVP](https://github.com/cbusillo/BD_to_AVP) — 3D Blu-ray to Apple Vision Pro converter
- [davlee1972/upscale_video](https://github.com/davlee1972/upscale_video) — Upscaling video using AI
- [AYAB - All Yarns Are Beautiful](https://github.com/AllYarnsAreBeautiful/ayab-desktop/) — Automated knitting software
- [minarca](https://github.com/ikus060/minarca) — Cross-platform data backup software
- [OceanOptics/Inlinino](https://github.com/OceanOptics/Inlinino) — Data logger for oceanography
- [cogent3/ensembl_tui](https://github.com/cogent3/ensembl_tui) —  Obtaining dumps of Ensembl MySQL databases
- [lakeshore](https://github.com/lakeshorecryotronics/python-driver) — Lake Shore instruments python Driver
- [UCSD-E4E/baboon-tracking](https://github.com/UCSD-E4E/baboon-tracking) — In pipelines of a Computer Vision project tracking baboons
- [pysimai](https://github.com/ansys/pysimai) — A Python wrapper for Ansys SimAI
- [viskillz-blender](https://www.sciencedirect.com/science/article/pii/S2352711023000249) — Generating assets of Mental Cutting Test exercises


## Links


- 🖤 GitHub: [github.com/wakepy/wakepy](https://github.com/wakepy/wakepy)
- 🐍 PyPI: [pypi.org/project/wakepy](https://pypi.org/project/wakepy/)
- 📖 Documentation: [wakepy.readthedocs.io/stable](https://wakepy.readthedocs.io/stable)
- 📝 Changelog: [wakepy.readthedocs.io/stable/changelog.html](https://wakepy.readthedocs.io/stable/changelog.html)


## Wakepy roadmap

Wakepy vision is to support *any*<sup>†</sup> environment which runs Python. The following runtime environments will get support in the future<sup>†</sup>. Please vote or comment on the issue to raise them towards top of priorities. I'm also happy to receive PRs or comments explaining how it could be implemented.

<sup>†</sup>: if technically possible.

<table class="wakepy-table">
  <colgroup>
    <col style="width: 50%;">
    <col style="width: 50%;">
  </colgroup>
  <thead>
    <tr>
      <th>Runtime environment</th>
      <th>Issue</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>WSL</td>
      <td><a href="https://github.com/wakepy/wakepy/issues/36">wakepy/#36</a></td>
    </tr>
    <tr>
      <td>cygwin</td>
      <td><a href="https://github.com/wakepy/wakepy/issues/363">wakepy/#363</a></td>
    </tr>
    <tr>
      <td>Unix + <a href="https://en.wikipedia.org/wiki/Cinnamon_(desktop_environment)">Cinnamon</a></td>
      <td><a href="https://github.com/wakepy/wakepy/issues/312">wakepy/#312</a></td>
    </tr>
    <tr>
      <td>Unix + <a href="https://en.wikipedia.org/wiki/Xfce">Xfce</a></td>
      <td><a href="https://github.com/wakepy/wakepy/issues/311">wakepy/#311</a></td>
    </tr>
    <tr>
      <td>Unix + <a href="https://en.wikipedia.org/wiki/MATE_(desktop_environment)">Mate</a></td>
      <td><a href="https://github.com/wakepy/wakepy/issues/314">wakepy/#314</a></td>
    </tr>
    <tr>
      <td>Unix + <a href="https://en.wikipedia.org/wiki/LXQt">LXQt</a></td>
      <td><a href="https://github.com/wakepy/wakepy/issues/313">wakepy/#313</a></td>
    </tr>
    <tr>
      <td>Unix + <a href="https://en.wikipedia.org/wiki/Systemd">systemd</a></td>
      <td><a href="https://github.com/wakepy/wakepy/issues/335">wakepy/#335</a></td>
    </tr>
    <tr>
      <td>ChromeOS</td>
      <td><a href="https://github.com/wakepy/wakepy/issues/364">wakepy/#364</a></td>
    </tr>
    <tr>
      <td>Android</td>
      <td><a href="https://github.com/wakepy/wakepy/issues/358">wakepy/#358</a></td>
    </tr>
    <tr>
      <td>Jupyter Notebook (hosted on eg. Google Colab)</td>
      <td><a href="https://github.com/wakepy/wakepy/issues/195">wakepy/#195</a></td>
    </tr>
    <tr>
      <td>Browser (Pyodide, PyPy.js, Brython, Transcrypt, Skulpt)</td>
      <td><a href="https://github.com/wakepy/wakepy/issues/362">wakepy/#362</a></td>
    </tr>
  </tbody>
</table>

If you have ideas or comments, please post yours on [wakepy/#317](https://github.com/wakepy/wakepy/discussions/317).

## Licenses

The contents of this repository are licensed with [MIT License](https://github.com/wakepy/wakepy/blob/main/LICENSE.txt), which is permissive and allows you to use the code as part of any application or library, commercial or not, with the following exception: The GitHub Invertocat logo used in the social share image is property of GitHub, downloaded from [github.com/logos](https://github.com/logos) and is used under the terms specified by GitHub.

---------------

## Footnotes

|                                                                                                                                             |
| ------------------------------------------------------------------------------------------------------------------------------------------- |
| <sup>[1]</sup> Windows XP or higher. Windows Server 2003 or higher.                                                                         |
| <sup>[2]</sup> Mac OS X 10.8 Mountain Lion (July 2012) or newer.                                                                            |
| <sup>[3]</sup> GNOME 2.24 (Sept 2008) onwards.                                                                                              |
| <sup>[4]</sup> KDE Plasma 5.12.90 (May 2018) onwards.                                                                                       |
| <sup>[5]</sup> Freedesktop.org compliant Desktop Environments on Unix-like (Linux/BSD) system which implements the listed D-Bus interfaces. |

<!-- wakepy readme after footnotes -->

