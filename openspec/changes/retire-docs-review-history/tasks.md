# Tasks

## 1. Specification changes

- [ ] 1.1 Apply `specs/evennia-test-optimization/spec.md`, `specs/webclient-browser-verification/spec.md`, `specs/npc-profile-registry/spec.md` and `specs/monster-ai-rollout/spec.md` as written.
- [ ] 1.2 Edit the `authored-dialogue-content` Purpose paragraph in `openspec/specs/authored-dialogue-content/spec.md`: a content slice owns its YAML files only; editorial quality is no longer claimed to live in `docs/lore/*-dialogue-review.md`.
- [ ] 1.3 Run `openspec validate retire-docs-review-history --strict`.

## 2. Delete the review and evidence pages

- [ ] 2.1 Delete the forty markdown pages listed in `proposal.md` under "Pages removed".
- [ ] 2.2 Delete `docs/development/monster-ai-activation-evidence/` and `docs/development/monster-ai-manual-evidence/` in full, including their JSON and TXT companions.
- [ ] 2.3 Delete `world/lore/npc_editorial_review.py` and remove `EditorialEntry`, `parse_editorial_ledger` and `check_editorial_ledger` from `world/lore/bestiary_documentation.py`.

## 3. Test surgery

- [ ] 3.1 Delete `world/lore/tests/test_npc_editorial_review.py` and `tests/test_webclient_frozen_contract.py`.
- [ ] 3.2 Delete `EditorialLedgerTests`, the `LEDGER` constant and the ledger imports from `world/lore/tests/test_bestiary_documentation.py`; keep the bestiary relationship tests.
- [ ] 3.3 Delete `TestOptimizationEvidenceTests` from `tests/test_evennia_test_optimization_contract.py`; keep the shard-ownership and fixture-boundary tests.
- [ ] 3.4 Rewrite `world/rules/tests/test_monster_ai_activation.py`: remove `ACTIVATION_RECORD`, `_record()`, the two `monster-ai-manual-evidence` path reads and the three evidence-file tests; derive activation and reflex-rollback assertions from `MONSTER_AI_TUNING`, `AI_ALGORITHM_VERSION` and the live reflex configuration.
- [ ] 3.5 Update the docstring in `web/tests/browser/test_map_editor_workflows.py` so it no longer cites `docs/design/map-editor-review.md`.

## 4. Reference cleanup

- [ ] 4.1 Remove the four deleted-page entries from `docs/_sidebar.md`.
- [ ] 4.2 Update `docs/development/adding-monsters.md`, `adding-npcs.md`, `adding-player-presets.md`, `monster-ai.md`, `evennia-testing-guide.md` and `narrative-memory-and-recall.md`: delete ledger/report links and instructions; replace them with the owning-change or git-history reference.
- [ ] 4.3 Update `docs/lore/bestiary.md` and `docs/lore/monster-creation-guidelines.md` to remove the editorial-ledger links while keeping the current indexed sections and the authoring guidance.
- [ ] 4.4 Update `AGENTS.md` and `README.md` to remove the `docs/development/evennia-test-performance.md` reference.
- [ ] 4.5 Update source comments in `world/lore/monster_activity.py`, `world/maps/population_forecast.py`, `world/lore/player_presets/data_story_cards.py` and `world/rules/rulebook/{buffs,combat_modifiers,equipment_effects}.yaml`.
- [ ] 4.6 Update `web/webclient-app/bridge.js`, `tools/contract_gate.py` and `tools/shard_register.py` wording that names the deleted audit/report.
- [ ] 4.7 Sweep `docs/` and the repository root for any remaining link or path to the 40 deleted pages; the only surviving mentions are inside `openspec/changes/archive/`.

## 5. Manifests and ledgers

- [ ] 5.1 Remove the `world/lore/tests/test_npc_editorial_review.py` entry from `tools/test_data_freeze.json` and `tools/test_data_lint_seed.json`.
- [ ] 5.2 Run `uv run --locked python -m tools.shard_register fix` and commit the resulting `.github/evennia-shards.json` and `.github/top-level-shards.json` changes.

## 6. Verification

- [ ] 6.1 Run `uv run --locked python -m tools.contract_gate`.
- [ ] 6.2 Run `uv run --locked python -m tools.spec_traceability check`.
- [ ] 6.3 Run the focused tests: `world.lore.tests.test_bestiary_documentation`, `world.rules.tests.test_monster_ai_activation`, `world.rules.tests.test_monster_ai_manual_reports`.
- [ ] 6.4 Serve `docs/` locally and confirm the sidebar has no dead route and no deleted page is reachable.
- [ ] 6.5 Report the removed requirements and the reduced guards (frozen audit, committed performance report, release-evidence record) in the handoff summary.
