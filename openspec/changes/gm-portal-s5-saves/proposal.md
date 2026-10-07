## Why

World-state experiments need a recoverable save slot that includes both SQLite state and generated artwork. The landed Developer portal supplies the access and transport foundation; S5 adds offline save management without field-level writes or any S6 console functionality.

## What Changes

- Add whole-world snapshots, metadata, per-automatic-kind retention, confirmed manual deletion, and tar downloads through `server/saves/`.
- Add staged restore requests, automatic pre-restore snapshots, and a standard-library pre-start restore tool with rollback and result reporting in both launchers.
- Verify and, where necessary, convert art writers to atomic replacement before using hardlinked snapshots.
- Add the saves page and the five approved save API routes using the existing Developer gate, CSRF, envelope, and isolated GM component layer.
- Add deterministic snapshot/restore/API/launcher/UI tests, shard ownership, traceability, operational documentation, and facade events.

## Capabilities

### New Capabilities

- `gm-save-management`: Complete database-and-art saves, retention, staged restore with rollback, download, and the operator save page.

### Modified Capabilities

None. The current `gm-portal-access-api` and `gm-portal-spa` contracts are reused, not re-specified or amended. S1–S4 are already landed.

## Impact

Implementation touches `server/saves/`, settings/startup integration under `server/conf/`, art writers under `world/art/`, `scripts/serve.sh`, `docker-entrypoint.sh`, `web/gm/`, `web/admin-app/`, test ownership manifests, and operator/development documentation. No new service, dependency, compose volume, database schema migration, compatibility shim, game command, OOB change, or game-client contract change is proposed.

## Sizing and Dependencies

Keep one engineer-day-sized change: one local storage workflow with thin existing portal adapters, no import/upload or scheduler product. It depends only on the landed S1 foundation; S2–S4 are not new prerequisites. S6 may later call `create_snapshot("auto_intervention", ...)`, but its artifacts and write policy are explicitly out of scope. Implementation conflict surfaces are shared portal URL/router/navigation files, art writers, settings/startup hooks, both launchers, and shard manifests; queue changes editing these surfaces serially.

The sizing assumes reuse of existing art worker serialization, Evennia shutdown, lease reclaim, GM components and temporary-file test fixtures, with no new persistence model or infrastructure. Art quiescence/writer safety and two-store rollback are explicit verification checkpoints before portal wiring; they must not be traded away to meet the sizing estimate.
