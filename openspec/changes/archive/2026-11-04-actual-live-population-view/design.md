# Design

## Context

`PopulationFact` already carries observation_key, cell, kind, hostile, label, threat_tier and danger_grade. `population_view` mixes expected ambient slots with real registered foreign entities. `travel_interrupts` and `presentation/area_map.py` read it, while GM `monsters.region_of` guesses region from the first ambient variant match.

## Goals / Non-Goals

Deliver this proposal's bounded regional-population prerequisite or cutover, using existing deterministic owners and real runnable operations. Do not implement adjacent field movement/aggression/escape or independent monster content. No compatibility paths or save conversion.

## Decisions

### Actual living read contract
Keep `population_view(wilderness, cells: Iterable[tuple[int,int]]) -> tuple[PopulationFact,...]` and the existing fact fields. Build one index over actual `itemcoordinates`; include each living Monster with valid requested current coordinate exactly once using `observation_key=f"object:{pk}"`. Existing character/NPC observation support stays intact. Stored HP reads must not construct traits or tick a gauge. Read canonical variant-derived threat/grade through the current individual helpers. Stable IDs survive rename, recycled rooms and depletion; a newly born object gets a fresh observation key. An uninitialized/empty/blocked/due habitat has no monster fact. Home ownership, site state or a composition declaration alone is not evidence of physical presence. Do not hide a living site member merely because its original site coordinate differs; physical registration is authoritative. Exclude dead, deleted and unregistered/absent IDs. No rooms, reconciliation, schedules, sequence, initialization or mutation events on reads.

Remove this function's dependency on `ambient_population_decision`, ExpectedSlot, ambient_observation_key, capital_entry and slot matching. Leave still-used creation helpers for the final runtime cutover; do not keep a slot projection alias or a second view. Explicit placed members and visitors are ordinary actual facts regardless of owner. Registry unavailable answers preserve existing named read-unavailable conventions without fabricating an expected species.

### Consumer contract
Migrate `world/rules/travel_interrupts.py`, sight-change comparison and `web/webclient/presentation/{area_map,local_map/wilderness}.py` to compare object identities only. Entering/recycling a room with the same existing ID produces no synthetic new-hostile event; a genuinely new living object may produce the existing committed new-sighting/hostile interrupt. Scheduled future waves never do. Existing movement/observation transaction rules and read fog/knowledge restrictions are unchanged. This slice does not add aggression or automatic encounter admission.

Change `web/gm/readers/monsters.py::{region_of,placement_section}` to report home ecology-zone ownership and actual coordinate/region independently; do not infer ownership from variant membership or original site coordinate. Migrate relevant list filters, registry summaries and tests that currently assume AmbientPlacementRule, but leave final old-registry deletion to runtime cutover. No new GM mutation verbs are added. Generic registry-index machinery exposes new immutable ecology rows without a copied key roster.

Regional hunt destinations are habitat guidance handled by the quest cutover. Preserve destination markers when no live target exists and never emit them as monster facts or exact entity targets. Exact entity actions revalidate actual ID/presence and never substitute another same-name monster. If this slice lands before quest guidance cutover, retain the existing regional destination behavior until that owning change; the public fact interface still changes atomically now.

### Tests and documentation
Replace prospective/materialization identity expectations in wilderness population tests and travel/area-map tests with synthetic actual registration assertions. Add no-copy tests by observing untouched Attributes/object/room counts and sequence before/after repeated reads. In `docs/development/regional-monster-population.md`, document actual-view semantics, habitat versus entity markers and GM ownership/current-position distinction. Human review assesses truthful labeling separately from testable presence and identity.

## Risks / Trade-offs

The existing display-name, coordinate-slot and supply contracts have broad callers. Complete the named semantic caller cutover within this slice; do not add a parallel legacy path. Candidate-world validation and mutable Evennia cache restoration are part of correctness. Use synthetic independently known mechanism outcomes and real-owner integration controls instead of production data-echo tests.

## Verification and requirement traceability

During implementation, create an environment file outside tracked source containing `MUD_TEST_SETTINGS=1`. Focused command: `uv run --locked --env-file=/tmp/mud-population-test.env evennia test --settings test_settings.py --keepdb LABELS`. Replace LABELS with one affected focused method or class from the module inventory below, keeping the single-token env-file form; run independent focused invocations, never concatenate the whole inventory or exceed 100 discovered tests in one command. Use fixed synthetic inputs and independently known outputs. Production checks establish references, ownership/topology and profile obligations without copying shipped values or prose. New nonbrowser modules require exact ownership in `.github/evennia-shards.json`; browser methods, if added, require `.github/browser-shards.json` ownership. Run observability lint alongside focused tests when logging changes. Full managed browser and complete evidence verification remain CI-owned.

Before changing annotations, record each affected assertion's synthetic-mechanism, registry-contract or representative-smoke role and substantive replacement in `docs/development/regional-monster-population.md`. Canonical IDs below came from `uv run --locked python -m tools.spec_traceability list --json-output /tmp/regional-population-requirements.json`. ADDED requirements have no current IDs; never fabricate one. Before archive, use the tool on an equivalent merged spec tree, then replace provisional nearest-current claims with generated IDs. Retain no retired, empty or skipped claims. Each delta scenario maps to tasks.md test modules and must assert behavior rather than echo data.

After the completed slice run `openspec validate <change> --strict` and `uv run --locked python -m tools.contract_gate`. This gate does not establish coverage of unarchived deltas; the assertion-role ledger and focused evidence remain required. The runtime slice owns the cross-system real smoke; each earlier slice still owns real-owner integration and reload/fault controls.

## Deployment and rollback boundary

No migrations, legacy readers, aliases, implicit reset or compatibility setting are authorized. New ordinary runtime activates only at regional-population-runtime-cutover; earlier APIs are fully implemented and independently exercised through real owners. Operation failures restore durable and live surfaces through deterministic owner compensation. An incompatible development save requires documented explicit GM save/repair/reset procedures, never startup mutation. A source/code rollback requires its matching explicitly saved development state, with no incompatible-record reinterpretation.

### Nearest current canonical anchors

- `wilderness-population-view::population-reads-share-materialization-decisions`: substantive current ownership/identity/lifecycle anchor; newly added behavior requires generated post-sync coverage, not an assertion-free extra decorator.
- `wilderness-population-view::observation-identities-survive-materialization`: substantive current ownership/identity/lifecycle anchor; newly added behavior requires generated post-sync coverage, not an assertion-free extra decorator.
- `wilderness-travel-interrupts::wilderness-steps-report-stateless-committed-interrupts`: substantive current ownership/identity/lifecycle anchor; newly added behavior requires generated post-sync coverage, not an assertion-free extra decorator.

### Focused implementation labels

`world.maps.tests.test_wilderness_population world.maps.tests.test_wilderness_population_species world.rules.tests.test_travel_events web.webclient.presentation.tests.test_area_map`
