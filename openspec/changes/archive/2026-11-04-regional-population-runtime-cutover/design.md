# Design

## Context

`ElosernWildernessMapProvider.at_prepare_room` still calls ensure_population on every activation. `sync_wilderness` re-prepares active rooms on restart. The old population module owns tier-example, capital-band, coordinate-hash slots, cleanup and prospective projection. Startup currently restores sessions before wilderness sync; new clock source registration must precede restoration without restoring visit-driven births.

## Goals / Non-Goals

Deliver this proposal's bounded regional-population prerequisite or cutover, using existing deterministic owners and real runnable operations. Do not implement adjacent field movement/aggression/escape or independent monster content. No compatibility paths or save conversion.

## Decisions

### Activation and startup contract
In `server/conf/at_server_startstop.py` (the existing startup composition root), register the real merged population lifecycle coordinator under the existing `monster_site_lifecycle` event source before `restore_persisted_sessions` can advance time, alongside the existing deterministic source setup. Use regional-population-recovery's merged site/transition/wave boundary coordinator. It applies exact-tick site lifecycle before same-tick regional births while retaining other existing stage order; never run a whole-interval site stage before a separate whole-interval regional stage. No callback runs from a wall timer. Pure next-boundary queries do not mutate. Keep combat restoration before any new wilderness initialization.

In `world/maps/bootstrap.py::sync_wilderness`, distinguish a genuinely newly created wilderness script from a preexisting one before provisioning. Use the already-implemented `initialize_population_seed(wilderness, seed=0, tick=current_tick)` owner operation on a genuinely new script, which atomically creates the empty transition/protection timeline with the saved seed, then invoke initialize_zone for each authored zone in stable-key order inside one owner-compensated provisioning transaction after actual map publication. Reuse each persisted zone seed thereafter. The seed/timeline prerequisite already exists on supported freshly provisioned scripts; this cutover must not introduce another seed writer. A preexisting world under the complete runtime contract must already have initialized zone state; missing/malformed state is a named `population_state_uninitialized` operator refusal with no automatic filling/conversion/reset. Do not inspect old coordinate slots to reconstruct it. Explicit GM save/repair/reset procedures are the only path for incompatible development state, documented without executing any reset here. Failure in a later zone initialization restores earlier created individuals and all owner/cache surfaces.

Remove ensure_population from provider preparation. Wilderness contrib attachment and itemcoordinates remain authoritative; preparation sets presentation/locks and attaches already registered individuals without reconciling expected counts. Retain existing resources, home markers and IDs through restart and pooled-room recycling. Repeated startup, source reread and player arrival create nothing. No code is permitted to delete a living object because a declaration changed. Foreign site, quest, story and GM entities are never converted or removed.

### Complete deletion boundary
Delete from `wilderness_population.py` all obsolete `MonsterPopulation`, `population_for_coordinates`, `_REGION_TIER`, `_REGION_DENSITY`, tier visual selection, capital_entry/CAPITAL_ENTRY_XY compatibility accessor, hunting-band constants/predicate, coordinate hash/slot selection, ExpectedSlot/PopulationDecision, ambient_population_decision, ambient_observation_key, ambient_slots_in_use, _population_key, _spawn, _spawn_species_individual, ensure_population and conformance/cleanup helpers. Keep only actual read projection and any genuinely shared canonical threat helper. Move active-session protection discovery to regional_population if still needed by the new owner and migrate site imports; no alias or old-path wrapper.

Remove `AmbientPlacementRule`, AMBIENT_PLACEMENT_REGISTRY, ambient_rule and declarations after all prerequisite consumers are migrated; retain current species/variant registries and art-only visual examples for their separate valid representation. Update `world/lore/{__init__,sync,registry_index}.py`, `world/maps/{geography,runtime}.py` candidate joins, GM readers, provider/bootstrap, tests/seeds and direct exports. Do a literal symbol caller sweep after CodeGraph discovery and remove every obsolete import, dead comment and test that establishes old immediate refill or example generation. Keep useful construction, ownership, rollback, view, resource and foreign-object controls in the replacement tests. No legacy slot reader, migration, compatibility setting, online reset, new ecology simulation, movement, aggression, flee relocation, undefined weak candidate or high-tier boss content.

### Integrated verification and smoke contract
Use a managed disposable development world through actual deterministic owners and text/browser-equivalent authoritative entry, not a manually patched production database. Add a retained developer smoke entrypoint `tools/monster_population_smoke.py` invoked by `uv run --locked evennia shell --plain -c "from tools.monster_population_smoke import run; run()"` in that disposable configured world. It installs synthetic registry/map fixtures via the existing synthetic-data kit, uses real species construction, initialization, explicit placement, map/presence projection, engage/cast draft and committed resolver defeat, clock recovery and fresh-object reload. It must not mock the tested consumer boundaries or directly patch quest/money/combat records. LLM/art calls are disabled through test settings; the deterministic loop completes offline. Existing unit tests remain separate evidence.

The smoke writes a bounded result report identifying seed, zone, original/new dbrefs, actual variant/cell/count, view IDs, roster and opening recipients, accepted undersupplied hunt ID/deadline, death occurrence/due ticks, before/at-due populations, state sequence and reloaded IDs/resources. Exercise actual existing GM spawn/HP/delete and quest placement owners with real map registration and delayed/cancelled recovery, including deleted away-home history and restart during a protected battle. Include an explicit legal placement in a noncapital settlement buffer, manual excess blocking ordinary births, cleared one-shot/not-due site preservation, cancellation after manual restoration with unchanged sequence and a fault AFTER actual construction+registration followed by same-plan retry. Final reload must show no duplicate/half-group and restored caches after rollback. The runner uses a documented disposable DB and restores its own synthetic fixture scope; no hidden reset or damage to unrelated data. It returns nonzero with the failed boundary, never a success from printed fixture declarations. Record the actual run and human review in `docs/development/regional-monster-population.md`, not a fabricated completion ledger.

### Documentation and traceability cutover
Update command docs as needed after the whole batch and remove capital-local tutorial guarantees; quest slice owns the data-model guarantee amendment. Replace current wilderness main-spec requirements with the deltas here, retaining actual room registration and active-session protection. The old capability purpose still describes the obsolete model: during authorized implementation amend its Purpose explicitly to actual sparse regional population before archive, because delta Purpose is ignored for existing capabilities. Likewise remove prospective wording from wilderness-population-view Purpose. These main-spec purpose-only edits occur during implementation, never in this planning batch.

Before replacing tests, add an assertion-role cutover ledger to the developer document recording each retired requirement annotation, whether its test is synthetic-mechanism/registry-contract/representative-smoke, the replacement requirement and reason. Use canonical IDs from `tools.spec_traceability list`; additions have no current IDs. Use an equivalent merged spec tree with the existing traceability tool for future IDs, reattach only substantively matching tests and remove all retired literal IDs without waivers. Retired coordinate-example and content-echo assertions are deleted, never disguised as data-contract tests. Update evennia/browser shard manifests exactly when modules/methods change. Full browser/evidence verification stays CI-owned; local smoke and smallest labels below are required before handoff.

## Original-request disposition and deferred integration

| Original item | Delivering change(s) or deferred owner |
| --- | --- |
| 1 Solitary/multiple monsters | Ecology authoring, population owner and manual compositions |
| 2 Sparse settlement surroundings | Ecology authoring and runtime activation; no patrol/culling |
| 3 No automatic births against walls | Ecology eligibility and owner; lawful explicit manual/quest exceptions |
| 4 Reserved future habitats | Unconfigured ground receives no automatic births |
| 5 Manual bosses/strays | Existing-profile manual compositions/lifecycle; new powerful profiles/final sites deferred to content |
| 6 Wandering | Deferred field behaviour; separate home ownership is included here |
| 7 Monster-initiated combat | Deferred field behaviour; whole-cell admission prerequisite only here |
| 8 Enemy escape relocation | Deferred field behaviour; current flee identities are preserved |
| 9 Previous-location player retreat | Deferred field behaviour; existing confirmed whole-party authority retained |
| 10 Undefined weak monsters | Remove example construction here; complete weak-species content deferred |
| 11 Capital introductory guarantee | Quest and runtime cutovers remove it without replacement guarantee |
| 12 Different species at same cell | Complete compositions and occurrence-seeded selection |
| 13 Density | Integer eligible-area bounds and independent local/home/cell/wave caps |
| 14 Delayed regional recovery | Recovery episode owner and final clock activation |
| 15 Mixed/repeated-name combat | Persistent combat identity, whole-cell admission and compositions |

Integration references are `2026-11-03-monster-field-behaviour-and-escape-design.md` and `2026-11-03-monster-content-expansion-design.md`. No activity/journey scheduler, aggression policy, reserve-based retreat, relocation, new abilities, weak species, high-tier boss profiles, transfer-station encounter or reward system is authorized here. Later movement consumes persistent IDs, separate home ownership and actual presence; detached/travelling living members stay home-counted and absence grants no defeat/clear-out credit. Future content must provide executable approved definitions before adding references. Birth exclusions never become movement barriers. Offline deterministic play does not depend on either follow-on design.

## Live baseline and batch order

The inspected `openspec list --json` returned no active changes. `scope-test-settlement-sync` is now archived, not an active prerequisite; current YAML-backed map contracts and scoped settlement synchronization supersede historical descriptions. Root checkout was clean on master before this batch. No unresolved external prerequisite blocks the regional population design.

| Change | Real prerequisites | Shared-code conflict boundary |
| --- | --- | --- |
| combat-individual-identity | none | Combat/session, AI, effect/event consumers and fixtures |
| whole-cell-field-engagement | combat-individual-identity | Session/initiation, text/browser; shared with recovery |
| regional-ecology-authoring | none | Lore placement, map candidate publication, registry metadata |
| regional-population-owner | regional-ecology-authoring | New owner/planner and snapshots |
| regional-population-recovery | regional-population-owner; combat-individual-identity; manual-monster-compositions | Owner, session timing and clock |
| manual-monster-compositions | regional-ecology-authoring; regional-population-owner; whole-cell-field-engagement | Site/lore declarations, binding tests |
| regional-hunt-supply-cutover | regional-ecology-authoring; manual-monster-compositions | Quest acceptance/catalog and habitat markers |
| actual-live-population-view | regional-population-owner | View/sight/travel/maps/GM; shared quest marker tests |
| regional-population-runtime-cutover | whole-cell-field-engagement; regional-population-recovery; manual-monster-compositions; regional-hunt-supply-cutover; actual-live-population-view | Startup/provider, deletion and integrated smoke |

Each row is a bounded one-engineer-day slice with an independently executable owner, validator or consumer boundary. Shared `.github/evennia-shards.json`, command docs and the developer document must be serialized/reconciled even when no behavior dependency exists. No earlier slice may claim the entire regional population design delivered before final cutover.


## Risks / Trade-offs

The existing display-name, coordinate-slot and supply contracts have broad callers. Complete the named semantic caller cutover within this slice; do not add a parallel legacy path. Candidate-world validation and mutable Evennia cache restoration are part of correctness. Use synthetic independently known mechanism outcomes and real-owner integration controls instead of production data-echo tests.

## Verification and requirement traceability

During implementation, create an environment file outside tracked source containing `MUD_TEST_SETTINGS=1`. Focused command: `uv run --locked --env-file=/tmp/mud-population-test.env evennia test --settings test_settings.py --keepdb LABELS`. Replace LABELS with one affected focused method or class from the module inventory below, keeping the single-token env-file form; run independent focused invocations, never concatenate the whole inventory or exceed 100 discovered tests in one command. Use fixed synthetic inputs and independently known outputs. Production checks establish references, ownership/topology and profile obligations without copying shipped values or prose. New nonbrowser modules require exact ownership in `.github/evennia-shards.json`; browser methods, if added, require `.github/browser-shards.json` ownership. Run observability lint alongside focused tests when logging changes. Full managed browser and complete evidence verification remain CI-owned.

Before changing annotations, record each affected assertion's synthetic-mechanism, registry-contract or representative-smoke role and substantive replacement in `docs/development/regional-monster-population.md`. Canonical IDs below came from `uv run --locked python -m tools.spec_traceability list --json-output /tmp/regional-population-requirements.json`. ADDED requirements have no current IDs; never fabricate one. Before archive, use the tool on an equivalent merged spec tree, then replace provisional nearest-current claims with generated IDs. Retain no retired, empty or skipped claims. Each delta scenario maps to tasks.md test modules and must assert behavior rather than echo data.

After the completed slice run `openspec validate <change> --strict` and `uv run --locked python -m tools.contract_gate`. This gate does not establish coverage of unarchived deltas; the assertion-role ledger and focused evidence remain required. The runtime slice owns the cross-system real smoke; each earlier slice still owns real-owner integration and reload/fault controls.

## Deployment and rollback boundary

No migrations, legacy readers, aliases, implicit reset or compatibility setting are authorized. New ordinary runtime activates only at regional-population-runtime-cutover; earlier APIs are fully implemented and independently exercised through real owners. Operation failures restore durable and live surfaces through deterministic owner compensation. An incompatible development save requires documented explicit GM save/repair/reset procedures, never startup mutation. A source/code rollback requires its matching explicitly saved development state, with no incompatible-record reinterpretation.

### Nearest current canonical anchors

- `wilderness-monster-population::a-registered-wilderness-monster-survives-room-recycling`: substantive current ownership/identity/lifecycle anchor; newly added behavior requires generated post-sync coverage, not an assertion-free extra decorator.
- `wilderness-monster-population::population-reconciliation-never-destroys-an-active-session-participant`: substantive current ownership/identity/lifecycle anchor; newly added behavior requires generated post-sync coverage, not an assertion-free extra decorator.
- `player-combat-session::startup-combat-restoration-advances-time-only-after-every-deterministic-clock-source-is-registered`: substantive current ownership/identity/lifecycle anchor; newly added behavior requires generated post-sync coverage, not an assertion-free extra decorator.

### Focused implementation labels

`world.maps.tests.test_bootstrap world.maps.tests.test_wilderness_population world.maps.tests.test_wilderness_population_species world.maps.tests.test_regional_population_recovery`
