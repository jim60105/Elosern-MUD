# Proposal

## Why

`docs/` is the Docsify site for the current state of the game. Forty non-specification pages under `docs/` are instead dated review records, evidence logs, performance reports and audit snapshots. Git history and `openspec/changes/archive/` already retain that history, and the project has one developer, so the pages add no review value. They also carry tests that pin prose and historical numbers, which contradicts the repository rule that tests establish mechanics rather than echo content.

## What Changes

- Delete the forty review/evidence/audit markdown pages listed below, plus the two evidence directories in full (`activation.json`, `focused-tests.txt`, `gates.txt`, the eight manual-report JSON files).
- Delete the tests that exist only to read those files: `world/lore/tests/test_npc_editorial_review.py`, `tests/test_webclient_frozen_contract.py`, `EditorialLedgerTests` in `world/lore/tests/test_bestiary_documentation.py`, and `TestOptimizationEvidenceTests` in `tests/test_evennia_test_optimization_contract.py`.
- Rewrite `world/rules/tests/test_monster_ai_activation.py` to assert the live startup tuning and reflex rollback instead of reading the committed activation record and manual reports.
- Remove the production ledger parser `world/lore/npc_editorial_review.py` and the bestiary ledger parser functions once their tests are gone.
- Remove the four capability requirements that only demanded a committed historical artifact (see the delta specs) and edit the `authored-dialogue-content` Purpose paragraph directly.
- Update every surviving reference: `docs/_sidebar.md`, the authoring guides, `docs/lore/bestiary.md`, `docs/lore/monster-creation-guidelines.md`, `docs/development/monster-ai.md`, `docs/development/evennia-testing-guide.md`, `docs/development/adding-monsters.md`, `docs/development/adding-npcs.md`, `docs/development/adding-player-presets.md`, `docs/development/narrative-memory-and-recall.md`, `AGENTS.md`, `README.md`, source comments and tool messages.
- Delete the `.review` test-data ledger entries and regenerate the shard manifests with `python -m tools.shard_register fix`.
- **BREAKING (developer surface)**: the deleted Docsify routes and the sidebar entries that point at them disappear. No redirects or compatibility pages are added.

### Pages removed

- `docs/design/map-editor-review.md`
- `docs/lore/character-template-alignment.md`
- `docs/lore/ciaran-commons-dialogue-review.md`, `ciaran-crafts-dialogue-review.md`, `ciaran-fare-dialogue-review.md`, `ciaran-local-goods-review.md`
- `docs/lore/elven-dialogue-status-review.md`, `elven-residents-review.md`, `elven-village-goods-review.md`, `elven-villages-map-review.md`
- `docs/lore/eolas-craft-homes-review.md`, `eolas-fare-homes-review.md`
- `docs/lore/fionnen-craft-homes-review.md`, `fionnen-fare-homes-review.md`
- `docs/lore/guild-dialogue-review.md`, `landmark-rites-review.md`
- `docs/lore/lower-civic-dialogue-review.md`, `lower-hospitality-dialogue-review.md`
- `docs/lore/middle-exchange-dialogue-review.md`, `middle-tools-dialogue-review.md`
- `docs/lore/upper-civic-dialogue-review.md`, `upper-faith-dialogue-review.md`
- `docs/development/bestiary-editorial-review.md`, `npc-editorial-review.md`
- `docs/development/human-combat-calibration-evidence.md`, `monster-content-expansion.md`, `monster-field-behaviour.md`
- `docs/development/evennia-test-performance.md`, `dialogue-epoch-calibration.md`, `webclient-vue-frozen-contract-audit.md`
- `docs/development/monster-ai-activation-evidence/` (whole directory)
- `docs/development/monster-ai-manual-evidence/` (whole directory)

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `evennia-test-optimization` - remove the requirement that mandates a committed pre/post performance report.
- `webclient-browser-verification` - remove the requirement that mandates the Phase-0 frozen contract audit deliverable.
- `npc-profile-registry` - drop the committed characterization ledger sentence and its ledger-coverage scenario; the remaining behavior scenarios stay.
- `monster-ai-rollout` - stop requiring a committed release-evidence record, and stop describing old reports as retained historical evidence.
