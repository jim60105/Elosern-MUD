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

## Test

Run the contrib matrix regression check with `python -m unittest discover tests` in an environment
that installed `requirements.txt`.
