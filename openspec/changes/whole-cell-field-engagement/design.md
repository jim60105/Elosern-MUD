# Design

## Context

`_room_monsters` already returns living co-located monsters sorted by pk. `_opening_line_up`, `_candidate_record` and `_prepare_opening` pass a skill-dependent target list through candidate reconstruction, validation and engagement. `engage` delegates to `engage_group(actor, [target])`; explicit examinations have a separate mode.

## Goals / Non-Goals

Deliver this proposal's bounded regional-population prerequisite or cutover, using existing deterministic owners and real runnable operations. Do not implement adjacent field movement/aggression/escape or independent monster content. No compatibility paths or save conversion.

## Decisions

### Roster and recipient contract
Add `field_enemy_roster(actor: Any) -> tuple[Monster, ...]` to `world/rules/combat_initiation.py`, replacing `_room_monsters` as the shared collection helper. It returns every living co-located Monster sorted by integer pk or an empty tuple when unlocated. It does not inspect ownership, species or group markers and writes nothing.

Keep `engage_group(actor, targets, *, opening_first_actor=None)` as the exact explicitly staged opponent API. Change ordinary `engage(actor, target)` to validate its requested anchor target first and call `engage_group(actor, field_enemy_roster(actor))`. Do not sweep spectators into `guild_exam` or other explicitly staged callers of `engage_group`. Route all text/browser ordinary engagement through `engage`, never a one-element `engage_group` bypass.

Keep `initiate_field_combat(actor, skill_key, target, scale=1.0, ...)` and companion authority. In `_prepare_opening`, compute `enemies = field_enemy_roster(commander)` independently of `recipients`: SINGLE uses `(target,)`; AREA uses the existing explicit concrete eligible enemy expansion and normal target/faction rules. NONE/SELF retain existing target-shape refusal here. Build `_candidate_record(commander, enemies)` and preflight only recipients. Extend `FieldOpeningPreview` with `enemies: tuple[Any, ...]`, preserving its `targets` as recipients; migrate all constructors and readers. Commit calls `engage_group` with `preview.enemies`, then `submit_opening_action` with `preview.targets`. Neither costs nor harmful-effect detection decides membership. Preserve existing explicit out-of-combat availability gate and seed/draft behavior.

### Boundaries and negative controls
Own `world/rules/combat_initiation.py`, `combat_session/lifecycle.py`, `commands/{combat,action}.py`, browser action adapters and skill/engagement previews. Do not modify skill formulas, AI decisions, manual lifecycle, aggression or movement. Require identical preview/commit enemy IDs. Revalidate stale/dead/remote anchor IDs without substituting same-label bystanders. Test direct API, command, browser dispatcher and companion initiator, including a non-damaging opening, AREA, pending companion draft and rollback after a real seed/session write. Add behavior docs to both command reference files, preserving discovery docs checks.

## Risks / Trade-offs

The existing display-name, coordinate-slot and supply contracts have broad callers. Complete the named semantic caller cutover within this slice; do not add a parallel legacy path. Candidate-world validation and mutable Evennia cache restoration are part of correctness. Use synthetic independently known mechanism outcomes and real-owner integration controls instead of production data-echo tests.

## Verification and requirement traceability

During implementation, create an environment file outside tracked source containing `MUD_TEST_SETTINGS=1`. Focused command: `uv run --locked --env-file=/tmp/mud-population-test.env evennia test --settings test_settings.py --keepdb LABELS`. Replace LABELS with one affected focused method or class from the module inventory below, keeping the single-token env-file form; run independent focused invocations, never concatenate the whole inventory or exceed 100 discovered tests in one command. Use fixed synthetic inputs and independently known outputs. Production checks establish references, ownership/topology and profile obligations without copying shipped values or prose. New nonbrowser modules require exact ownership in `.github/evennia-shards.json`; browser methods, if added, require `.github/browser-shards.json` ownership. Run observability lint alongside focused tests when logging changes. Full managed browser and complete evidence verification remain CI-owned.

Before changing annotations, record each affected assertion's synthetic-mechanism, registry-contract or representative-smoke role and substantive replacement in `docs/development/regional-monster-population.md`. Canonical IDs below came from `uv run --locked python -m tools.spec_traceability list --json-output /tmp/regional-population-requirements.json`. ADDED requirements have no current IDs; never fabricate one. Before archive, use the tool on an equivalent merged spec tree, then replace provisional nearest-current claims with generated IDs. Retain no retired, empty or skipped claims. Each delta scenario maps to tasks.md test modules and must assert behavior rather than echo data.

After the completed slice run `openspec validate <change> --strict` and `uv run --locked python -m tools.contract_gate`. This gate does not establish coverage of unarchived deltas; the assertion-role ledger and focused evidence remain required. The runtime slice owns the cross-system real smoke; each earlier slice still owns real-owner integration and reload/fault controls.

## Deployment and rollback boundary

No migrations, legacy readers, aliases, implicit reset or compatibility setting are authorized. New ordinary runtime activates only at regional-population-runtime-cutover; earlier APIs are fully implemented and independently exercised through real owners. Operation failures restore durable and live surfaces through deterministic owner compensation. An incompatible development save requires documented explicit GM save/repair/reset procedures, never startup mutation. A source/code rollback requires its matching explicitly saved development state, with no incompatible-record reinterpretation.

### Nearest current canonical anchors

- `field-combat-initiation::validation-runs-against-a-candidate-battlefield-that-is-never-persisted-under-a-combat-context`: substantive current ownership/identity/lifecycle anchor; newly added behavior requires generated post-sync coverage, not an assertion-free extra decorator.
- `field-combat-initiation::session-creation-and-the-opening-action-share-one-failure-boundary`: substantive current ownership/identity/lifecycle anchor; newly added behavior requires generated post-sync coverage, not an assertion-free extra decorator.
- `player-combat-session::engage-group-opens-one-session-against-several-co-located-hostile-targets`: substantive current ownership/identity/lifecycle anchor; newly added behavior requires generated post-sync coverage, not an assertion-free extra decorator.

### Focused implementation labels

`world.rules.tests.test_combat_initiation world.rules.tests.test_combat_session_flow.test_engage_group_flow commands.tests.test_combat_actions`
