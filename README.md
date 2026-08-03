# Elosern MUD

[![codecov](https://codecov.io/gh/jim60105/MUD/graph/badge.svg?token=ysbLT6R5c7)](https://codecov.io/gh/jim60105/MUD)

This project uses Evennia `6.1.0`, SciPy `1.16.0` for Evennia's XYZ grid contrib, and the container
image pins Python `3.13`.

## Run locally

Build the image with Podman:

```sh
podman compose build
```

Before the first startup against a fresh database volume, run the one-shot bootstrap service and
create Account #1 interactively:

```sh
podman compose --profile bootstrap run --rm bootstrap
```

Then start the service with `podman compose up`. The normal startup script applies any pending
database migrations before launching Evennia. Connect through telnet at `localhost:4000` or the web
client at `http://localhost:4001`.

`OLLAMA_BASE_URL` and `SD_WEBUI_BASE_URL` configure external services. They are not containerized
by this project.

## Develop locally

Use uv `0.12.0` or newer. This checkout pins uv's interpreter selection to Python `3.13` in
`.python-version`. Install the locked project dependencies with:

```sh
uv sync --locked
```

Use `uv add <package>` and `uv remove <package>` to change dependencies so that `pyproject.toml`
and `uv.lock` stay synchronized. The `--locked` commands intentionally fail when those files
disagree.

## Preview documentation

Start the Docsify documentation site from the project root:

```sh
uv run --locked python -m http.server --directory docs 3000
```

Then open `http://localhost:3000` in a browser.

## Test

Use the explicit retained test profile for package-local non-browser tests:

```sh
MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py \
  --keepdb commands server typeclasses world web.webclient
```

Run managed browser acceptance and repository-wide contracts separately:

```sh
uv run --locked python -m unittest discover -s web/tests/browser -t .
uv run --locked -m unittest discover -s tests -t .
```

For fast feedback, replace the package labels with one dotted module, class, or
method and optionally add `--failfast`. Focused tests do not replace final
verification. See `docs/development/evennia-test-performance.md` for profiling,
database rebuild, parallel-evaluation, evidence, and coverage commands.
