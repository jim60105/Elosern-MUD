# elosern-map-editor

The independent local map editor service and its separate Vue workspace
(`frontend/`). It loads the authored map documents through
`elosern_map_core`, serves a read-only world browser over the complete
authoring world, and exposes bounded, authenticated local HTTP/SSE APIs.

It has its own `pyproject.toml`/`uv.lock` and its own pnpm lock; installing
it never installs the game, Evennia, Django or the game frontend bundle.

See `docs/development/map-editor.md` for the launch commands, the API and the
security model.

```console
uv run --locked python -m pytest            # service mechanism tests (this directory)
```
