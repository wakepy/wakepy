# Installing

The supported python versions are

- CPython 3.7, 3.8, 3.9, 3.10, 3.12, 3.13, 3.14 and 3.15 (including free-threaded)
- [PyPy](https://pypy.org/) 3.8, 3.9, 3.10 and 3.11 (PyPy 3.7 might work as well [^pypy37])

[^pypy37]: The PyPy 3.7 also passes unit tests but cannot be used with mypy, so it's not officially supported. See: [this comment in wakepy/#393](https://github.com/wakepy/wakepy/pull/393#issuecomment-2362974437)

## PyPI
Wakepy may be installed from [PyPI](https://pypi.org/project/wakepy/) with pip (or [uv](https://github.com/astral-sh/uv)). For example:

```
pip install wakepy
```

Alternatively, if you are installing wakepy for the [CLI](#cli-api), you can use [pipx](https://github.com/pypa/pipx):

```
pipx install wakepy
```

## GitHub releases

You may also install a release (.whl or .tar.gz) by downloading it from the [GitHub releases](https://github.com/wakepy/wakepy/releases) and installing with the tool of your choise (e.g. pip / pipx / uv). For example:

```
pip install wakepy-0.9.1-py3-none-any.whl
```

Note that GitHub releases also contain the .sigstore files (e.g. `wakepy-0.9.1-py3-none-any.whl.sigstore`) which you may use to verify that an artifact has came from the [Publish a wakepy release 📦](https://github.com/wakepy/wakepy/blob/main/.github/workflows/publish-a-release.yml) GitHub Action.

## Source code

You may also install directly from the [source code](https://github.com/wakepy/wakepy) by (forking and) cloning the repo. This way it's possible to also install an unreleased ("latest") version. If you do this, you might want to look at the [DEV.md](https://github.com/wakepy/wakepy/blob/main/DEV.md)

## conda-forge

Wakepy (>=0.9.1) is also published to [conda-forge](https://anaconda.org/conda-forge/wakepy), the community-led conda channel of installable packages. This means that you can install it with [conda](https://docs.conda.io/en/latest/):

```
conda install wakepy
```

or with [mamba](https://mamba.readthedocs.io/en/latest/):

```
mamba install wakepy
```

The prerequisite is that you have to had added conda-forge to your channels with

```
conda config --add channels conda-forge
conda config --set channel_priority strict
```

The [conda-forge/wakepy-feedstock](https://github.com/conda-forge/wakepy-feedstock) contains more information and is the source for the wakepy package in conda-forge.

## Installing notes
Note that to get the `wakepy` <a href="https://wakepy.readthedocs.io/stable/cli-api.html">CLI command</a> working, you might need to restart the shell / terminal application after installing.
