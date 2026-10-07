## Why

S1–S5 already provide protected diagnostics, runtime inspection, authored-data browsing and recoverable world saves. The remaining S6 console lets the sole operator repair unanticipated faults and set up test situations without hand-patching a Django shell, while preserving deterministic ownership and a recoverable pre-intervention save.

## What Changes

- Add a shared console execution path that hands every operation to the gameplay thread as one synchronous operation, with a process-local tick baseline, conditional S5 `auto_intervention` snapshots whose represented tick is read from the copied database, fail-closed snapshot handling with fail-fast contention refusal, result refresh and `gm_action` evidence; successful manual saves reset the baseline from their own copied database.
- Add the complete approved first batch of fourteen domain verbs in `world/rules/gm.py`, `world/maps/gm.py`, `world/quests/gm.py` and `world/narrative/gm.py`, reusing existing inventory (including the materialized item objects that mirror its canonical keys), traits, clock, movement, monster, quest and append-only memory mechanisms.
- Add transactional one-object raw batches in `server/console/raw.py` for Attributes, categorized tags and location, resolving S3 object references; no typeclass editing, other-model editing or code execution.
- Add POST `/gm/api/console/<verb>`, POST `/gm/api/state/object/<dbref>/raw` and GET `/gm/api/console/status`, retaining landed access, CSRF, envelopes and stable code-based errors.
- Add contextual entity drawers, the raw edit toggle with a permanent bypass warning, NPC memory actions and dashboard clock advance, with save-aware confirmation and section refresh. There is no standalone repair catalogue or placeholder console page.
- Amend `AGENTS.md` and `docs/gm/overview.md` in implementation to name writer ownership and allow manual state patching only through the console. Include the approved S6 acceptance matrix, shard ownership, stories and substantive canonical requirement traceability.
- **BREAKING**: the S3 raw URL becomes GET/POST rather than GET-only; GET, all reader modules and recall remain immutable. Remove S5's explicit requirement that S6 stay disabled after S6 delivery. No compatibility layers or migrations.

## Capabilities

### New Capabilities

- `gm-developer-console`: conditional snapshots, all fourteen owner-backed verbs, transactional raw edits, shared execution, API/error contracts, contextual operator surfaces, documentation and acceptance obligations.

### Modified Capabilities

- `gm-runtime-state`: retain immutable inspection while admitting a separately dispatched raw POST at the existing raw URL; keep reader AST/runtime protections intact.
- `gm-save-management`: successful manual save baseline integration and removal of the now-obsolete S6-disabled presentation restriction; all snapshot/restore/retention behavior stays unchanged.
- `gm-portal-spa`: recognize contextual S6 entry points without inventing a standalone intervention page; retain disabled behavior for genuinely undelivered sections.

`gm-portal-access-api` and `gm-operations-dashboard` remain unchanged: the console reuses their access/transport and read-only dashboard GET contracts; clock mutation uses the separate console POST.

## Impact

Implementation touches `server/console/`, the four owning `gm.py` modules and narrow existing settlement seams (including the snapshot metadata seam in `server/saves/snapshot.py`), `web/gm/` transport/routes, `web/admin-app/` contextual components and tests, save/manual-baseline integration, `AGENTS.md`, `docs/gm/overview.md`, component/story manifests and test shard/traceability contracts. Authored source remains read-only; game bundle, OOB, `/admin/`, AI writers and frozen contracts remain untouched. No audit model, repair detection, new player command, external-service dependency or arbitrary execution is added.

This is one bounded engineer-day integration change: existing S1–S5 presentation/save infrastructure and deterministic settlement mechanisms are prerequisites, not work to recreate. The verb batch is closed, with small owner adapters and shared transport/confirmation; raw editing is one object per batch. Keeping these coupled surfaces together avoids shipping writes without the approved snapshot gate or an unusable subset of S6.

Prerequisites already on `master`: archived S1 foundation, S2 dashboard (for its world-section entry), S3 runtime state and S5 saves. There are no active-change dependencies and no batch split. Prospective code conflicts are the shared GM URL/response map, entity/memory/world components, save creation path, owner settlement seams, `AGENTS.md`, overview documentation and shard manifests; any later work touching these paths must reconcile against this change.

Authoritative sources: `docs/superpowers/specs/2026-10-06-gm-portal-s6-console-design.md` §§1–9, parent `2026-10-06-gm-portal-design.md` §3/§6/§7, architectural engine design and current main capability specs. Proposal commits contain only this change's artifacts; documentation/code/test changes above belong to implementation.
