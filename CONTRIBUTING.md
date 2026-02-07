# Contributing to wakepy

Thank you for your interest in contributing to wakepy! We're excited to have you here. Whether you're fixing a typo, adding a new feature, or testing on your platform, every contribution helps make wakepy better for everyone.

## Table of Contents

1. [How to Contribute](#1-how-to-contribute)
2. [Development Environment Setup](#2-development-environment-setup)
3. [Git Workflow](#3-git-workflow)
4. [Introduction to the wakepy repo](#4-introduction-to-the-wakepy-repo)
5. [Development Workflow](#5-development-workflow)
6. [Testing](#6-testing)
7. [Code Standards](#7-code-standards)
8. [Adding support for a new Platform/DE](#8-adding-support-for-a-new-platformde)
9. [Documentation](#9-documentation)
10. [FAQ](#10-faq)
11. [Release Process](#11-release-process-for-maintainers)
12. [Platform-Specific Setup Notes](#12-platform-specific-setup-notes)


## 1. How to Contribute

There are many ways to contribute to wakepy, and all of them are much appreciated 🙌

### 💻 Coding Contributions

For **small and/or localized code changes** such as:
- Bug or typo fixes
- Small, localized code improvements
- [New platform/DE support](#adding-support-for-a-new-platformde)

You can *directly submit a pull request* without creating an issue first. For **larger or structural changes**, such as:

- New features
- Significant refactoring
- Breaking changes

Please create an [issue](https://github.com/wakepy/wakepy/issues) first to discuss your proposed changes. This helps ensure that:
- Your contribution aligns with the project's goals
- You don't spend time on something that might not be accepted
- We can provide guidance and feedback early in the process

### 🧪 Testing on Different Platforms

Testing wakepy on different systems is incredibly valuable. If you try wakepy on your setup, please report your results—even if everything works fine!

- Operating system and version
- Desktop environment and version (if Linux/BSD)
- wakepy version

👉 See [How to test wakepy Modes?](https://wakepy.readthedocs.io/stable/test-manually.html) for testing instructions.

### 💡 Proposing Features

Have an idea for improvement? Create an [issue](https://github.com/wakepy/wakepy/issues) to discuss it! Explain:
- What problem the feature solves
- How you envision it working
- Any alternative approaches you've considered


### 📚 Improving Documentation

[Documentation improvements](https://github.com/wakepy/wakepy/issues?q=is%3Aissue%20state%3Aopen%20label%3A%22Type%3A%20Documentation%22) are always welcome and great for first-time contributors. For example:
- Fix typos or unclear explanations
- Add examples
- Update outdated information

## 2. Development Environment Setup

You can develop wakepy in two ways:

### Option 1: Developing Locally

**Prerequisites:**
- [uv](https://docs.astral.sh/uv/getting-started/installation/) package manager
- [just](https://github.com/casey/just) command runner

**Setup:**
1. Fork and clone the wakepy repository
2. Install all dependencies (run in the root folder):
   ```bash
   uv sync
   ```
3. Verify everything works:
   ```bash
   just test
   ```

➜ FreeBSD user? See [Platform-Specific Setup Notes](#freebsd) below

### Option 2: Developing Inside a Devcontainer

[Devcontainers](https://code.visualstudio.com/docs/devcontainers/containers) provide a pre-configured development environment with all necessary tools installed and ready to use. They are supported by many editors, including [VS Code](https://code.visualstudio.com/docs/devcontainers/containers), [PyCharm](https://www.jetbrains.com/help/pycharm/connect-to-devcontainer.html), [Zed](https://zed.dev/docs/dev-containers), [Cursor](https://www.vcluster.com/blog/cursor-with-devpod) and [Windsurf](https://docs.windsurf.com/windsurf/advanced#dev-containers).

**Why use a devcontainer?**
- **Consistent environment** across different machines and contributors - no "works on my machine" issues
- **Isolated sandbox** perfect for running AI agents and experimental tools without affecting your host system
- **Zero local setup** - no need to install Python, uv, just, or other dependencies on your machine

**Quick Start:**
1. Open the repository a supported editor
2. When prompted, click "Reopen in Container" (or use Command Palette: "Dev Containers: Reopen in Container")
3. Wait for the container to build and start
4. Run `just test` to verify

**Want to add custom tools like AI agents?**: You could add for example these features to add claude-code, codex and custom firewall rules (Edit [settings.json](https://code.visualstudio.com/docs/getstarted/settings#_settingsjson) in VS Code):

```
{
  "dev.containers.defaultFeatures": {
    "ghcr.io/w3cj/devcontainer-features/firewall@sha256:f8ae63faf64094305ef247befc0a9c66eecd7a01768df0cc826c7d4a81a92bfc": {
      "verbose": true,
      "pypi": true,
      "anthropicApi": true,
      "openaiApi": true,
      "googleAiApi": true,
      "vscodeMarketplace": true
    },
    "ghcr.io/fohrloop/devcontainer-features/codex@sha256:7d78dad69447100e6694d4eb73b4307566c07e678f3f346d06e0c6fe37ef959c": {},
    "ghcr.io/fohrloop/anthropics-devcontainer-features-fork/claude-code@sha256:f76bc7179de085269881172935f6c5541321478f607c129872b0881d7109d5bf": {}
  }
}
```

For more details on adding extensions, dotfiles, and features, see [.devcontainer/CUSTOMIZATIONS.md](.devcontainer/CUSTOMIZATIONS.md).

## 3. Git Workflow

- The **`main`** branch is the only long-living branch. New code is merged into it through Pull Requests.
- Create a local short-lived feature branch for development.
- After done with your changes, push the changes into the remote of the forked repo, and create a PR against main branch in the wakepy repository.

## 4. Introduction to the wakepy repo

### Key Files


```
src/wakepy/
├── __init__.py                    Public API exports
├── __main__.py                    Command-line interface
├── modes/
│   └── keep.py                    User-facing API (keep.running and keep.presenting)
├── core/
│   ├── mode.py                    Mode logic and lifecycle management
│   ├── method.py                  Method base class (for subclassing all Methods)
│   ├── prioritization.py          Method selection and prioritization logic
│   ├── activationresult.py        Result types (ActivationResult, MethodActivationResult)
│   ├── platform.py                Platform detection utilities
│   ├── constants.py               Core enums (PlatformType, ModeName, StageName, ...)
│   └── dbus.py                    D-Bus abstractions and utilities
├── methods/
│   ├── windows.py                 Windows-specific methods (SetThreadExecutionState)
│   ├── macos.py                   macOS-specific methods (caffeinate)
│   ├── gnome.py                   GNOME desktop methods
│   └── freedesktop.py             Freedesktop/D-Bus methods
└── dbus_adapters/
    └── jeepney.py                 Jeepney adapter for D-Bus communication

tests/
├── conftest.py                    Global pytest fixtures
├── unit/                          Unit tests with mocked dependencies
└── integration/                   Platform-specific integration tests

docs/source/
└── changelog.md                   Project changelog

pyproject.toml                     Build configuration, dependencies, and tool settings
.justfile                          Just commands (format, check, docs, test, build)
```

### Understanding the Main Logic

If you want to understand how wakepy works internally, start from any of the public factory functions (e.g. `keep.presenting()` or `keep.running()` in [modes/keep.py](src/wakepy/modes/keep.py)). These create a `wakepy.Mode` instance which is defined in [core/mode.py](src/wakepy/core/mode.py). The starting point for entering a mode is `Mode.__enter__()` in [mode.py](src/wakepy/core/mode.py).

## 5. Development Workflow

This project uses [just](https://github.com/casey/just) as a command runner. To see all available commands, run:

```bash
just
```

**Available commands**:

- **`just test`** - Run tests with coverage (pass any pytest arguments, e.g. `just test --pdb`, `just test -k test_name`)
- **`just format`** - Format code using ruff
- **`just check`** - Static checking of code, linting, formatting checks, spell checking, etc.
- **`just docs`** - Build and serve the documentation with live-reload
- **`just build`** - Build the package (sdist and wheel)

### Development Iteration Cycle

Always format and verify your changes before creating a PR:

```bash
just format
just test
```

## 6. Testing

### Test Commands (from smallest to largest iteration cycle)

1\. **Single test**: Run a specific test on single python version (tests against source tree)
   ```bash
   uv run python -m pytest tests/unit/some.py::somefunc
   ```
2\. **Full check**: Run tests, check coverage, and run formatting checks (tests against installed version)
   ```bash
   just test
   ```

3\. **Test with few different OS + python versions** ([Fast Tests 🚀](https://github.com/wakepy/wakepy/actions/workflows/fast-tests.yml) in GitHub): 
* Starts automatically in GitHub Actions every time a PR is updated. Can also be started manually.
* Runs tests and check test coverage (against built wheel), run formatting and static typing checks (against source tree)
* This test is relatively fast. Contains oldest supported python on Linux, newest stable release on Linux, Windows and macOS.

4\. **Rigorous tests with multiple different OS + python versions** ([Full Tests 🔬](https://github.com/wakepy/wakepy/actions/workflows/full-tests.yml) in GitHub): 
* Starts automatically in GitHub Actions every time after a PR is merged into main, and just before a release is published. Can also be started manually.
* Same as "Fast Tests 🚀" but with more OS + Python version combinations.

### Running Tests Against Specific Python Version Locally

Use `uv sync --python <version>` followed with `uv run --python <version>`. For example:

```bash
uv sync --python python3.8 --group test
uv run --python python3.8 pytest
```

To switch back:

```bash
uv sync
```

You can see the list of available python versions with `uv python list`. The list is tied to the installed uv version.


## 7. Code Standards

- **Type hints**: All code must be fully typed (mypy strict mode)
- **Code style**: Follow the project's formatting (enforced by ruff)
- **Structure**: Top-level functions before subfunctions
- **Readability**: Code should be easily readable and well-documented
- **Tests**: When writing tests, use pytest with classes, and use fixtures when applicable. Try to avoid I/O in tests.
- **Docs**: Use Nympy docstyle, and make sure docstrings are parsed correctly when documentation is built (if part of public API).

## 8. Adding support for a new Platform/DE

1. Create new file in `src/wakepy/methods/` (e.g., `new_platform.py`)
2. Inherit from `Method` base class. Important parts:
   - `caniuse()`: Check if method can be used
   - `enter_mode()`: Activate wakelock
   - `exit_mode()`: Deactivate wakelock
   - `mode_name`: Name of the wakepy mode
   - `name`: Name of the method
   - `supported_platforms`
3. Add unit tests in `tests/unit/test_methods/`
4. Update documentation in `docs/source/`

## 9. Documentation

The documentation uses Sphinx with MyST (Markdown) and the source code lives at `./docs/source`.

### Building Documentation Locally

For debugging/testing docs with autobuild:

```bash
just docs
```

### Documentation URLs

- **Stable** ([wakepy.readthedocs.io/stable/](https://wakepy.readthedocs.io/stable/)): Latest release (tagged version), as documented [here](https://docs.readthedocs.io/en/stable/versions.html)
- **Latest** ([wakepy.readthedocs.io/latest/](https://wakepy.readthedocs.io/latest/)): Follows the HEAD of the `main` branch (development version)
- **Versioned**: Released versions X.Y.Z can be accessed at `wakepy.readthedocs.io/vX.Y.Z/`

### Deploying Documentation

Just merge in main on GitHub, and readthedocs will automatically build documentation (by default, the "latest"). The settings can be adjusted [here](https://readthedocs.org/dashboard), and you can see the history of builds [here](https://app.readthedocs.org/projects/wakepy/).

Versions selected for documentation are selected in the readthedocs UI. Select one version per `major.minor` version (latest of them) from the git tags.


## 10. FAQ

### Do I need to complete the entire PR myself?

Not at all! Partial contributions are welcome and appreciated. If you start working on something but can't finish it, or if you'd like feedback before continuing, feel free to open a PR with what you have. Just let us know in the PR description that it's a work in progress or that you'd like us to take it from there. We're happy to collaborate and help get your contribution across the finish line.

### Do I need to test on all platforms?

No. Most contributors don't have access to all platforms (Windows, macOS, Gnome, KDE, etc.). Just test on the platform you have available. The CI pipeline will run tests on multiple platforms, and maintainers or other contributors can help test on platforms you don't have access to.


## 11. Release Process (for Maintainers)

The release process is automated, but changelog creation takes a few manual steps.

### Steps

1. Add changelog and release date to `docs/source/changelog.md`
2. Merge the changes to main
3. Locally, fetch and checkout latest main, and create a new git tag for the release. Releases use [Semantic Versioning](https://semver.org/) with format `v[major].[minor].[patch]`; e.g. v1.2.0 or v2.2.0.
4. Push the tag to GitHub. Verify that the tag commit is same as latest main commit
5. Go to GitHub and run the [action for release](https://github.com/wakepy/wakepy/actions/workflows/publish-a-release.yml) *on the tag vX.Y.Z*
6. After release, go to GitHub Releases at https://github.com/wakepy/wakepy/releases/. Start editing the description of the latest release
7. Copy-paste the changelog from https://wakepy.readthedocs.io/stable/changelog.html to the description. Add titles (`###`) and list markers (`-`) back
8. Copy-paste the text further to a text editor and find and replace "wakepy.readthedocs.io/stable" with "wakepy.readthedocs.io/X.Y.Z" to keep the changelog links working even after later releases
9. Copy-paste back to the GitHub Releases, and save


## 12. Platform-Specific Setup Notes

### FreeBSD

- To install ruff, you need a recent version of Rust. Recommended to use rustup. You'll also need gmake
- You'll also need the Standard Python binding to the SQLite3 library (py3**-sqlite3)
