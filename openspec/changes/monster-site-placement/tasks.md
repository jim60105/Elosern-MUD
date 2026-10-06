## 1. Placement registries

- [x] 1.1 Create `world/lore/monster_placement.py` with frozen `AmbientPlacementRule` and `MonsterSite` (closed kind/recovery vocabularies) plus keyed registries validated at construction (unknown region/variant, habitat-incompatible authoring, missing/out-of-vocabulary recovery condition all named errors), and verify each rejection with `unittest.TestCase` cases using synthetic species/variant fixtures
- [x] 1.2 Mirror the registries through the existing `world/lore/sync.py` step discipline with one `startup_step` boundary event, and verify a twice-run no-op plus a public-surface inspection test proving the lore module exposes no spawn/place/reconcile callable

## 2. Site lifecycle owner

- [x] 2.1 Create `world/maps/monster_sites.py`: site creation/repopulation through the individual construction owner, per-site durable state (`state`, `cleared_at_tick`), individuals marked with the site key, capacity ceiling, and one-shot stays-cleared semantics, and verify with `EvenniaTest` cases that room re-entry and quest acceptance recover nothing, and that a one-shot site never auto-recovers across clock advancement
- [x] 2.2 Wire recoverable-site maturation into the existing clock-upkeep seam with in-game-tick conditions only, creating fresh-identity individuals on recovery, and verify a test where a recovered site's new individuals have persistent identities distinct from the defeated ones and recovery emits one boundary event naming site/variants/clock context
- [x] 2.3 Append `monster_site_lifecycle` to `world/rules/clock.py::_STAGE_ORDER` per the two MODIFIED delta specs (`settlement-stage-order`, `world-clock`), register the source through a new `register_monster_sites` startup step placed before session restoration, keep the settlement absent-tolerant when no wilderness script exists, and update the pinned stage-order tests plus the startup registration guards

## 3. Ambient species reconciliation

- [x] 3.1 Extend `world/maps/wilderness_population.py` reconciliation to species-bearing ambient individuals authored by regional rules: pure coordinate-hash variant selection, quantity/capacity ceilings, ambient marker discipline, and foreign-owner immunity, and verify tests for create-up-to-capacity-no-more, drift/idempotent no-op passes, and untouched site-/quest-owned monsters in the same room
- [x] 3.2 Run the existing tier-example population tests unchanged to prove the pinned introductory-hunt behaviour is untouched, and confirm each coordinate belongs to exactly one ambient branch

## 4. Verification

- [x] 4.1 Register new test modules in exactly one shard of `.github/evennia-shards.json`, run focused lore/maps tests plus the shard-ownership contract, run `uv run --locked python -m tools.contract_gate` and the observability lint for changed modules, and confirm no player-command docs update is required
- [x] 4.2 Record the new boundary events in the observability design document's event catalog and verify a rolled-back advance restores the site source's wilderness state, leaves no created-individual row, and leaves no rolled-back individual in the instance cache
