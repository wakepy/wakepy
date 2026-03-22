# External Integrations

**Analysis Date:** 2026-02-19

## APIs & External Services

**No external APIs** - Wakepy does not integrate with remote services, cloud platforms, or third-party APIs. All functionality uses native OS/Desktop Environment APIs.

## Data Storage

**Databases:**
- None - No database integration

**File Storage:**
- Local filesystem only - No cloud storage integration

**Caching:**
- None

## Authentication & Identity

**Auth Provider:**
- None - No authentication required

## Platform-Native OS/DE APIs

**Windows:**
- `SetThreadExecutionState` - Kernel32.dll function (native Windows API)
  - Location: `src/wakepy/methods/windows.py`
  - Implementation: `ctypes` module for FFI to kernel32.dll
  - Flags: ES_CONTINUOUS, ES_SYSTEM_REQUIRED, ES_DISPLAY_REQUIRED
  - No external dependencies

**macOS:**
- `caffeinate` - Native command-line tool (part of OS X 10.8+)
  - Location: `src/wakepy/methods/macos.py`
  - Implementation: Subprocess call to system binary
  - No external dependencies

**Linux & BSD (Desktop Environments):**
- D-Bus message bus - Inter-process communication protocol
  - Service: `org.freedesktop.ScreenSaver` (Freedesktop standard)
  - Service: `org.gnome.SessionManager` (GNOME-specific)
  - Service: `org.kde.Solid.PowerManagement` (KDE Plasma-specific)
  - Adapter: `JeepneyDBusAdapter` (`jeepney` library)
  - Location: `src/wakepy/dbus_adapters/jeepney.py`
  - Bus types: SESSION (for per-user) and SYSTEM (for system-wide)
  - D-Bus abstractions: `src/wakepy/core/dbus.py`
    - `DBusAddress` - Service/path/interface specification
    - `DBusMethod` - Method invocation specification
    - `DBusMethodCall` - Concrete method call with arguments
    - `DBusAdapter` - Abstract adapter for D-Bus implementations

**Freedesktop.org Standard Methods:**
- `src/wakepy/methods/freedesktop.py`
  - Implements cookie-based inhibitor pattern
  - Detects desktop environment via `XDG_SESSION_DESKTOP` environment variable
  - Supports: GNOME, KDE, XFCE, and any freedesktop.org-compliant DE

## Monitoring & Observability

**Error Tracking:**
- None

**Logs:**
- Python `logging` module (stdlib)
  - Location: All modules use `logger = logging.getLogger(__name__)`
  - No external log aggregation

## CI/CD & Deployment

**Hosting:**
- GitHub (source and releases)
- Read the Docs - Documentation hosting

**CI Pipeline:**
- GitHub Actions
  - Workflow: `.github/workflows/build-and-run-tests.yml`
  - Builds: Python wheels (sdist + wheel) via `uv build`
  - Tests: Multi-platform, multi-Python version matrix
    - Fast mode: Python 3.7 and 3.14 on Ubuntu, macOS, Windows
    - Full mode: Python 3.7-3.15, PyPy, free-threaded variants on Ubuntu; 3.7/3.14 on macOS/Windows
  - Artifact upload to GitHub
  - Workflow: `.github/workflows/publish-a-release.yml` - Release publishing
  - Actions: `actions/checkout`, `astral-sh/setup-uv`, `actions/upload-artifact`

**Build Tool:**
- `uv` - All builds use `uv build`
- Setuptools backend with setuptools_scm for versioning

## Environment Configuration

**Required env vars:**
- None - No required environment variables

**Optional env vars:**
- `XDG_SESSION_DESKTOP` (Linux) - Detects desktop environment
  - Values: KDE, XFCE, GNOME, or unset
  - Used in: `src/wakepy/core/platform.py` (platform debug info)
- `DESKTOP_SESSION` (Linux) - Additional session detection

**Secrets location:**
- None - No secrets required

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Special Integrations

**D-Bus Adapter Pattern:**
- Abstract: `DBusAdapter` (base class in `src/wakepy/core/dbus.py`)
- Concrete: `JeepneyDBusAdapter` (using `jeepney` library)
- Location: `src/wakepy/dbus_adapters/jeepney.py`
- Lazy-loaded via `__getattr__` in `src/wakepy/__init__.py` (only imported when needed)
- Handles: Method call marshalling, bus connection, message unwrapping

**Method Discovery & Registration:**
- Registry system: `src/wakepy/core/registry.py`
- Automatic registration of platform-specific methods
- Selection: `src/wakepy/core/prioritization.py` (chooses best available method per platform)

**No External Dependencies for Core:**
- The only external dependency is `jeepney` (D-Bus library), which is:
  - Conditional: Only installed on Linux/BSD systems (via environment markers in `pyproject.toml`)
  - Optional: Code gracefully handles missing D-Bus support
  - Lazy-loaded: Not imported unless actually used

---

*Integration audit: 2026-02-19*
