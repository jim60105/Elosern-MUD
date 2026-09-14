# Tasks — Phase B SkillCategory taxonomy consolidation

> **Serialization gate (blocking):** Do NOT start any task below until the seven active
> `light-*` changes (light-judgment-traits, light-sustained-recovery, light-penance-events,
> light-sacrament-casting, light-climax-empowerment, light-cleric-feedback, light-spell-catalog)
> are implemented, archived, and their delta specs synced to main specs — `openspec/changes/`
> holds no `light-*` directory and `openspec/specs/skill-registry/spec.md` already carries
> change-10's synced light requirement. This change edits `world/skills/registry.py` and
> `world/skills/tests/test_skill_registry.py`, which are light-spell-catalog's (order 10)
> integration ownership, and its partition counts must include the 16 synced light nodes.
> Main-spec synchronization of THIS change's deltas likewise happens only in the separately
> authorized archive/sync workflow after these tasks are done.

## 1. Taxonomy code cutover

- [ ] 1.1 Confirm the apply gate above observably (archive listing + synced main spec present); then re-inspect `world/skills/registry.py`, `world/rules/disengage.py`, `world/rules/combat_view.py`, `world/rules/status_query.py`, `web/static/webclient/js/elosern/protocol.js` against this change's design.md D2 table — the post-change-10 registry may differ from the proposal-time snapshot; adopt the current content, do not assume it.
- [ ] 1.2 Drop `MOVEMENT`/`INNATE_GIFT` from `SkillCategory` and re-home the five `registry.py` construction sites per the D2 table (`flight`/`flash_step` → `ENHANCEMENT` group `"身法"`; `elf_longevity`/`reincarnation_boon_elosia`/`reincarnation_boon_yuka` → `ENHANCEMENT` group `"天賦"`); change only `category`/`group` kwargs — no effect/kind/cost/element edits anywhere.
- [ ] 1.3 Re-home `flee`'s explicit `category` kwarg in `world/rules/disengage.py` to `SkillCategory.MARTIAL_ARTS` (still declared at its own construction site), and re-kwarg the four helper/test construction sites that import the retired members: `world/rules/tests/test_movement.py` `_DART_STEP` → `MARTIAL_ARTS`; `world/rules/tests/_combat_session_helpers.py` `synth_innate_overlay()` flee row → `MARTIAL_ARTS` (shared by 15+ test modules); `web/browser_support/browser_fixtures_data.py` synth flee row → `MARTIAL_ARTS`; `world/rules/tests/test_status_query.py` module-level `_ROW_REST` category tuple → `ENHANCEMENT` tags / `MARTIAL_ARTS`. These are import/call-time `AttributeError`s, not edit-optional.
- [ ] 1.4 Update `CATEGORY_LABELS`/`_CATEGORY_LABELS` in `combat_view.py`/`status_query.py` (drop 移動/天賦 entries) and add the `ENHANCEMENT` sub-group ordering branch (null → 天賦 → 身法, fixed, ownership-independent) in `group_skill_views()` and `group_skill_keys()`; `lineage_query.py` and `progression.py` need no edit — verify by import/behavior, not by reading alone.
- [ ] 1.5 Drop `"movement"`/`"innate_gift"` from `SKILL_CATEGORY_KEYS` in `protocol.js` and shrink `CHARACTER_MAX_CATEGORY_GROUPS` 9 → 7 to mirror Python's `len(SkillCategory)+1`; verify the validator's category-count bound follows from the shrunk mirror and that enhancement group keys (CJK strings) pass the existing group validation as sexual_act's do.

## 2. Contract + behavior tests

- [ ] 2.1 Rewrite `world/skills/tests/test_skill_registry.py` presentation contracts: `_CATEGORY_ORDER` (6 members), `_UNGROUPED_CATEGORIES`, the D4 per-category key-set test (re-homed keys move; group tags asserted), `FleeCategoryDeclarationTests` (both `SkillCategory.MOVEMENT` assertions incl. the disengage.py AST source check → `MARTIAL_ARTS`; canonical ID `universal-action-ownership::flee-declares-its-skill-category-at-its-own-construction-site` unchanged), and the enum member-set test — annotating with the literal canonical IDs `skill-category-registry::skillcategory-enumerates-exactly-six-presentation-categories`, `skill-category-registry::skill-registry-s-entries-partition-exactly-across-the-six-categories`, `skill-category-registry::category-group-vocabulary-is-closed-per-category`, `skill-category-registry::classifying-a-skill-changes-no-other-field` (IDs from the delta's RENAMED set; confirm via `tools.spec_traceability list` after delta sync).
- [ ] 2.2 Prove acquisition-path passives still resolve after re-bucketing (run, extend only if a gap exists): flight waiver `world/rules/tests/test_movement.py` → `movement-cost-charging::charge-movement-is-the-single-shared-movement-cost-charging-function`; `skill_owned` rows incl. `reincarnation_boon_yuka` → `combat-modifier-table::the-eight-previously-dead-passive-buff-combat-prediction-skills-each-grant-a-real-adjustment`; `reincarnation_boon_elosia` growth_rate and `elf_longevity` inert-trait resolution paths; `flee` disengage behavior. No new data-echo tests.
- [ ] 2.3 Re-pin grouping-presentation tests to the six-category shape and enhancement tag sub-groups: `world/rules/tests/test_combat_view.py`, `world/rules/tests/test_status_query.py` (`webclient-exploration-menu::character-panel-skills-are-grouped-by-category-with-the-same-ordering-rule-as-the-combat-panel`; `_ROW_REST` covered by 1.3), `webclient/presentation/tests/test_combat_panel.py` (`webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices`), `test_character_panel.py`, JS `web/static/webclient/js/tests/protocol.test.js` + `combat_menu.test.js` + `character_menu.test.js`, and the `web/webclient-app` fixtures naming retired category keys — `tests/preserved_contract.test.js` (`innate_gift` payload re-aims at a surviving category; the client validator rejects non-mirrored keys), `tests/data/skill_book.test.js`, `stories/fixtures.js`, store-frame-test fixtures.
- [ ] 2.4 Re-pin the managed-browser suite (edit-only locally; browser-shards CI owns execution): `web/tests/browser/test_browser_combat.py` — `_open_category(page, "movement")` flee navigation → `martial_arts`, and the enum-order panel assertion (`test_panel_groups_skills_by_category_in_enum_order`) → the six-key list. No new shard owner; verify the touched methods stay in their current `.github/browser-shards.json` shard.

## 3. Doc consistency + integration checks

- [ ] 3.1 `docs/lore/magic-system.md`: §2 table → six-branch taxonomy naming the three mechanic families and the 身法/天賦 display tags; §5/§7/§8 prose follow design.md D5 in Phase A's 唯一權威 voice; keep narrative, re-add no tables.
- [ ] 3.2 `docs/lore/skill-trees/index.md` §7 非魔法分支 table: 身法/天賦異能 rows re-labeled as display-tag rows under 身心強化; `enhancement.md` gains the merged acquired-passives framing with the two tag tables; `movement.md`/`innate-gift.md` headers state the display-tag categorization, and every in-body `SkillCategory.INNATE_GIFT`/`MOVEMENT` enum-name reference (e.g. innate-gift.md 機制備註) is reworded — all three pages stay the per-key acquisition authorities.
- [ ] 3.3 Re-verify (do not pre-edit) that no player command surface is affected: `docs/game/commands.md` / command-reference name no category-dependent behavior for flight/flash_step/flee; run `tests.test_command_docs`-equivalent if any doc test exists for the touched pages.
- [ ] 3.4 Shard-manifest/traceability impact check: confirm no new test modules (`.github/evennia-shards.json` / `browser-shards.json` manifests untouched — in-shard test edits keep their existing owners per 2.4's check, `tools/test_data_freeze.json` unmodified unless a task above added a file); run `uv run --locked python -m tools.spec_traceability check` and confirm no unknown IDs from the renamed set are cited before sync (post-sync annotation of new/modified tests happens with the archive/sync workflow per docs/development/spec-test-traceability.md).
- [ ] 3.5 Run the focused batch below plus the JS unit gates (`node --test web/static/webclient/js/tests/*.test.js`; vitest for `web/webclient-app` per the frontend guide); all proof comes from the specific tests, not from reading code.

### Focused invocation

```sh
uv run --locked evennia test --settings test_settings.py --keepdb world.skills.tests.test_skill_registry world.skills.tests.test_spell_catalogs world.rules.tests.test_movement world.rules.tests.test_combat_view world.rules.tests.test_status_query webclient.presentation.tests.test_combat_panel webclient.presentation.tests.test_character_panel
node --test web/static/webclient/js/tests/protocol.test.js
uv run --locked python -m tools.test_data_lint check
uv run --locked python -m tools.spec_traceability check
openspec validate skill-taxonomy-consolidation --strict
```

Pass `MUD_TEST_SETTINGS=1` through the tool environment where the test runner needs it. No full local browser/evidence/aggregate-coverage run. No apply, archive, main-spec sync or branch merge in the proposal turn.
