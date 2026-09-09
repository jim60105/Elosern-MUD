## Why

The built-in fallback set guarantees *something* is shown, but it is six generic
images shared by the whole world. The realistic way to give hundreds of NPCs and
player templates real art is to prepare it in bulk offline and hand the server a
folder — which is exactly what cannot go into git: hundreds of megabytes of
images would bloat every clone forever, and git LFS was considered and rejected.

The project already solves this shape once, for prompts: a host folder
bind-mounted read-only into the container, overridable for bare-metal runs. This
change applies the same pattern to bulk art and copies it idempotently into the
gallery at startup, exactly as `world/lore/sync.py` mirrors registries into the
database.

## What Changes

- New setting `ART_SEED_ROOT`, defaulting to `<GAME_DIR>/art-seed` and overridable
  through the environment variable of the same name — the `PROMPT_ROOT` precedent,
  a directory root read with a plain environment read rather than a typed
  `ART_SD_*` knob. An absent directory means "no seed art", not an error.
- `compose.yaml` mounts `${ART_SEED_DIR:-./art-seed}:/app/art-seed:ro,z`, the same
  read-only, SELinux-relabelled pattern as the prompt mount. The folder is never
  baked into the image.
- `.gitignore` gains `art-seed/`, so a developer's local seed folder can never be
  committed.
- New `world/art/gallery_seed.py::sync_all()`, run as a named startup step:
  walks `<seed root>/<kind>/<subject-key>/`, copies each image into the store's
  gallery path, and appends one unbound card per file with `source` `seed` and no
  prompt pair.
- Idempotency without bookkeeping: each seed file's card id is derived
  deterministically from its path inside the seed root, so a second sync finds the
  card already present and copies nothing.
- An optional per-subject `manifest.json` (`default`, `face_rect`) selects the
  default card and the face rectangle; with no manifest the first file by sorted
  name is the default and cards get the shared default rectangle. A manifest
  default applies only when the subject has no default yet, so a player's chosen
  default survives every restart.
- Seed cards are ordinary cards: deletable, default-settable, resolvable.
- A missing, unreadable, or malformed seed tree logs one `gallery_seed_sync` event
  and skips. It is never a startup failure.
- `.env.example`, `docs/development/settings-and-environment.md`, and the
  compose-only variable allow-list in the environment-inventory test are updated
  in this change so the inventory stays exact.

No backward compatibility or data migration.

## Capabilities

### New Capabilities

- `art-gallery-seed-sync`: the seed directory contract, the idempotent startup
  synchronization, the manifest contract, seed card provenance, and the tolerant
  degradation of a missing or broken seed tree.

### Modified Capabilities

- `container-image`: `compose.yaml` additionally mounts the host seed-art folder
  read-only at `/app/art-seed`, and the folder is explicitly not baked into the
  image.

`settings-environment-overrides` is NOT modified: `ART_SEED_ROOT` is a directory
root outside the enumerated `ART_SD_*` / `ART_SCHEDULER_*` typed-knob groups,
exactly like `PROMPT_ROOT`, and its `.env.example` entry and guide row satisfy the
existing inventory requirement rather than changing it.

## Impact

- `server/conf/settings.py` — `ART_SEED_ROOT`.
- `compose.yaml`, `.gitignore`, `.env.example`,
  `docs/development/settings-and-environment.md` — the new mount, ignore entry,
  inventory entry, and guide row.
- `world/art/gallery_seed.py` — new module.
- `server/conf/at_server_startstop.py` — one new startup step.
- `server/conf/tests/test_env_overrides.py`, `tests/test_container_contract.py` —
  the compose-only variable allow-list and the volume assertion.
- `world/art/tests/` — sync, idempotency, manifest, and degradation coverage.
- Unaffected: generation, the resolution chain, the fallback set, the wire
  payloads, and every player-facing command.
