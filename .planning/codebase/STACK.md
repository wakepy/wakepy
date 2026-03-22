# Technology Stack

**Analysis Date:** 2026-02-19

## Languages

**Primary:**
- Python 3.7+ - Core library and CLI implementation
- Platform-specific OS APIs: C (Windows kernel32.dll), macOS caffeinate binary, D-Bus (Linux/BSD)

## Runtime

**Environment:**
- Python 3.7, 3.8, 3.9, 3.10, 3.11, 3.12, 3.13, 3.14, 3.15 (via CPython)
- PyPy 3.8, 3.11 (alternative implementation)
- Free-threaded Python variants (3.14t, 3.15t)
- Cross-platform: Windows, macOS, Linux (all major distributions), BSD (FreeBSD, OpenBSD, NetBSD, DragonFly), SunOS, AIX, Minix

**Package Manager:**
- `uv` - Modern Python package manager (v0.9.18 in CI)
- Python version: 3.14 (development/CI default)

## Frameworks

**Core:**
- None (stdlib only) - Pure Python implementation with no web framework dependencies

**Build/Package:**
- `setuptools` 69.1.0 - Package building
- `setuptools_scm` 8.1.0 - Automatic version management from git tags
- `build` - Build system abstraction

**Testing:**
- `pytest` (>=8.3.5 for 3.13+) - Test runner
- `pytest-cov` 4.1.0 (Python 3.7) / 5.0.0 (Python 3.8+) - Coverage reporting
- `coverage-conditional-plugin` >=0.9.0 - Platform-conditional coverage rules

**Type Checking:**
- `mypy` 1.4.1 (Python 3.7) / 1.11.2 (Python 3.8+) - Strict static type checking
- `typing-extensions` - Backport for Python <3.10 (Literal, TypedDict, ParamSpec)

**Code Quality:**
- `ruff` 0.6.5 - Linter and formatter (isort, pycodestyle, Pyflakes, bandit, eradicate, boolean-trap)
- `codespell` >=2.4.1 - Spell checker

**Documentation:**
- Sphinx 7.2.6 - Documentation generator
- `sphinx-book-theme` 1.1.2 - Book-style documentation theme
- `myst-parser` 2.0.0 - Markdown support in Sphinx
- `pydata-sphinx-theme` 0.15.3 - Data-focused theme
- `numpydoc` 1.7.0 - NumPy documentation standard
- `sphinx-copybutton` 0.5.2 - Copy code blocks button
- `sphinx_design` 0.5.0 - Design components
- `sphinx-autobuild` 2024.4.16 - Auto-rebuild documentation on changes
- Additional: alabaster, mdit-py-plugins, markdown-it-py, accessible-pygments

**Development:**
- `IPython` - Interactive shell
- `zizmor` >=1.16.3 - Security linter for GitHub workflows

## Key Dependencies

**Critical:**
- `jeepney` >=0.7.1 - D-Bus communication for Linux/BSD systems (conditional: only installed on Unix-like FOSS platforms)

**Infrastructure:**
- None - No external service clients (no AWS SDK, database drivers, HTTP clients)

## Configuration

**Environment:**
- No required environment variables for core functionality
- Optional: `XDG_SESSION_DESKTOP` - Detects desktop environment (GNOME, KDE, XFCE, etc.) on Linux
- Platform detection: Via `platform.system()` and `os.name`

**Build:**
- `pyproject.toml` - Modern Python project configuration (setuptools, coverage, ruff, mypy, codespell)
- `.python-version` - Development Python version (3.14)
- `.github/workflows/*.yml` - CI/CD configuration
  - `build-and-run-tests.yml` - Build and multi-version test matrix
  - `fast-tests.yml` - Quick test subset
  - `full-tests.yml` - Comprehensive test suite
  - `publish-a-release.yml` - Release automation

**Development:**
- `.justfile` - Task runner commands (format, check, docs, test, build)
- `ruff` - Enforces line length 88 (Black-compatible), import sorting (isort), strict linting rules

## Platform Requirements

**Development:**
- Python 3.7+ (3.9+ for docs/dev/check dependency groups)
- uv package manager
- Git (for setuptools_scm version extraction)
- For documentation: Requires Python 3.9+

**Production:**
- Windows: Windows XP+ (for SetThreadExecutionState)
- macOS: OS X Mountain Lion 10.8+ (2012) for caffeinate
- Linux: Any distribution with D-Bus support
- BSD: FreeBSD, OpenBSD, NetBSD, DragonFly with D-Bus
- Unix-like: SunOS, AIX, Minix with D-Bus

**Type Safety:**
- Strict mypy mode enforced
  - `disallow_untyped_defs` - All functions typed
  - `disallow_any_generics` - No untyped generics
  - `disallow_any_unimported` - External modules must be typed
- Exception: Tests excluded from strict requirements

---

*Stack analysis: 2026-02-19*
