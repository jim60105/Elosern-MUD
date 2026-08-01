# Elosern MUD

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

Run the contrib matrix regression check in the uv-managed environment:

```sh
uv run --locked -m unittest discover tests
```
