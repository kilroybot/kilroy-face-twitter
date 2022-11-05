<h1 align="center">kilroy-face-twitter</h1>

<div align="center">

kilroy face for Twitter 🐦

[![Lint](https://github.com/kilroybot/kilroy-face-twitter/actions/workflows/lint.yaml/badge.svg)](https://github.com/kilroybot/kilroy-face-twitter/actions/workflows/lint.yaml)
[![Multiplatform tests](https://github.com/kilroybot/kilroy-face-twitter/actions/workflows/test-multiplatform.yaml/badge.svg)](https://github.com/kilroybot/kilroy-face-twitter/actions/workflows/test-multiplatform.yaml)
[![Docker tests](https://github.com/kilroybot/kilroy-face-twitter/actions/workflows/test-docker.yaml/badge.svg)](https://github.com/kilroybot/kilroy-face-twitter/actions/workflows/test-docker.yaml)
[![Docs](https://github.com/kilroybot/kilroy-face-twitter/actions/workflows/docs.yaml/badge.svg)](https://github.com/kilroybot/kilroy-face-twitter/actions/workflows/docs.yaml)

</div>

---

This `README` provides info about the development process.

For more info about the package itself see
[package `README`](kilroy_face_twitter/README.md) or
[docs](https://kilroybot.github.io/kilroy-face-twitter).

## Quickstart (on Ubuntu)

```sh
$ apt update && apt install curl git python3 python3-pip python3-venv
$ python3 -m pip install pipx && pipx install poetry
$ pipx ensurepath && exec bash
$ curl -sSL https://repo.anaconda.com/miniconda/Miniconda3-py39_4.10.3-Linux-x86_64.sh -o miniconda.sh
$ bash miniconda.sh && exec bash
(base) $ git clone https://github.com/kilroybot/kilroy-face-twitter
(base) $ cd kilroy_face_twitter
(base) $ conda env create -f environment.yaml
(base) $ conda activate kilroy-face-twitter
(kilroy-face-twitter) $ cd kilroy_face_twitter
(kilroy-face-twitter) $ poetry install --sync
(kilroy-face-twitter) $ poe run
```

## Quickerstart

If you just want to try it out and don't care about polluting your environment:

```sh
$ python3 -m pip install ./kilroy_face_twitter
$ kilroy-face-twitter
```

## Environment management

We are using [`conda`](https://conda.io) for environment management
(but you can as well use any other tool, e.g. `pyenv + venv`). The major reason
is that `conda` lets you specify `python` version and will install that version
in the environment. This ensures consistency between different instances
(developers, CI, deployment).

The first step is of course to install [`conda`](https://conda.io).

To create an environment, run from project root:

```sh
conda env create -f environment.yaml
```

And then activate it by:

```sh
conda activate kilroy-face-twitter
```

Creating the environment is performed only once, but you need to activate it
every time you start a new shell.

If the configuration file `environment.yaml` changes, you can update the
environment by:

```sh
conda env update -f environment.yaml
```

## Package management

We are using [`poetry`](https://python-poetry.org) to manage our package and
its dependencies. You need to have it installed outside our environment
(I recommend to use [`pipx`](https://pipxproject.github.io/pipx) for that).

To install the package, you need to `cd`
into `kilroy_face_twitter` directory and run:

```sh
poetry install --sync
```

This will download and install all package dependencies (including development
ones) and install the package in editable mode into the activated environment.

Editable mode means that you don't have to reinstall the package if you change
something in the code. The changes are reflected automatically.

However, you need to install the package again if you change something in its
configuration (e.g. add a new dependency). But more on that later.

If it's the first time installing the package, `poetry` will write specific
versions of all packages to `poetry.lock` file. This file should be committed
to the repository, so other people can have the exact same versions of all
dependencies. It will work because `poetry install` checks if `poetry.lock`
file is available and uses it if it is.

## Testing

We are using [`pytest`](https://pytest.org) for tests. It's already installed
in the environment, because it's a development-time dependency. To start first
write the tests and put them in `kilroy_face_twitter/tests`.

To execute the tests, `cd` into `kilroy_face_twitter` and run:

```sh
poe test
```

## Building docs

We are using [`mkdocs`](https://www.mkdocs.org)
with [`material`](https://squidfunk.github.io/mkdocs-material)
for building the docs. It lets you write the docs in Markdown format and
creates a nice webpage for them.

Docs should be placed in `kilroy_face_twitter/docs/docs`. They
are pretty straightforward to write.

To build and serve the docs,
`cd` into `kilroy_face_twitter` and run:

```sh
poe docs
```

It will generate `site` directory with the webpage source and serve it.

## Adding new dependencies

If you need to add a new dependency, look into `pyproject.toml` file. Add it
to `tool.poetry.dependencies` section. If it is a development-time dependency
you need to mark it as optional and add it to the right groups
in `tool.poetry.extras`.

After that update the installation by running
from `kilroy_face_twitter` directory:

```sh
poe update
```

This will install anything new in your environment and update the `poetry.lock`
file. Other people only need to run `poetry install` to adjust to the incoming
changes in the `poetry.lock` file.

## Continuous Integration

When you push changes to remote, different GitHub Actions run to ensure project
consistency. There are defined workflows for:

- deploying docs to GitHub Pages
- testing on different platforms
- testing inside Docker container
- drafting release notes
- uploading releases to PyPI
- publishing Docker images

For more info see the files in `.github/workflows` directory and `Actions` tab
on GitHub.

Generally if you see a red mark next to your commit on GitHub or a failing
status on badges in `README`
it means the commit broke something (or workflows themselves are broken).

## Releases

Every time you merge a pull request into main, a draft release is automatically
updated, adding the pull request to changelog. Changes can be categorized by
using labels. You can configure that in `.github/release-drafter.yaml` file.

Every time you publish a release:

- the package is uploaded to PyPI with version taken from release tag (you
  should store your PyPI token in `PYPI_TOKEN` secret),
- the Docker image is built and uploaded to GitHub registry with tag taken from
  release tag.

## Docker

You can build a Docker image of the package (e.g. for deployment). The build
process is defined in `Dockerfile` and it's optimized to keep the size small.

To build and run the container in one go,
`cd` into `kilroy_face_twitter` and run:

```sh
poe docker
```
