# Design

## Context

`Battlefield.__post_init__` equates roster keys with `entity.key`. `reconstruct_battlefield` rejects duplicate labels although records already persist integer dbrefs. `stable_actor_id` and monster-AI `stable_identity` already use dbrefs for real entities but fall back to names for synthetic ones. `RoundRecord.identities` already maps roster keys to dbrefs.

## Goals / Non-Goals

Deliver this proposal's bounded regional-population prerequisite or cutover, using existing deterministic owners and real runnable operations. Do not implement adjacent field movement/aggression/escape or independent monster content. No compatibility paths or save conversion.

## Decisions

### Identity contract and complete cutover
Keep `Battlefield.teams: dict[str, frozenset[str]]`, `roster: dict[str, Any]`, `fled: set[str]`, `knocked_out: set[str]` and `RoundTactical` string-key shapes. Change the existing `stable_actor_id(entity: Any) -> str` in `world/rules/combat/decision_scope.py` to return `dbref:<positive integer pk>` for persisted actors. Nonpersistent pure actors MUST supply an explicit nonempty `combat_identity: str`; return `fixture:<combat_identity>`. Missing, boolean or malformed identities raise `ValueError` before mutation. `world/rules/monster_ai/models.py::stable_identity` delegates to that identity contract. Do not append suffixes to display names, derive IDs from labels, retain name-key fallbacks or read old saves.

Use the helper for every identity lookup, membership, order/tie-break, nonlethal key, action bookkeeping, log participant reference and AI observation. `Battlefield` validates exact identity-to-object correspondence and unique participants; contexts reject a non-roster object even with the same label. Reconstruct from record dbrefs, sort persistent IDs numerically for admission, retain record order for a/e tokens. Renaming after selection cannot alter identity. Existing `CombatSessionRecord` fields stay JSON-safe, including opening-first-actor identity; no migration or alias parser.

### Source boundary
Migrate the identity-bearing uses in `world/rules/combat/{battlefield,rounds,damage,healing,decision_scope}.py`, `combat_session/{battlefield,lifecycle,rounds,policies,scans,settlement,observations,records}.py`, `combat_beats.py`, `targeting.py`, `disengage.py`, `overwhelm.py`, `monster_behaviour.py`, and `monster_ai/{models,snapshot,candidates,legality,estimation,utility,manual_campaign}.py`. Follow participant references from `world/rules/action/` and effect handlers into `world/quests/planner.py`, `world/narrative/action_adapters.py`, command/combat-result rendering and `web/webclient/presentation/{combat_panel,combat_beats,skill_use}.py`. Preserve prose labels separately when an EventLog identity becomes a dbref. This is a semantic audit of identity uses, not a blanket `.key` replacement. Use CodeGraph caller sets and literal identity lookups to enumerate and finish every affected production and fixture caller in the same change. Do not alter balance, AI scoring, escape location, population placement or roster admission policy.

### Acceptance and evidence
Synthetic `A + A + B` with different HP/resources establishes unique initiative, target, Defend/Dodge/Taunt, healing, flee, knockout, AI observation and defeat credit. Rename A after draft selection, reload an unfinished session, then resolve the chosen A and show the other A remains unchanged by that effect. A duplicate exact entity still rejects before persistence. Existing exam and bounded pure-combat paths use the same Battlefield with explicit fixture IDs. Inject failure after a recipient write and require database reload, live caches, draft and observation memory to match baseline. Human review of labels is recorded in `docs/development/regional-monster-population.md`; wording is not a test requirement.

## Risks / Trade-offs

The existing display-name, coordinate-slot and supply contracts have broad callers. Complete the named semantic caller cutover within this slice; do not add a parallel legacy path. Candidate-world validation and mutable Evennia cache restoration are part of correctness. Use synthetic independently known mechanism outcomes and real-owner integration controls instead of production data-echo tests.

## Verification and requirement traceability

During implementation, create an environment file outside tracked source containing `MUD_TEST_SETTINGS=1`. Focused command: `uv run --locked --env-file=/tmp/mud-population-test.env evennia test --settings test_settings.py --keepdb LABELS`. Replace LABELS with this slice's labels below, keeping the single-token env-file form. Use fixed synthetic inputs and independently known outputs. Production checks establish references, ownership/topology and profile obligations without copying shipped values or prose. New nonbrowser modules require exact ownership in `.github/evennia-shards.json`; browser methods, if added, require `.github/browser-shards.json` ownership. Run observability lint alongside focused tests when logging changes. Full managed browser and complete evidence verification remain CI-owned.

Before changing annotations, record each affected assertion's synthetic-mechanism, registry-contract or representative-smoke role and substantive replacement in `docs/development/regional-monster-population.md`. Canonical IDs below came from `uv run --locked python -m tools.spec_traceability list --json-output /tmp/regional-population-requirements.json`. ADDED requirements have no current IDs; never fabricate one. Before archive, use the tool on an equivalent merged spec tree, then replace provisional nearest-current claims with generated IDs. Retain no retired, empty or skipped claims. Each delta scenario maps to tasks.md test modules and must assert behavior rather than echo data.

After the completed slice run `openspec validate <change> --strict` and `uv run --locked python -m tools.contract_gate`. This gate does not establish coverage of unarchived deltas; the assertion-role ledger and focused evidence remain required. The runtime slice owns the cross-system real smoke; each earlier slice still owns real-owner integration and reload/fault controls.

## Deployment and rollback boundary

No migrations, legacy readers, aliases, implicit reset or compatibility setting are authorized. New ordinary runtime activates only at regional-population-runtime-cutover; earlier APIs are fully implemented and independently exercised through real owners. Operation failures restore durable and live surfaces through deterministic owner compensation. An incompatible development save requires documented explicit GM save/repair/reset procedures, never startup mutation. A source/code rollback requires its matching explicitly saved development state, with no incompatible-record reinterpretation.

### Nearest current canonical anchors

- `battlefield-action-context::is-present-checks-canonical-battlefield-roster-membership`: substantive current ownership/identity/lifecycle anchor; newly added behavior requires generated post-sync coverage, not an assertion-free extra decorator.
- `player-combat-session::startup-restores-valid-sessions-and-terminates-invalid-references-safely`: substantive current ownership/identity/lifecycle anchor; newly added behavior requires generated post-sync coverage, not an assertion-free extra decorator.
- `monster-individual-construction::kill-accounting-keys-on-persistent-individual-identity-and-dedupes-duplicate-defeat-events`: substantive current ownership/identity/lifecycle anchor; newly added behavior requires generated post-sync coverage, not an assertion-free extra decorator.

### Focused implementation labels

`world.rules.tests.test_combat_session_persistence world.rules.tests.test_combat_session_targeting world.rules.tests.test_disengage_integration world.rules.tests.test_monster_ai_selection world.rules.tests.test_combat_beats`
