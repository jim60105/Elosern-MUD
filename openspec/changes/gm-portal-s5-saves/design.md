## Context

The authoritative contract is `docs/superpowers/specs/2026-10-06-gm-portal-s5-saves-design.md` (Approved design), together with parent §3, §6 S5, and §7. See proposal.md for motivation. Current `gm-portal-access-api` and `gm-portal-spa` supply protection, JSON errors, CSRF-on-POST, offline isolation and the fetch/component boundary. `web/gm/urls.py` registers concrete routes through `gm_path()` before API fallbacks; the current router has no S5 route. `ArtDrainScript` calls the existing worker drain; pausing it must actually prevent art publication, not merely prevent future timer ticks.

## Goals / Non-Goals

**Goals:** Complete local database-and-art save slots, safe recoverable pre-start restoration, and an operator page using landed contracts. Keep restore execution independent of Django/Evennia so it can precede migration.

**Non-Goals:** S6 console work, uploads/imports, source/model/log/transcript backup, account management, service/queue controls, migrations or compatibility layers, automatic periodic-save scheduling, and game-field mutations from `web/`.

## Decisions

### 1. Storage and ownership

`server/saves/snapshot.py` owns `create_snapshot(kind: str, label: str) -> SaveInfo`, `list_saves() -> list[SaveInfo]`, `delete_save(save_id: str) -> None`, and `request_restore(save_id: str) -> None`. `server/saves/restore.py` owns the standard-library-only `--apply-pending` entry point. IDs follow `YYYYMMDDTHHMMSS-<6 hex>`; validate every supplied ID at route and function boundaries before filesystem access.

Use `server/db/saves/<id>/{evennia.db3,manifest.json}` and `ART_STORE_ROOT/.saves/<id>/` (default `server/.art/.saves/<id>/`). The database directory also holds `RESTORE_PENDING` and `RESTORE_RESULT.json`. Separate volume-local halves permit hardlinks without compose changes. Exclude `.saves/` from all live-art traversal/replacement; preserve save archives during restore. A save becomes visible only when both halves and its manifest are complete. A failure after the first final rename must remove that newly published half as well as partial directories; two filesystem renames are not an atomic transaction.

### 2. Snapshot consistency and retention

Serialize snapshots with a process lock, refusing an overlapping attempt as `save_in_progress`. Pause ArtDrainScript before SQLite online backup and keep art publication quiescent until the file mirror completes; inspect active worker and other writer paths rather than assuming timer pause stops in-flight work. Audit worker output, gallery seeding, cutout and cleanup under `world/art/`; convert every in-place file writer to write-temp-then-atomic-replace before relying on hardlinks. Deletion/unlink must not mutate saved inodes. Use SQLite's online backup API, never a live database byte copy.

Write DB and art into `<id>.partial` directories. Art files are hardlinked with copy fallback on link failure. The manifest records id, label, kind (`manual`, `auto_restore`, `auto_intervention`), creation time, world tick/in-game date, player summary (name/location key), latest applied migration per app, file count and size. Publish only a complete pair; clean failed publication and always resume the drain in `finally`.

After successful creation, prune the oldest saves independently for each automatic kind to `GM_AUTOSAVE_KEEP` (default 10, environment override); manual saves are never pruned. Public deletion rejects automatic kinds and removes both halves for a manual save. Retention uses an internal deletion path, not the manual-only public operation. A restore request pins its selected target before creating the pre-restore snapshot: when that target is an `auto_restore` save, defer that kind's pruning until pending application finishes. The pre-start tool leaves archives intact; the subsequent server startup performs the deferred retention. This temporary overflow resolves the source design's otherwise conflicting pre-save/oldest-pruning order without deleting the target before application.

### 3. Restore request and pre-start transaction

Before changing current state, refuse a save whose migration inventory contains a migration unknown to current code (`save_incompatible`). Older known saves are accepted and migrate forward normally. Create an `auto_restore` snapshot first; if that fails, do not write the pending marker or shut down. Then write the target ID to `RESTORE_PENDING`, respond successfully, and schedule the existing Evennia shutdown path after the response rather than restoring live SQLite or caches.

If request preparation fails before the pending marker is committed, release the target pin and finish any deferred pruning without shutting down. Persisted pending/result state identifies deferred retention across the restart; no in-memory pin is assumed to survive shutdown.

The live server can obtain applied migration metadata through Django. The pre-start compatibility check must obtain known migration names from current installed application migration files using standard-library discovery, without importing migration modules or initializing Django/Evennia. Include dependency apps as well as project apps; share the app-location discovery data with launcher configuration rather than maintaining a second hardcoded migration list. Test this seam in an interpreter where Django/Evennia imports are prohibited.

Both `scripts/serve.sh` and `docker-entrypoint.sh` invoke `--apply-pending` before `evennia migrate`, using the project uv-managed interpreter. With no marker, the tool leaves live files unchanged. With a marker, validate the ID, manifest, migration compatibility and all save files before moving originals aside. Move the live database and live art aside, install independent writable copies of the selected save, and preserve `.saves/`. Do not consume the selected archive or its siblings. On success remove moved-aside originals and marker; on failure restore originals, remove marker and continue normal startup. Write `RESTORE_RESULT.json` in either outcome and report on stdout. The server startup hook translates it to `save_restored`/`save_restore_failed` facade events; list API returns the latest result for the page. Existing lease reclaim requeues captured `in_progress` jobs.

### 4. Portal adapters and download

Register exactly the approved routes before catch-alls: GET/POST `/gm/api/saves/`, POST `/gm/api/saves/<id>/restore`, POST `/gm/api/saves/<id>/delete`, GET `/gm/api/saves/<id>/download`. Reuse `gm_path()`, response helpers, access middleware and CSRF. JSON success/error follow the current envelope; list includes save metadata and latest restore result. A successful download is the deliberate binary exception: stream an uncompressed tar of database, art and manifest without buffering the whole archive; pre-stream errors remain JSON envelopes. Add download handling to the existing GM API boundary rather than a second fetch convention, preserving authentication and code-based failures. The current client triggers permission navigation for almost every 403; avoid classifying `save_delete_forbidden` as account denial by keeping that domain refusal distinct from the `forbidden` access response.

Enable only the S5 navigation entry and add the saves page. Reuse token-only components and danger styling; list label/kind/time/game date/player summaries/size, create with label, restore, download and confirmed manual deletion. Restore confirmation explains pre-save, shutdown and the need to start again. Do not enable S6. Operational writes emit `gm_action` with account/target, in addition to existing request traces and S5 events.

## Risks / Trade-offs

- Hardlinks depend on immutable published art inodes; writer audit and saved-byte regression tests are prerequisites, not optional optimization work.
- Database/art reside on separate volumes; use complete-pair listing and compensating cleanup, not claims of atomic cross-volume rename.
- Restoring a database without artwork is not acceptable; inject failures between replacements and prove originals return intact.
- Long snapshots can pause art processing; no network service is needed and deterministic play remains offline-capable.

## Contract Details Not Specified by the Approved Design

The source does not fix JSON field names/status numbers for S5 payloads, label length/empty-label policy, per-file manifest verification representation (for example an inventory versus checksums), restore-result field names/consumption policy, or behavior if rollback itself cannot write due to storage failure. It requires verification of every file but names only aggregate file count/size in the manifest. Do not silently add checksum formats, new public error codes, retry policies or a crash-recovery protocol as approved requirements. The implementation must document its concrete serialization and verification choices while preserving the stated behavior; unrecoverable storage failures remain an explicit operational limitation, not a fabricated successful rollback. These details do not change S5's scope or warrant S6 work.
