# GM Portal S5 Design: Save Management

- Date: 2026-10-06
- Status: Approved design
- Parent: `docs/superpowers/specs/2026-10-06-gm-portal-design.md` (sub-project S5)
- Depends on: S1 (portal skeleton)
- Consumed by: S6 (automatic snapshot before every intervention)

## 1. Responsibility

S5 saves and restores the world state. Elosern is a single-player game in which
the player and the operator are the same person, so a world snapshot is the
game's save slot: the operator saves before experimenting or repairing, and
returns to that state when something goes wrong.

Not in S5: account and permission management, broadcasts, multi-user server
lifecycle, and service or queue controls. Those are multi-user concerns or are
already available in game (`@art`). Prompt hot reload belongs to S4.

## 2. What a save contains

- The SQLite database `server/db/evennia.db3` (objects, Attributes, Scripts,
  narrative records).
- The generated art store under `ART_STORE_ROOT` (`server/.art`), because the
  database records only file identities, regeneration overwrites files in
  place or deletes the prior file on an extension change, and removing a
  gallery card deletes its file. Restoring the database alone would show newer
  images or fall back to silhouettes.

Not in a save: `prompts/`, rulebooks, and lore (source under git), model files
(`.translate`, `.rembg`), logs, and LLM transcripts.

## 3. Module: `server/saves/`

The operation sits below game rules and concerns the whole world, so it lives
under `server/`, beside `server/conf`, rather than in a game subsystem.

- `snapshot.py` (runs in the server process):
  - `create_snapshot(kind: str, label: str) -> SaveInfo`
  - `list_saves() -> list[SaveInfo]`
  - `delete_save(save_id: str) -> None`
  - `request_restore(save_id: str) -> None`
  - S6 calls `create_snapshot("auto_intervention", ...)`.
- `restore.py` (standard library only; runs before the server starts):
  `python -m server.saves.restore --apply-pending`.

### Layout

```
server/db/saves/<id>/evennia.db3
server/db/saves/<id>/manifest.json
server/db/saves/RESTORE_PENDING          # contains a save id
server/db/saves/RESTORE_RESULT.json
server/.art/.saves/<id>/...              # mirror of the art store tree
```

The database and art stores are separate container volumes (`evennia-db`,
`evennia-art`), and hardlinks cannot cross volumes, so each half of a save
lives inside its own volume. No compose change is needed.

`<id>` is `YYYYMMDDTHHMMSS-<6 hex>`; every route and function validates it
against that pattern.

## 4. Creating a save

At most one snapshot runs at a time (process lock).

1. Pause `ArtDrainScript` so no art file is written mid-snapshot.
2. Database: copy through the SQLite online backup API to
   `server/db/saves/<id>.partial/evennia.db3`, which yields a consistent copy
   while the server runs.
3. Art: walk `ART_STORE_ROOT` (excluding `.saves/`) and hardlink each file into
   `server/.art/.saves/<id>.partial/`, falling back to a copy when a link fails.
   Hardlinks are safe only if every art write is write-temp-then-atomic-replace.
   The implementation plan verifies every writer under `world/art/`
   (worker output, gallery seeding, cutout, cleanup) and converts any in-place
   write to an atomic replace before relying on links.
4. Write `manifest.json`: id, label, kind (`manual`, `auto_restore`,
   `auto_intervention`), created time, world clock tick and in-game date,
   player character summary (name, location key), the latest applied migration
   per app, file count, and size.
5. Rename both `.partial` directories to their final names. Any failure removes
   the `.partial` directories; no half save is ever listed.
6. Resume `ArtDrainScript` in a `finally` block. Jobs captured as
   `in_progress` are requeued after a restore by the existing lease reclaim.

### Retention

- Each automatic kind keeps at most `GM_AUTOSAVE_KEEP` saves (default 10,
  environment override); the oldest of that kind is deleted after a new one
  is created.
- Manual saves are never deleted automatically; the operator deletes them
  explicitly with confirmation.

## 5. Restoring a save

A restore cannot run inside the live server: the SQLite file and Evennia's
object caches are in use. The server records the request and shuts down; the
launcher applies it before the next start.

1. The operator confirms in the portal. The dialog uses the danger style and
   states that the current state is saved first, that the server shuts down,
   and that the operator must start it again.
2. The server:
   1. Checks migration compatibility: a save containing a migration the
      current code does not know is refused with `save_incompatible`.
   2. Creates an `auto_restore` save of the current state.
   3. Writes `RESTORE_PENDING` with the save id.
   4. Responds to the portal, then shuts the server down through Evennia's
      shutdown path.
3. The operator starts the server again. `scripts/serve.sh` and
   `docker-entrypoint.sh` run `restore --apply-pending` before
   `evennia migrate`:
   1. Verify the manifest and every file of the save.
   2. Move the current database and art store aside, then place the save's
      files.
   3. On success, remove the moved-aside files and the marker. On any failure,
      move the original files back, remove the marker, and continue a normal
      start.
   4. Write `RESTORE_RESULT.json` in either case.
4. `evennia migrate` then runs as usual, so an older save is migrated forward.
5. On startup the server reads `RESTORE_RESULT.json`, emits `save_restored` or
   `save_restore_failed`, and the portal shows the result on the saves page.

## 6. Download

`GET /gm/api/saves/<id>/download` streams an uncompressed tar of the database,
art files, and manifest. Uploading or importing saves is out of scope.

## 7. Portal

A 存檔 page lists saves (label, kind badge, created time, in-game date, player
characters, size) with actions: create (with a label), restore, download, and
delete (manual saves only). The latest restore result is shown at the top
when present.

| Route | Purpose |
| --- | --- |
| `GET /gm/api/saves/` | Save list plus the latest restore result |
| `POST /gm/api/saves/` | Create a manual save |
| `POST /gm/api/saves/<id>/restore` | Request a restore |
| `POST /gm/api/saves/<id>/delete` | Delete a manual save |
| `GET /gm/api/saves/<id>/download` | Download |

Errors: `save_not_found`, `invalid_save_id`, `save_incompatible`,
`save_in_progress`, `save_delete_forbidden` (automatic saves).

## 8. Observability

Events `save_created`, `save_failed`, `save_deleted`,
`save_restore_requested`, `save_restored`, `save_restore_failed`, each with
`save` and `kind` in `context`. `restore.py` runs before the server and cannot
use the facade; it reports through `RESTORE_RESULT.json` and stdout.

## 9. Tests

- Snapshot against a temporary SQLite database and art directory: consistent
  copy while writes occur, `.partial` cleanup on failure, retention per kind,
  `ArtDrainScript` always resumed.
- `restore.py` standard-library unit tests: success, missing file, corrupt
  manifest, incompatible migrations, failure midway with rollback of the
  original files.
- API: shapes, id validation, delete forbidden for automatic saves.
- Contract test: both launchers invoke `--apply-pending` before
  `evennia migrate`.
- New Python test modules registered in `.github/evennia-shards.json`.
