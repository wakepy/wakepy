# Development

This document serves as documentation for the package developers.

## Branches and tags

- **`main`** branch: The only long-living branch. All PRs are done against it.
- Use a local short-lived feature branch for development.
- Releases use [Semantic Versioning](https://semver.org/) and are marked with git tags (on the `main` branch) with format `v[major].[minor].[patch]`; e.g. v1.2.0 or v2.2.0.

## Installing for development

Requirements:
- At least one of the supported Python versions installed (see README.md and/or tox.ini).
- pip >= 21.3 (for pyproject.toml support)

Update pip and install wheel:

```
python -m pip install -U pip wheel
```

Install in editable state with the `dev` requirements:
```
python -m pip install -r requirements/requirements-dev.txt -e .
```

where `.` means the current directory (assuming cwd is at root of the repository).

### FreeBSD notes (installing for development)

- To install ruff, You need a recent version of Rust. Recommended to use rustup. You'll also need gmake.
- You'll also need the Standard Python binding to the SQLite3 library (py3**-sqlite3)

## Documentation

- The documentation is done with Sphinx and the source code lives at
 `./docs/source`.
- **Building locally** (for debugging / testing docs), with autobuild:

```
invoke docs
```

- **Deploying**: Just push to github, and it will be automatically built by readthedocs. The settings can be adjusted [here](https://readthedocs.org/dashboard).
- Versions selected for documentation are selected in the readthedocs UI. Select one version per `major.minor` version (latest of them) from the git tags.

### urls
- The `stable` version in readthedocs ([wakepy.readthedocs.io/stable/](https://wakepy.readthedocs.io/stable/)) is the latest *release* (tagged version), as documented in [here](https://docs.readthedocs.io/en/stable/versions.html).
- The `latest` version in readthedocs ([wakepy.readthedocs.io/latest/](https://wakepy.readthedocs.io/latest/)) follows the HEAD of the `main` branch automatically. This is the *development* version.
- The released versions X.Y.Z can also be accessed at `wakepy.readthedocs.io/vX.Y.Z/`

# Testing

Wakepy uses pytest for testing the source tree with one python version and tox for testing the created wheel with multiple python versions. The test commands from smallest to largest iteration cycle:

- `python -m pytest /tests/unit/some.py::somefunc` - Run a single test on single python version. Tests against source tree.
- `python -m pytest ` - Run all unit and integration tests on single python version. Tests against source tree.
- `inv test` (`invoke test`) - pytest + black + isort + ruff + mypy checks on single python version. Tests against source tree.
- `tox` - pytest on multiple python versions & black + isort + ruff + mypy on single python version. Tests are run agains a build (.whl) version instead of the source tree.
- GitHub Actions (PR checks): pytest + mypy on multiple python versions and multiple operating systems. Code check (isort + black + ruff + mypy) on single python version. Test that documentation build does not crash.

Below there are a few more words about the `inv test` and `tox` options.

## Running tests with single environment

- Requirement: Any one python version within the range of supported versions (see README.md or tox.ini)
- Use pytest to run tests within a single environment:

```
invoke test
```
this will (1) run tests in your current python environment against the intalled version
of wakepy (if editable install, uses the source tree), (2) Check code coverage, (3)
run code formatting checks.


## Running tests with multiple environments

- Requirement:  One or more of the python versions mentioned in the envlist in tox.ini have to be installed and available for tox. Missing python versions are going to be simply skipped. If running on UNIX/macOS, you may use [pyenv](https://github.com/pyenv/pyenv) to install multiple versions of python. In this case, you probably want to use the [pyenv global](https://github.com/pyenv/pyenv/blob/master/COMMANDS.md#pyenv-global-advanced) to mark multiple versions, as in the example below. Also note that pypy3.7 would be used in place of CPython3.7 with py37 tox marker, if CPython3.7 is not installed.

```
pyenv global 3.12.6 3.10.15 3.7.17 pypy3.10 pypy3.7
```

- To run the tests with multiple python versions, use tox:

```
tox
```

- To start a debugger on error with a specific python version, select the tox environment with "-e <envname>" and add "-- --pdb" to start the python debugger on error. For example:

```
tox -e py310 -- --pdb
```

- When using tox within this project, what happens is (1) wakepy is built with `python -m build`. This creates sdist from source tree and then wheel from the sdist. (2) Tests are ran against the created *wheel* (if not `skip_install=True` for that environment).

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