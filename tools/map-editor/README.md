# elosern-map-editor

The independent local map editor service and its separate Vue workspace
(`frontend/`). It loads the authored map documents through
`elosern_map_core`, serves a world browser over the complete authoring world
with guarded single-document commands (interior layout moves, autosave and
segment undo/redo), follows the workspace files continuously (directory
watching reconciled against its committed fingerprints, stale previews and
restart recovery, with no handoff), runs explicit partition jobs in a child
process with guarded artifact publication, and exposes bounded, authenticated
local HTTP/SSE APIs.

It has its own `pyproject.toml`/`uv.lock` (with the core's `generation` extra,
NumPy and SciPy) and its own pnpm lock; installing it never installs the game,
Evennia, Django or the game frontend bundle.

See `docs/development/map-editor.md` for the launch commands, the API, the
command envelope, durability and history semantics, and the security model.

```console
uv run --locked python -m pytest            # service mechanism tests (this directory)
```
