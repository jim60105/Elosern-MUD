# Design

## Context

`MonsterSite` has variant_keys/capacity, `_populate` cycles variants over capacity, and `_members` scans only the authored coordinate. `site_living_members` is pure and supplies quest clear-out bindings. Site state currently records populated/cleared and cleared_at_tick; clock settlement owns creation/recovery.

## Goals / Non-Goals

Deliver this proposal's bounded regional-population prerequisite or cutover, using existing deterministic owners and real runnable operations. Do not implement adjacent field movement/aggression/escape or independent monster content. No compatibility paths or save conversion.

## Decisions

### Manual composition and persistent site contract
Change `MonsterSite` to `(key: str, kind: str, region_key: str, coordinates: tuple[int,int], composition_key: str, capacity: int, one_shot: bool, recover_after_ticks: int | None=None)`. `capacity` remains the maximum legal complete site's individuals for definition validation, not an instruction to fill absent rows. Require every legal composition outcome <=capacity and species/habitat/placement validity. Use the ecology change's immutable composition registry; remove `variant_keys` and every old constructor/cycling reader in the same change. Do not add a compatibility property or inferred composition. Existing three site declarations receive explicit composition rows retaining their declared variant membership and lifecycle. Add `stray` and `encounter` to the existing closed site-kind vocabulary for explicit solitary and mixed placements, with no separate subsystem.

Extend site durable records with saved `seed: int`, `generation_sequence: int` and `member_ids: list[int]`. Seed deterministically derives from the world's persisted population seed and site key on first owner creation; no global random. Use shared pure composition sampling discipline from regional_population, but explicit manual sites bypass ordinary birth buffer, zone/cell density and ordinary wave budgets. They still validate the placement surface and approved variant relationships. Quest scenes retain their own explicit constructor authority and do not gain site ownership.

`_populate(wilderness, site)` constructs every sampled row together via `construct_species_individual`, stamps site_key and registers all IDs transactionally. Its capacity does not permit splitting minima or replacing survivors to meet a new draw. Site first population and matured recovery remain clock-owned. On clear-out preserve old bound IDs in existing quest records; recovered members are new IDs. Store member IDs as the site's authority, resolve living members by identity regardless of temporary absence, and determine clear-out only after all owned IDs are defeated/deleted under the existing lawful cleanup. A living detached/unlocated member never makes the site cleared. This supplies the ownership seam required by later movement without implementing journeys. `site_living_members` returns the site's living owned IDs; actual-presence consumers additionally filter position, while clear-out binding uses the standing owned set. An absent living bound actor is not a defeat.

Snapshot site state, new IDs, coordinate registry, markers, room attachments/contents and shared mutable caches before writes, joining the existing site clock snapshot contract and enclosing transaction compensation. A failing constructor or later write restores the full composition; a retry uses the same saved seed/sequence. Emit bounded site events on outer commit only. Ordinary regional settlement counts site occupants locally yet never initializes, clears, recovers or deletes a site; binding never transfers ownership.

### Caller boundary and preserved contracts
Own `monster_placement.py`, `monster_sites.py`, lore index/sync metadata and current site construction/read callers in `world/quests/{definitions,runtime}.py`, GM authored/runtime site inspection and tests. Capacity-based bound definition validation remains an upper possibility check; acceptance still requires enough actual standing owned IDs and binds exactly that returned set. Do not restore a cleared/not-yet-due site on quest acceptance or make newly recovered IDs satisfy older bindings. Do not author the adjacent design's transfer-station encounter or high-tier bosses. Update developer lifecycle documentation and generic production reference/topology checks; authored membership relations can be checked generically, mutable values/prose remain human-reviewed.

## Risks / Trade-offs

The existing display-name, coordinate-slot and supply contracts have broad callers. Complete the named semantic caller cutover within this slice; do not add a parallel legacy path. Candidate-world validation and mutable Evennia cache restoration are part of correctness. Use synthetic independently known mechanism outcomes and real-owner integration controls instead of production data-echo tests.

## Verification and requirement traceability

During implementation, create an environment file outside tracked source containing `MUD_TEST_SETTINGS=1`. Focused command: `uv run --locked --env-file=/tmp/mud-population-test.env evennia test --settings test_settings.py --keepdb LABELS`. Replace LABELS with this slice's labels below, keeping the single-token env-file form. Use fixed synthetic inputs and independently known outputs. Production checks establish references, ownership/topology and profile obligations without copying shipped values or prose. New nonbrowser modules require exact ownership in `.github/evennia-shards.json`; browser methods, if added, require `.github/browser-shards.json` ownership. Run observability lint alongside focused tests when logging changes. Full managed browser and complete evidence verification remain CI-owned.

Before changing annotations, record each affected assertion's synthetic-mechanism, registry-contract or representative-smoke role and substantive replacement in `docs/development/regional-monster-population.md`. Canonical IDs below came from `uv run --locked python -m tools.spec_traceability list --json-output /tmp/regional-population-requirements.json`. ADDED requirements have no current IDs; never fabricate one. Before archive, use the tool on an equivalent merged spec tree, then replace provisional nearest-current claims with generated IDs. Retain no retired, empty or skipped claims. Each delta scenario maps to tasks.md test modules and must assert behavior rather than echo data.

After the completed slice run `openspec validate <change> --strict` and `uv run --locked python -m tools.contract_gate`. This gate does not establish coverage of unarchived deltas; the assertion-role ledger and focused evidence remain required. The runtime slice owns the cross-system real smoke; each earlier slice still owns real-owner integration and reload/fault controls.

## Deployment and rollback boundary

No migrations, legacy readers, aliases, implicit reset or compatibility setting are authorized. New ordinary runtime activates only at regional-population-runtime-cutover; earlier APIs are fully implemented and independently exercised through real owners. Operation failures restore durable and live surfaces through deterministic owner compensation. An incompatible development save requires documented explicit GM save/repair/reset procedures, never startup mutation. A source/code rollback requires its matching explicitly saved development state, with no incompatible-record reinterpretation.

### Nearest current canonical anchors

- `monster-site-placement::one-shot-sites-stay-cleared-and-recoverable-sites-recover-only-on-approved-conditions`: substantive current ownership/identity/lifecycle anchor; newly added behavior requires generated post-sync coverage, not an assertion-free extra decorator.
- `monster-site-placement::a-site-s-living-individuals-are-the-quest-layer-s-binding-source-and-no-quest-may-create-or-recover-a-site`: substantive current ownership/identity/lifecycle anchor; newly added behavior requires generated post-sync coverage, not an assertion-free extra decorator.

### Focused implementation labels

`world.lore.tests.test_monster_placement world.maps.tests.test_monster_sites world.quests.tests.test_site_clear_out_acceptance`
