# Development

This document serves as documentation for the package developers.

## Branches and tags

- **`main`** branch: The only long-living branch. All PRs are done against it.
- Use a local short-lived feature branch for development.
- Releases use [Semantic Versioning](https://semver.org/) and are marked with git tags (on the `main` branch) with format `v[major].[minor].[patch]`; e.g. v1.2.0 or v2.2.0.

# Installing wakepy for development

[Install uv](https://docs.astral.sh/uv/getting-started/installation/), clone the wakepy repo and install all dependencies:

```
uv sync --all-groups
```

### Installing: FreeBSD notes (installing for development)

- To install ruff, You need a recent version of Rust. Recommended to use rustup. You'll also need gmake.
- You'll also need the Standard Python binding to the SQLite3 library (py3**-sqlite3)

# Just commands

This project uses [just](https://github.com/casey/just) as a command runner. To see all available commands, run:

```
just
```

Available commands:
- `just test` - Run tests with coverage (pass any pytest arguments, e.g. `just test --pdb`, `just test -k test_name`)
- `just format` - Format code using isort, black, and ruff.
- `just check` - Static checking of code, linting, formatting checks, etc.
- `just docs` - Build and serve the documentation with live-reload.
- `just build` - Build the package (sdist and wheel)

# Testing

The test commands from smallest to largest iteration cycle:

- `python -m pytest /tests/unit/some.py::somefunc` - Run a single test on single python version. Tests against source tree.
- `python -m pytest ` - Run all unit and integration tests on single python version. Tests against source tree.
- `just test` - Will (1) run tests in your current python environment against the intalled version of wakepy (if editable install, uses the source tree), (2) Check code coverage, (3) run code formatting checks.
- GitHub Actions (PR checks): pytest + mypy on multiple python versions and multiple operating systems. Code check (formatting, linting) on single a python version. Tests also that documentation build does not crash.

## Running tests against a specific version of python

Use `uv sync --python <version>` followed with `uv run --python <version>`. For example:

```
uv sync --python python3.8 --group test
uv run --python python3.8 pytest
```

To switch back, use

```
uv sync --all-groups
```

That will use the python version You can see the list of available versions of python with `uv python list`. The list is tied to the installed uv version.


# Documentation

- The documentation is done with Sphinx and the source code lives at
 `./docs/source`.
- **Building locally** (for debugging / testing docs), with autobuild:

```
just docs
```

- **Deploying**: Just merge in main in GitHub, readthedocs will automatically build documentation (by default, the "latest"). The settings can be adjusted [here](https://readthedocs.org/dashboard), and you can see the history of builds [here](https://app.readthedocs.org/projects/wakepy/).
- Versions selected for documentation are selected in the readthedocs UI. Select one version per `major.minor` version (latest of them) from the git tags.

## urls
- The `stable` version in readthedocs ([wakepy.readthedocs.io/stable/](https://wakepy.readthedocs.io/stable/)) is the latest *release* (tagged version), as documented in [here](https://docs.readthedocs.io/en/stable/versions.html).
- The `latest` version in readthedocs ([wakepy.readthedocs.io/latest/](https://wakepy.readthedocs.io/latest/)) follows the HEAD of the `main` branch automatically. This is the *development* version.
- The released versions X.Y.Z can also be accessed at `wakepy.readthedocs.io/vX.Y.Z/`

# Creating a release

The release process is automated, but changelog creation takes a few manual steps, since then it's possible to use Sphinx syntax to refer and link to python classes, methods and attributes within the changelog, and it's possible to get the same changelog to RTD and GitHub Releases.

**Steps**:
- Add changelog and release date to [changelog.md](docs/source/changelog.md)
- Merge the changes to main.
- Locally, fetch and checkout latest main, and create a new git tag with format vX.Y.Z
- Push the tag to GitHub. Verify that the tag commit is same as latest main commit.
- Go to GitHub and run the action for release (https://github.com/wakepy/wakepy/actions/workflows/publish-a-release.yml) *on the tag vX.Y.Z*.
- After release, go to GitHub Releases at https://github.com/wakepy/wakepy/releases/. Start editing the description of the latest release.
- Copy-paste the changelog from https://wakepy.readthedocs.io/stable/changelog.html to the description. Add titles (`###`)  and list markers (`-`) back.
- Copy-paste the text further to a text editor and find and replace "wakepy.readthedocs.io/stable" with "wakepy.readthedocs.io/X.Y.Z" to keep the changelog links working even after later releases.
- Copy-paste back to the GitHub Releases, and save.