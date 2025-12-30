[private]
default:
  @just --list

# static checking of code, linting, formatting checks, etc.
check:
  uv run ruff check --no-fix src/wakepy tests/
  uv run ruff format --check src/wakepy tests/
  uv run mypy src/wakepy tests/

# Format code using ruff.
format:
  uv run ruff check --fix src/wakepy tests/
  uv run ruff format src/wakepy tests/

# Build and serve the documentation with live-reload.
docs:
    #!/usr/bin/env python3
    import platform
    import subprocess
    import sys

    if platform.system() == "Windows":
        print("***********************************************", flush=True)
        print("*** WARNING: Full docs built only on Linux ***", flush=True)
        print("***  (Most docs are fine on Windows)       ***", flush=True)
        print("***********************************************", flush=True)

    sys.exit(subprocess.run(["uv", "run", "sphinx-autobuild", "docs/source/", "docs/build/", "-a"]).returncode)

# Run tests with coverage (pass any pytest arguments, e.g. --pdb, -k test_name)
test *args="":
    #!/usr/bin/env bash
    set -euo pipefail

    echo "Running tests with coverage..."
    if ! env -u DBUS_SESSION_BUS_ADDRESS uv run python -m pytest -W error {{ args }} --cov-branch --cov ./src --cov-fail-under=100; then
        echo "Tests failed. Generating coverage report..."
        uv run coverage html
        uv run python -m webbrowser -t htmlcov/index.html
        exit 1
    fi

    echo "Tests passed. Running static checks..."
    just check

# Run tests with coverage, show CLI report (for AI agents - no browser)
test-cli *args="":
    #!/usr/bin/env bash
    set -euo pipefail

    echo "Running tests with coverage..."
    if ! env -u DBUS_SESSION_BUS_ADDRESS uv run python -m pytest -W error {{ args }} --cov-branch --cov ./src --cov-fail-under=100; then
        echo "Tests failed. Generating coverage report in CLI..."
        uv run coverage report -m
        exit 1
    fi

    echo "Tests passed. Running static checks..."
    just check

# Build the package (sdist and wheel)
build:
    uv build
