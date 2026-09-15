# Design — Phase B SkillCategory taxonomy consolidation

## D0. Apply-phase serialization contract (hard gate)

**Nothing in this change is implemented until the seven active `light-*` changes are implemented, archived, and their deltas synced to main specs** (light-effect-potency, light-divinity-tier and light-effect-routing are already archived+synced as of 2026-09-14; the operative condition — archive listing empty of `light-*` and `skill-registry` main spec carrying change 10's synced light requirement — is what tasks.md gates on). Rationale (docs/superpowers/specs/2026-08-12-skill-system-redesign-design.md §11):

- `light-spell-catalog` (wave order 10) is the integration owner of `world/skills/registry.py`'s light rows, the `skill-registry` main-spec light-requirement replacement, and the shard-manifest/traceability/doc integration for the whole light wave. This change edits the same file's enum and five non-light construction sites, and its partition re-pinning must count the 16 light nodes `change 10` registers into `ELEMENTAL_MAGIC` group `light`.
- `world/skills/tests/test_skill_registry.py` is edited by both (change 10 removes light echo tests; this change rewrites `_CATEGORY_ORDER`, `_UNGROUPED_CATEGORIES`, and the D4 classification-table test).
- §11 mandates serialization of everything touching `registry.py`/`effects.py`/`action.py` behind change 10, and the skill-registry presentation deltas here must build on change 10's post-archive synced snapshot — pre-sync, the main-spec light requirement this change deliberately does not touch is still the old flat-catalog text.

The proposal itself has no code. Tasks carry the same gate at their top.

## D1. Ratified mechanic taxonomy (givens; do not relitigate)

Three families:

| Family | Categories | Parameters |
|---|---|---|
| Prerequisite-DAG skill 譜 | `ELEMENTAL_MAGIC` (MP), `MARTIAL_ARTS` (SP), `UTILITY` (MP, empty today), `DIVINE_MYSTERY` (zero-cost + research-digest cadence + divine gate) | one mechanism (use-driven `SkillPrerequisite` DAG, progression.py), three parameters: resource axis, learning cadence, divine gate |
| Acquired passives | `ENHANCEMENT` (absorbs former `MOVEMENT`/`INNATE_GIFT` content) | keyed by acquisition condition, per `docs/lore/skill-trees/enhancement.md` format; no ownership-through-practice path exists for these |
| Sexual-act catalog | `SEXUAL_ACT` + `SEXUAL_ACT_REGISTRY` counter mechanism | deliberately independent by design; untouched |

`SkillCategory` drops from 8 to 6 members: `ELEMENTAL_MAGIC, MARTIAL_ARTS, ENHANCEMENT, DIVINE_MYSTERY, UTILITY, SEXUAL_ACT` (declaration order preserved for surviving members; display order stays the contract of `skill-category-registry`).

## D2. Full per-key re-homing table (every currently-MOVEMENT/INNATE_GIFT-categorized key, from registry.py + world/rules/disengage.py)

Investigation baseline (runtime registry, with `world.rules.disengage` imported): MOVEMENT = {`flight`, `flash_step`, `flee`}, INNATE_GIFT = {`elf_longevity`, `reincarnation_boon_elosia`, `reincarnation_boon_yuka`}. Note `reincarnation_boon_yuna` is already `SEXUAL_ACT` group 精通 and is **not** touched.

| Key | From (category/group) | To (category/group) | Mechanics preserved verbatim |
|---|---|---|---|
| `flight` | MOVEMENT / None | ENHANCEMENT / `"身法"` | `movement:flight` typed effect, PASSIVE, D8 wilderness-move cost waiver in `world/rules/movement.py`, `mp=22` cost (wind-catalog row stays: the `skill-registry` 風-element requirement pins key/kind/cost/effects, never category) |
| `flash_step` | MOVEMENT / None | ENHANCEMENT / `"身法"` | `movement:flash_step` typed effect, PASSIVE, movement-gated-exit behavior |
| `flee` | MOVEMENT / None (registered by `world/rules/disengage.py`) | MARTIAL_ARTS / None | disengage action, `INNATE_SKILL_KEYS` unconditional ownership; category kwarg still declared at flee's own construction site (requirement kept, value re-pinned) |
| `elf_longevity` | INNATE_GIFT / None | ENHANCEMENT / `"天賦"` | inert `passive_trait:elf_longevity` flavor effect, PASSIVE |
| `reincarnation_boon_elosia` | INNATE_GIFT / None | ENHANCEMENT / `"天賦"` | `growth_rate:practice:100` |
| `reincarnation_boon_yuka` | INNATE_GIFT / None | ENHANCEMENT / `"天賦"` | `combat_prediction:武感` + `skill_owned: reincarnation_boon_yuka` row in `combat_modifiers.yaml` |

Display-tag semantics: the two retired categories survive only as display-level groups inside the acquired-passives bucket. `"身法"` / `"天賦"` are chosen because both presenters (`combat_view._element_label`-style group labeling and `status_query._group_label`) already render a non-elemental `group` verbatim as the sub-group label, and the client validator treats group keys as free strings (sexual_act already ships CJK group keys). Untagged enhancement members keep `group=None`. `flee`→`MARTIAL_ARTS` pairs it with its `INNATE_SKILL_KEYS` sibling `basic_attack`; the alternative (`UTILITY`) was rejected — UTILITY is the narrative 雜學秘術 譜, and flee is an innate combat action, not a utility lineage node.

`Kind`, `cost`, `effects`, `element`, `target_spec`, `faction_constraint`, `usable_out_of_combat` of every row above are byte-identical before/after (the `classifying-a-skill-changes-no-other-field` requirement governs and stays).

## D3. Group-rule change in `skill-category-registry`

The requirement "elemental_magic and sexual_act members declare a non-null group; every other category's members declare a null group" becomes a closed per-category group vocabulary:

- `ELEMENTAL_MAGIC`: non-null group == own element key (unchanged)
- `SEXUAL_ACT`: non-null non-empty group (unchanged)
- `ENHANCEMENT`: `None` | `"天賦"` | `"身法"` (new tag vocabulary; exactly the re-homed keys use the tags)
- `MARTIAL_ARTS`, `DIVINE_MYSTERY`, `UTILITY`: `None` (unchanged)

Requirement renames change canonical IDs (slugs derive from titles); the delta therefore renames exactly these two requirements and re-annotates the tests that cite them:

| old canonical ID | new canonical ID |
|---|---|
| `skill-category-registry::skillcategory-enumerates-exactly-eight-presentation-categories` | `skill-category-registry::skillcategory-enumerates-exactly-six-presentation-categories` |
| `skill-category-registry::skill-registry-s-entries-partition-exactly-across-the-eight-categories` | `skill-category-registry::skill-registry-s-entries-partition-exactly-across-the-six-categories` |
| `skill-category-registry::elemental-magic-and-sexual-act-members-declare-a-non-null-group-every-other-category-s-members-declare-a-null-group` | `skill-category-registry::category-group-vocabulary-is-closed-per-category` |

Unchanged-ID requirements this delta still MODIFIES (text edits, same header, scenario-name superset): `skill-category-registry::every-skilldef-declares-a-required-category-and-an-optional-group` (only to drop member names from prose where they'd go stale — keep ID), `skill-category-registry::classifying-a-skill-changes-no-other-field` (adds the Phase B sentence + the re-homed-passive scenario; header unchanged), and `universal-action-ownership::flee-declares-its-skill-category-at-its-own-construction-site` (value MOVEMENT→MARTIAL_ARTS in text; header unchanged, so canonical ID unchanged — and the scenario name "flee is classified MOVEMENT" is deliberately KEPT verbatim, because openspec validate rejects a MODIFIED block that omits an existing scenario name; the re-homed value is stated in the scenario body).

## D4. Presentation-surface changes (all contract-level, no new mechanism)

- `world/skills/registry.py`: enum loses `MOVEMENT`/`INNATE_GIFT`; 5 construction sites re-kwarg'd (`flight`, `flash_step`, 3 boons) + `flee`'s site in `world/rules/disengage.py`. Four further production-helper/test-helper construction sites reference the retired members and break at import/call time, not compile time: `world/rules/tests/test_movement.py` (`_DART_STEP`, module-level), `world/rules/tests/_combat_session_helpers.py` (`synth_innate_overlay()`'s flee row — consumed by 15+ test modules across commands/webclient/rules tests), `web/browser_support/browser_fixtures_data.py` (synth flee row grafted into browser-seed catalogs under `ELOSERN_BROWSER_SYNTH_CATALOGS=1`), `world/rules/tests/test_status_query.py` (`_ROW_REST`, module-level category tuple). All four re-kwarg to the same targets as the shipped rows (synth flee rows → `MARTIAL_ARTS`; `_DART_STEP` → `MARTIAL_ARTS`; `_ROW_REST` rows → `ENHANCEMENT` tag / `MARTIAL_ARTS`).
- `world/rules/combat_view.py` / `world/rules/status_query.py`: `CATEGORY_LABELS` drops 移動/天賦 entries; both grouping functions gain an `ENHANCEMENT` branch that emits untagged (`group=None`) rows first, then `天賦`, then `身法` sub-groups in that fixed order (deterministic, ownership-independent — same style as the ELEMENT_REGISTRY rule). `webclient-combat-menu::combat-presentation-enumerates-complete-deterministic-choices` and `webclient-exploration-menu::character-panel-skills-are-grouped-by-category-with-the-same-ordering-rule-as-the-combat-panel` (headers unchanged → IDs unchanged) carry the rule text amendment: six-member category set, enhancement sub-group order rule, and the `movement`-ordering / innate-`flee` scenarios re-pinned (flee now under `martial_arts`; acquisition-tag passives under `enhancement`).
- `web/static/webclient/js/elosern/protocol.js`: `SKILL_CATEGORY_KEYS` mirror → six keys; the category-group count bound (`skills.length > SKILL_CATEGORY_KEYS.length`) follows automatically; `CHARACTER_MAX_CATEGORY_GROUPS` shrinks 9 → 7 to mirror Python's dynamic `len(SkillCategory)+1` (upper bound stays behavior-safe; `protocol.test.js` reads the constant dynamically).
- `world/rules/progression.py`'s `ELEMENTAL_MAGIC` prefix check and `lineage_query.py`'s `CATEGORY_LABELS[skill.category]` read survive unchanged (no branch membership lost that they key off).

## D5. Doc consistency (lore authority split: node data = skill-trees/*, mechanics = index §1–4; magic-system is narrative)

- `docs/lore/magic-system.md` §2: eight-row branch table → six-row taxonomy + a sentence that 身法/天賦 are display tags inside 身心強化 and the three families' parameterization; §5 names the acquired-passives bucket; §7/§8 keep their narrative but state the display-tag relationship (mirror Phase A's "唯一權威" dedup voice; do not re-add tables).
- `docs/lore/skill-trees/index.md`: the 身法/天賦異能 rows (only in §7 非魔法分支) become tag rows under 身心強化 (pages stay as acquisition-condition authorities).
- `docs/lore/skill-trees/enhancement.md`: gains the merged acquired-passives framing (movement passives + innate traits rows in its own table format, cross-linked to movement.md/innate-gift.md which stay the per-key acquisition authorities).
- `docs/lore/skill-trees/movement.md` / `innate-gift.md`: header notes that categorization is now display-tag level, and every in-body `SkillCategory.INNATE_GIFT`/`MOVEMENT` enum-name reference (e.g. innate-gift.md's 機制備註 "SkillCategory.INNATE_GIFT 底下不應該出現…") is reworded to the retired-branch wording; their D8 PASSIVE rationale text stays.
- `docs/game/commands.md`: **no change expected** (verified: movement commands are entry/go/map commands; flight/flash_step are passive ownership waivers with no command surface; no command doc references SkillCategory). Task includes a re-verification step, not an edit.

## D6. Test plan (no data-echo tests)

Contract (presentation metadata): `world/skills/tests/test_skill_registry.py` rewrites `_CATEGORY_ORDER` (6), `_UNGROUPED_CATEGORIES` (drops INNATE_GIFT/MOVEMENT), the D4 per-category key sets (re-homed rows move into ENHANCEMENT/MARTIAL_ARTS with group tags asserted), `FleeCategoryDeclarationTests` (re-pins the two MOVEMENT assertions to `MARTIAL_ARTS`, incl. the AST source check on disengage.py), and the enum-member test. New/modified annotations use the literal canonical IDs in D3/D4, incl. `skill-category-registry::classifying-a-skill-changes-no-other-field` for the re-homed rows' unchanged-mechanics assertion. `test_spell_catalogs.py` and the `USABLE_OUT_OF_COMBAT_FALSE_KEYS` inventory need no change (verified: the wind flight row is a key/label/target/cost/effects 5-tuple with no category pin; flee's flag unchanged).

Behavior (acquisition-path passives still resolve after re-bucketing — prove existing coverage passes; annotate anything newly added):
- flight waiver: `world/rules/tests/test_movement.py::test_flight_owner_is_waived_the_wilderness_move_cost` → `movement-cost-charging::charge-movement-is-the-single-shared-movement-cost-charging-function`
- skill_owned passives (defense_instinct… reincarnation_boon_yuka incl.): existing status/combat_modifier tests → `combat-modifier-table::the-eight-previously-dead-passive-buff-combat-prediction-skills-each-grant-a-real-adjustment`
- stat_multiply PASSIVE resolution + innate traits: existing body-enhancement/passive-trait tests stay green untouched
- grouping behavior with new tags: presenter tests in `test_combat_view.py` / `test_status_query.py` / `webclient/presentation/tests/test_combat_panel.py` / `test_character_panel.py` (IDs per D4)
- managed-browser surface (runs in browser-shards CI, not in the local focused batch): `web/tests/browser/test_browser_combat.py` re-pins `_open_category(page, "movement")` navigation to the flee skill's new `martial_arts` category and the enum-order panel assertion to the six-key list.
- JS validator: `web/static/webclient/js/tests/protocol.test.js` + menu tests re-pin to six keys; `web/webclient-app/tests/preserved_contract.test.js`'s `innate_gift` category-group fixture payload re-aims at a surviving category (the client validator rejects a non-mirrored key), and `web/webclient-app` story/store fixtures naming retired keys follow.

Shard-manifest/traceability impact: none expected — no new test modules (so `.github/evennia-shards.json` / `browser-shards.json` owners unchanged) and `tools/test_data_freeze.json` needs no edit unless tasks add a file; tasks include an explicit check step.

## D7. Sizing

≤ 1 engineer-day: enum + 5 registry sites + 1 disengage site + 4 helper/test construction sites + 2 label maps + 2 grouping branches + 1 JS mirror ≈ 2.5h; test/fixture re-pinning (≈7 Python modules incl. the shared `_combat_session_helpers` overlay consumed by 15+ modules, 1 browser test file, ≈6 JS fixture/test files) ≈ 3h; docs (5 lore files, prose-only) ≈ 1.5h. The browser-suite re-pin is edit-only locally (CI owns the browser shards; no local browser run, consistent with repo convention). The spec sync is the separately-authorized archive/sync workflow (not counted here). Below the split threshold — no mechanic-boundary split needed; docs ride with code because the delta/spec/tests/docs all reference one re-homing table and splitting would only duplicate it.
