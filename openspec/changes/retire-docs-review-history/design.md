# Design

## D1 - `docs/` is current state only

The Docsify site is the current operator/developer reference. Historical review records, evidence logs, profiling reports and audit snapshots live in git and `openspec/changes/archive/`; they are deleted rather than moved. The project is unreleased, so no redirect, compatibility page or migration is added.

`docs/superpowers/specs/**` is out of scope: those dated design documents are the architectural exception and are not Docsify pages.

## D2 - Deleted inventory

Forty markdown pages plus two evidence directories, exactly as listed in `proposal.md`. Deleting a directory removes its non-markdown companions too:

| Path | Non-markdown removed with it |
| --- | --- |
| `docs/development/monster-ai-activation-evidence/` | `activation.json`, `focused-tests.txt`, `gates.txt` |
| `docs/development/monster-ai-manual-evidence/` | `selector-check.json`, `performance.json`, six `archetype-*.json` |

No other `docs/` page is deleted.

## D3 - Test surgery

| Test surface | Action | Reason |
| --- | --- | --- |
| `world/lore/tests/test_npc_editorial_review.py` | Delete the module | It exists only to read the deleted ledger |
| `world/lore/tests/test_bestiary_documentation.py` | Delete `EditorialLedgerTests`, the `LEDGER` constant, ledger imports and the `parse_editorial_ledger`/`check_editorial_ledger` import | Bestiary relationship tests against `docs/lore/bestiary.md` stay |
| `tests/test_evennia_test_optimization_contract.py` | Delete `TestOptimizationEvidenceTests` and its `report` path read | The measurement-report requirement is removed |
| `tests/test_webclient_frozen_contract.py` | Delete the module | It exists only to parse the deleted audit |
| `world/rules/tests/test_monster_ai_activation.py` | Remove `ACTIVATION_RECORD`, `_record()`, the manual-evidence paths and the three evidence-file tests; rewrite record-derived assertions to read `MONSTER_AI_TUNING`, `AI_ALGORITHM_VERSION` and the live reflex configuration | The release-evidence requirement is removed; activation, retuning and rollback behavior stay |

`world/rules/tests/test_monster_ai_manual_reports.py`, `world/rules/tests/test_human_combat_calibration.py` and `web/tests/browser/test_map_editor_workflows.py` do not open the deleted files (only comments/docstrings mention them), so they only need comment updates.

## D4 - Production modules

- Delete `world/lore/npc_editorial_review.py`; its only consumer is the deleted test module.
- In `world/lore/bestiary_documentation.py`, remove `EditorialEntry`, `parse_editorial_ledger` and `check_editorial_ledger`; keep the bestiary document parser and relationship checks.
- `tools/monster_ai_manual_reports.py` keeps its `.var/monster-ai-manual-reports` default; only its docstring and the `adding-monsters.md` instructions stop naming `docs/`.

## D5 - Spec changes

Delta specs in this change:

| Capability | Operation | Effect |
| --- | --- | --- |
| `evennia-test-optimization` | REMOVED | Drops the committed pre/post performance-report requirement |
| `webclient-browser-verification` | REMOVED | Drops the Phase-0 frozen-audit deliverable requirement |
| `npc-profile-registry` | MODIFIED | Drops the committed-ledger sentence and the ledger-coverage scenario; keeps service-semantics behavior |
| `monster-ai-rollout` | MODIFIED + REMOVED | Live startup tuning replaces the report wording; the committed release-evidence requirement is removed |

`openspec/specs/authored-dialogue-content/spec.md` has a Purpose paragraph that names `docs/lore/*-dialogue-review.md`. Purpose is not expressible as a delta; edit that paragraph directly in the same change, per the OpenSpec instruction to change an existing capability's Purpose in the main spec. No requirement in that capability changes.

`monster-resource-abilities` and `monster-ai-manual-validation` need no delta: their requirements are still covered by the surviving bestiary/manual-report tool tests, which never read the deleted files.

## D6 - Reference cleanup

| Surface | Change |
| --- | --- |
| `docs/_sidebar.md` | Remove the four entries pointing at deleted pages |
| `docs/development/adding-monsters.md`, `adding-npcs.md`, `adding-player-presets.md` | Remove ledger/report instructions; point authors at the owning change instead |
| `docs/development/monster-ai.md`, `evennia-testing-guide.md`, `narrative-memory-and-recall.md` | Remove links to deleted reports/calibration pages |
| `docs/lore/bestiary.md`, `monster-creation-guidelines.md` | Remove ledger links and review-record wording; the current bestiary structure stays |
| `AGENTS.md`, `README.md` | Remove the profiling-report reference |
| `world/lore/monster_activity.py`, `world/maps/population_forecast.py`, `world/lore/player_presets/data_story_cards.py`, `world/rules/rulebook/{buffs,combat_modifiers,equipment_effects}.yaml` | Remove or reword comments that cite deleted files |
| `web/webclient-app/bridge.js`, `tools/contract_gate.py`, `tools/shard_register.py` | Remove audit/report wording |

## D7 - Manifests and ledgers

- Run `uv run --locked python -m tools.shard_register fix` after deleting the two test modules; commit both shard manifests.
- Remove the `world/lore/tests/test_npc_editorial_review.py` entries from `tools/test_data_freeze.json` and `tools/test_data_lint_seed.json`.
- The deleted tests carried `@covers_requirement` annotations for requirements that either remain covered elsewhere (`npc-profile-registry`) or are removed by this change; no unrelated annotation is added.

## Risks

| Risk | Mitigation |
| --- | --- |
| Removing the frozen-audit test loses the only guard on the four façades | The Vue migration is complete; the managed browser suite still targets the identifiers. The requirement removal is explicit in the delta. |
| Removing the performance-report test loses the 20% median assertion | The assertion was hardware-dependent and measured a one-time optimization; fixture-boundary and shard-ownership tests remain. |
| Activation tests lose their committed evidence | Tests are rewritten against live startup tuning, so they still detect a wrong mode, intelligence or fingerprint. |
| Traceability gate fails after test deletion | Only delete annotations for removed requirements or requirements with another annotated test; run `tools.spec_traceability check`. |
| Bestiary ledger was the only editorial completeness proof | `monster-resource-abilities` requires keyed documentation relationships, which the surviving tests still prove; editorial judgement is explicitly not testable. |

## Verification

```sh
uv run --locked python -m tools.contract_gate
uv run --locked python -m tools.spec_traceability check
uv run --locked python -m tools.test_data_lint check
uv run --locked python -m tools.observability_lint check
openspec validate retire-docs-review-history --strict
```

Focused behavior tests after the deletion:

```sh
uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.lore.tests.test_bestiary_documentation
uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.rules.tests.test_monster_ai_activation
uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.rules.tests.test_monster_ai_manual_reports
```

Docsify smoke: `uv run --locked python -m http.server --directory docs 3000`; the sidebar has no dead route and no deleted page is reachable.
