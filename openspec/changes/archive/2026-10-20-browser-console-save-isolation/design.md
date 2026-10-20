# Design: Isolated console saves

## Context

See proposal.md. Handoff issue 1 observed a protected teleport refusing before mutation, with an AttributeError at `server/saves/snapshot.py:138`. Browser settings import Evennia defaults rather than production settings. `default_layout()` reads the database, `GM_SAVES_ROOT` and `ART_STORE_ROOT` per call; `SnapshotPolicy.execute()` snapshots before intervention.

## Goals / Non-Goals

The managed runtime must exercise the production save boundary using private files. Production fallback paths, importing production settings wholesale, weakening the snapshot guard and adding console verbs are excluded.

## Decisions

Bind `GM_SAVES_ROOT` to a saves directory inside the existing managed temporary root. Route any environment override through the managed runtime's path ownership, matching how its database, art, media and logs are configured. Teardown owns the saves with the rest of that root. Configure `GM_AUTOSAVE_KEEP` with the same meaning and default as production (10); a test override may use a smaller positive count for focused retention checks.

Audit the actual snapshot/intervention path for every settings access, including retention, art-side manifests and snapshot lifecycle hooks. Add missing browser settings using production semantics and private paths. Keep a short settings-to-private-root table in the existing browser runtime documentation; production settings remain the reference, never the browser's imported configuration.

The integration regression boots an isolated `ManagedServer`, authenticates a Developer account with CSRF, submits a real `/gm/api/console/teleport` request and verifies `snapshot.taken`, a real complete save ID and the committed target room. Inspect the saved database to prove it contains the pre-teleport location. Establish that the live DB, save DB/manifests and copied art all resolve under that invocation's root; record byte hashes or absent-before/after sentinels for developer DB/save/art roots without creating production data. Do not mock the successful saver. A focused failure injection must still refuse with `snapshot_failed`, preserving location and policy baseline.

## Risks / Trade-offs

Snapshots copy a real database and art; keep the fixture small and test one protected operation. Two managed instances must own disjoint save roots. Existing save-policy tests cover cadence; add retention coverage for the browser configuration without expanding this change into production save redesign.

## Verification and documentation

Use focused save/console tests and one exact browser method. Register new browser methods in `.github/browser-shards.json`; any new eligible Evennia module goes in exactly one `.github/evennia-shards.json` shard. Update the existing browser-runtime development guide with the save layout and override semantics. Run strict validation, exact ownership/frozen contracts and post-sync contract/traceability checks under the implementation/maintenance owners. Full browser and evidence gates remain CI-owned.
