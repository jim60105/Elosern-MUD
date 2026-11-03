# Proposal

## Why

Regional hunts currently demand immediate living supply and provision the shortfall at acceptance. This contradicts sparse habitats and delayed recovery across multiple encounters.

## What Changes

- **BREAKING** Remove ordinary acceptance-time provisioning and per-coordinate quantity limits, validating lawful authored ecological or explicit supply instead.
- Keep issuance/rank/deadline rules and exact standing site bindings, retain truthful habitat guidance while undersupplied, and remove the introductory guaranteed hunting assumption.
- Amend the approved monster data-model guarantee explicitly and retire obsolete provisioning code, tests and documentation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quest-blueprint`: Revise the behavior contract in this change's delta.
- `quest-lifecycle`: Revise the behavior contract in this change's delta.
- `guild-quest-board`: Revise the behavior contract in this change's delta.

## Impact

`world/quests/runtime.py::_provision_hunt_targets` invokes `monster_provisioning.ensure_hunt_targets` inside acceptance, with special provisioning snapshots. `test_hunt_catalog_content.py` enforces the ambient per-cell ceiling. Existing map_quest_destinations resolves a species hunt to the nearest legal geographic-region cell, independently of living entities, but it does not restrict that destination to a permitted source habitat.

Planning only for `docs/superpowers/specs/2026-11-03-regional-monster-population-design.md`, under the 2026-07-29 architecture. Offline deterministic single-writer ownership is retained. No implementation, apply, archive, migration or main-spec edit occurs in this proposal commit. Human judgments of ecology, tutorial wording and presentation truthfulness are reviewed in `docs/development/regional-monster-population.md` during implementation; tests establish mechanisms rather than shipped wording or balance values.

## Batch:

depends-on: regional-ecology-authoring

Code conflicts:
- manual-monster-compositions changes site declarations and acceptance tests; these slices share clear-out tests and must serialize shared edits.
- regional-population-runtime-cutover removes ambient registries after this change deletes all provisioning consumers.
- actual-live-population-view shares map_quest_destinations and habitat-guidance presentation tests; assign those edits to this quest slice and rebase view expectations afterward.
