# Design

## Context

`world/quests/runtime.py::_provision_hunt_targets` invokes `monster_provisioning.ensure_hunt_targets` inside acceptance, with special provisioning snapshots. `test_hunt_catalog_content.py` enforces the ambient per-cell ceiling. Existing map_quest_destinations resolves a species hunt to the nearest legal geographic-region cell, independently of living entities, but it does not restrict that destination to a permitted source habitat.

## Goals / Non-Goals

Deliver this proposal's bounded regional-population prerequisite or cutover, using existing deterministic owners and real runnable operations. Do not implement adjacent field movement/aggression/escape or independent monster content. No compatibility paths or save conversion.

## Decisions

### Supply validation contract
The site-composition API is a real prerequisite from manual-monster-compositions; this slice cannot run after ecology authoring alone.
Add read-only `hunt_supply_sources(region_key: str, species_key: str, countable_variant_keys: tuple[str,...]) -> tuple[HuntSupplySource,...]` in `world/quests/definitions.py`. Frozen `HuntSupplySource(kind: str, key: str, region_key: str, variant_keys: tuple[str,...])` has kind `ecology_zone` or `monster_site`. Resolve from the immutable ecology composition pools and explicit site composition declarations; include only matching parent region, owned countable variants and an ordinary eligible variant required by the existing selector contract. A valid source must pass authoring legality, with permitted capacity/count outcomes, but its current living quantity is irrelevant. Explicit site compositions are the discoverable manual source here. Existing quest scenes create only their explicitly declared encounters under quest authority and do not implicitly authorize unrelated regional hunts. Do not infer supply from species habitat tags or art keys. Bound site clear-outs remain a different selector and continue requiring actual standing members. Do not reject a regional hunt because quantity exceeds any one cell/site/wave, because it may span future recovery and encounters. A one-shot source authorizes a finite opportunity and makes no completion promise.

`validate_definition` and generated/handwritten publication callers require an actual matching lawful source; reject unknown/mismatched selectors before publication. Use candidate map bindings where publication validates geometry, preserving the candidate-world boundary. Remove `_provision_hunt_targets`, its `_stage_zero_hunt`/ordinary-only helper uses when dead, provisioning-only snapshot wrappers and `world/maps/monster_provisioning.py` entirely after migrating every caller. Delete its dedicated provisioning tests/shard entry; replace their useful ownership/atomicity assertions with owner or acceptance tests rather than a new fake ensure API. Retain ordinary-countable variant validation where it still establishes selector legality, and replace its obsolete acceptance-supply rationale in the full Species-hunt objectives requirement scenario with authored ordinary-source eligibility.

### Acceptance, board and bindings
Regional acceptance uses normal definition/issuance/rank/time/quota checks and records a quest even at zero living matching targets. It writes no population, no due time and no sequence; blocked ordinary headroom is not an acceptance refusal. Deadlines remain actual accepted_tick+hours with no guarantee of immediate supply or timely completion. Existing site clear-out refusal vocabulary, exact bound IDs, no early recovery, fresh recovered-ID non-substitution, atomic quest/affinity/party writes and escort semantics remain unchanged. Keep board listing rank/local rules and standing-site availability; regional hunts are not hidden by live target shortage. Distinguish invalid/no-source definitions from temporary undersupply.

### Guidance and introductory cutover
In `web/webclient/presentation/map_quest_destinations.py::resolve_record_destination`, choose the nearest legal authored source habitat cell for regional hunts with the existing squared-distance then x,y tie break. Preserve `DestinationFamily.SPECIES_HUNT` as a habitat destination; add `destination_kind: "habitat" | "entity" | "location"` to the internal QuestDestination record and migrate all constructors and area/world marker projections. Habitat source cells require no living target and reveal no topology; entity destinations require actual living target IDs/position. Existing regional-hunt marker contract already represents a destination, so do not turn it into a hostile observation. Update quest summary/board/log prose where an immediate target or capital-gate guarantee is promised.

Update `world/quests/catalog.py`, its registered offers/rewards and introductory/tutorial references coherently: retain a valid permanent offline introductory DEFEAT quest using an approved source without guaranteeing one adjacent cell, or remove an obsolete guarantee-specific offer while retaining the current offline-quest contract. The chosen cutover is to retain introductory_hunt's existing tier objective and reward identity but remove its gate-local supply promise, describing a general low-tier wilderness hunt with no guaranteed immediate target. Current species-backed low-tier populations provide lawful ordinary encounters; no tier-example species is introduced. Other valid quests remain unchanged except quantity/source validation.

Explicitly amend `docs/superpowers/specs/2026-10-05-monster-data-model-design.md` §6 regional hunt paragraphs and §8 acceptance evidence to supersede immediate supply/provisioning with sparse-source validation, delayed recovery and unchanged deadlines. Mark its old proposal-delivery statements historical where they restate a superseded guarantee. Update `docs/game/commands.md`, `docs/game/command-reference.md` and the population developer document. Human review of truthful tutorial/quest wording is recorded there, not asserted by string/content pin tests. No new side quests, boss content, migration or fallback species.

## Risks / Trade-offs

The existing display-name, coordinate-slot and supply contracts have broad callers. Complete the named semantic caller cutover within this slice; do not add a parallel legacy path. Candidate-world validation and mutable Evennia cache restoration are part of correctness. Use synthetic independently known mechanism outcomes and real-owner integration controls instead of production data-echo tests.

## Verification and requirement traceability

During implementation, create an environment file outside tracked source containing `MUD_TEST_SETTINGS=1`. Focused command: `uv run --locked --env-file=/tmp/mud-population-test.env evennia test --settings test_settings.py --keepdb LABELS`. Replace LABELS with one affected focused method or class from the module inventory below, keeping the single-token env-file form; run independent focused invocations, never concatenate the whole inventory or exceed 100 discovered tests in one command. Use fixed synthetic inputs and independently known outputs. Production checks establish references, ownership/topology and profile obligations without copying shipped values or prose. New nonbrowser modules require exact ownership in `.github/evennia-shards.json`; browser methods, if added, require `.github/browser-shards.json` ownership. Run observability lint alongside focused tests when logging changes. Full managed browser and complete evidence verification remain CI-owned.

Before changing annotations, record each affected assertion's synthetic-mechanism, registry-contract or representative-smoke role and substantive replacement in `docs/development/regional-monster-population.md`. Canonical IDs below came from `uv run --locked python -m tools.spec_traceability list --json-output /tmp/regional-population-requirements.json`. ADDED requirements have no current IDs; never fabricate one. Before archive, use the tool on an equivalent merged spec tree, then replace provisional nearest-current claims with generated IDs. Retain no retired, empty or skipped claims. Each delta scenario maps to tasks.md test modules and must assert behavior rather than echo data.

After the completed slice run `openspec validate <change> --strict` and `uv run --locked python -m tools.contract_gate`. This gate does not establish coverage of unarchived deltas; the assertion-role ledger and focused evidence remain required. The runtime slice owns the cross-system real smoke; each earlier slice still owns real-owner integration and reload/fault controls.

## Deployment and rollback boundary

No migrations, legacy readers, aliases, implicit reset or compatibility setting are authorized. New ordinary runtime activates only at regional-population-runtime-cutover; earlier APIs are fully implemented and independently exercised through real owners. Operation failures restore durable and live surfaces through deterministic owner compensation. An incompatible development save requires documented explicit GM save/repair/reset procedures, never startup mutation. A source/code rollback requires its matching explicitly saved development state, with no incompatible-record reinterpretation.

### Nearest current canonical anchors

- `quest-lifecycle::accept-quest-creates-one-deterministic-active-record`: substantive current ownership/identity/lifecycle anchor; newly added behavior requires generated post-sync coverage, not an assertion-free extra decorator.
- `quest-lifecycle::bound-stage-bindings-survive-every-substitution-attempt`: substantive current ownership/identity/lifecycle anchor; newly added behavior requires generated post-sync coverage, not an assertion-free extra decorator.
- `guild-quest-board::board-acceptance-and-abandonment-delegate-to-quest-lifecycle`: substantive current ownership/identity/lifecycle anchor; newly added behavior requires generated post-sync coverage, not an assertion-free extra decorator.

### Focused implementation labels

`world.quests.tests.test_species_hunt_acceptance world.quests.tests.test_hunt_catalog_content world.quests.tests.test_site_clear_out_acceptance web.webclient.presentation.tests.test_map_quest_destinations`
