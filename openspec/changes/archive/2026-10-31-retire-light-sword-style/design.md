# Design

## Context

See `proposal.md` for motivation. This is a clean pre-release catalog cutover, not a rules change. The registry is now split into `world/skills/registry/data_*.py`; do not use older archived plans' flat `registry.py` paths. The source architecture remains `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`, including read-only lore/skills and deterministic activation writers.

The existing `basic_swordplay` declaration is in `world/skills/registry/data_martial_sword.py:40-52`. It is ACTIVE, SINGLE, SP 8, elementless, `damage:none:physical`, coefficient 1.0, with no prerequisites. Its consumer `flowing_strikes` requires proficiency 3. These are observations for understanding the cutover, not a second numerical approval table or instructions to change that row. Granting root ownership lets the two presets practice from the beginning; it does not automatically award later-node ownership.

## Goals / Non-Goals

**Goals:** Delete the obsolete skill and its current references, reuse the existing root in both human sword cards, and keep generic resolution/activation/lineage contracts intact.

**Non-Goals:** No signature, schema, resolver, handler, prerequisite, balance, or persistence changes. No alias, migration, deprecation mechanism, additional skill, or compatibility layer. Do not edit `data_martial_sword.py`, any of the 14 tree-node declarations, `basic_attack`, or `dual_wield_style`. In `data_shadow_martial.py`, delete the obsolete row and leave every surviving row byte-for-byte unchanged. Do not edit NPC profiles, faction or item data, or NPC 「劍聖劍術」 wording.

## Decisions

### 1. Fixed edit manifest and data contract

The reference search covered the retired key, its hyphenated traceability slug, 光劍架式, and 聖騎士劍術 across code, tests, tools, current docs, main specs, and active changes. It also searched English and Chinese single-sword exclusivity variants. The following is the complete current hit disposition. Line numbers are discovery anchors, not patch offsets.

| File / symbol or section | Required edit | Task |
| --- | --- | --- |
| `world/skills/registry/data_shadow_martial.py`, `ROWS`, lines 43-55 | Delete the entire `_skill("light_sword_style", ...)` entry, including its comma. Preserve sibling declarations and imports still used elsewhere. | 1.1 |
| `world/skills/narration/data_martial.py`, `ROWS`, lines 87-93 | Delete the complete `NarrationRow` for that key. Do not move its prose to the sword root. | 1.1 |
| `world/lore/player_presets/data_pack_cards.py`, `ROWS["elysa_snow"]`, line 29 | Replace exactly with `active_skills=("basic_swordplay",),`. Leave passive skills, proficiency, stats, items, identity and prose unchanged. | 1.1 |
| `world/lore/player_presets/data_story_cards.py`, `ROWS["lidzia_rosenthal"]`, line 32 | Apply the same active tuple replacement and preserve every other field. | 1.1 |
| `world/imports/examples/example_character.json`, `skills`, line 23 | Replace the array with `"skills": ["basic_swordplay"]`. Preserve all other JSON fields. | 1.2 |
| `world/skills/tests/test_skill_registry/test_content_completion.py`, `SkillContentCompletionTests.test_light_sword_style_declares_the_damage_convention`, lines 57-65 | Delete the entire test, explanatory comment and retired decorator. Do not retarget its literal damage assertion to another skill. Keep the file and all other tests. | 1.1 |
| `world/skills/tests/test_skill_registry/test_category_classification.py`, `SkillCategoryClassificationTests.test_per_category_key_sets_match_the_d4_classification_table`, line 195 | Remove this key from the existing `MARTIAL_ARTS` expected set. No other category/member changes. | 1.1 |
| `world/lore/tests/test_player_presets.py`, `PlayerPresetTests.test_kit_validation_rejects_unknown_kind_mismatch_and_divine_gate`, line 237 | Use `make(passive_skills=("basic_swordplay",))`, still expecting `"classifies it as"`. Retain the unknown-key and other kind/divine cases. | 1.1 |
| `world/rules/progression/_practice.py`, `_is_elemental_magic(skill: SkillDef) -> bool`, lines 22-23 | Change the worked example to `shadow_slash` carrying `element == dark` and PHYSICAL damage. No executable changes. | 2.1 |
| `docs/lore/magic-system.md`, lines 95, 98, 170 | Delete one bullet and replace the two separate-paladin-art claims per the lore review contract below. Preserve surrounding factions and institutions. | 2.2 |
| `docs/development/adding-player-presets.md`, example line 81 | Use `active_skills=("basic_swordplay",),`. | 1.2 |
| `docs/development/adding-spells.md`, catalog-test guidance line 265 | Remove the light-element obsolete example. Use the surviving `shadow_slash` dark physical skill as the illustrative non-spell ACTIVE example. Do not classify `basic_swordplay` as light magic. | 1.2 |
| `docs/superpowers/specs/2026-08-12-skill-system-redesign-design.md`, §3.3 lines 93-94 and SP calibration lines 411-412 | Use `shadow_slash` as the SINGLE cast-time attack example. Delete the obsolete-key/SP-6 calibration operand, retaining the stated cost bands and other operands unchanged. These edits amend current technical documentation, not OpenSpec history. | 2.2 |
| `docs/superpowers/specs/2026-08-15-skill-category-system-design.md`, D-2 line 53, D-4 line 55, martial census line 69 | D-2 uses `shadow_slash` as the element-bearing PHYSICAL counterexample; D-4 states that `shadow_slash` declares `martial_arts` despite its dark element, which does not assign `elemental_magic`. Replace the martial row's stale count/member snapshot with a reference to the existing current category-census test; qualify the remaining numerical snapshots as historical and replace the obsolete total/partition claim at lines 77-78 with that live-census reference. Do not create a second 14-node member list. | 2.2 |
| `openspec/specs/skill-registry/spec.md`, lines 391-398 | Remove the requirement via this change's REMOVED delta at the later authorized sync/archive phase. Do not edit the main spec during proposal or apply. | 1.1, workflow follow-up |
| `openspec/specs/skill-lineage/spec.md`, scenario “The affinity factor is magic-damage-scoped”, lines 210-214 | This change's MODIFIED delta changes `light_sword_style` to `shadow_slash`. Keep the complete requirement, exact existing heading (including `accruses`), formula and all 17 scenarios. | 2.1, workflow follow-up |

No new module, public symbol, data field, API, or runtime caller is required.

### 2. Traceability cutover matrix

Canonical IDs below were obtained with `uv run --locked python -m tools.spec_traceability list --json-output <scratch-path>` and existing annotations. Do not correct the existing `accruses` spelling during this unrelated cutover.

| Assertion / role | Existing canonical annotation | Disposition and reason |
| --- | --- | --- |
| Deleted `SkillContentCompletionTests.test_light_sword_style_declares_the_damage_convention`, registry-contract | `@covers_requirement("skill-registry::light-sword-style-deals-damage-via-the-standard-damage-convention")` | Remove with its test. No annotation is moved to a surviving requirement because the test solely pins a deleted declaration. |
| Existing category-census test, registry-contract | `@covers_requirement("skill-category-registry::skill-registry-s-entries-partition-exactly-across-the-seven-categories")` | Retain unchanged while shrinking the existing expected set. |
| Retargeted preset kind-error case, registry-contract | `@covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-skill-kit")` | Retain unchanged; the surviving ACTIVE in `passive_skills` must still reach the kind-mismatch branch. |
| `world/rules/tests/test_skill_lineage.py`, `PracticeFormulaTests.test_physical_skill_takes_neutral_affinity_even_for_element_affinity`, synthetic mechanism | `@covers_requirement("skill-lineage::successful-active-resolution-accruses-lineage-practice-xp")` | Retain unchanged; its synthetic physical skill already establishes neutral affinity. No shipped-row or prose pin is added. Other annotations on this unchanged requirement stay unchanged too. |
| `world/rules/tests/test_character_creation/test_preset_activation_kit.py`, kit grant/usability tests, synthetic mechanism | `@covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-skill-kit")` | Retain unchanged; declared kits already flow through activation and the shared usability predicate. |

`tools/spec_traceability.py` is unchanged. No replacement canonical ID is needed and no tool allowlist or waiver is introduced. `tools/test_data_freeze.json` retains the entries for all three edited test files, with `skill registry content contract` for the two registry slices and `lore registry content contract` for the preset suite. `tools/test_data_lint_seed.json` has the same entries/reasons and remains unchanged. Retaining the completion file is required because its remaining tests still inspect shipped content. Test paths do not move, so `.github/evennia-shards.json` remains unchanged.

The local traceability checker indexes main specs, not delta specs. Once the deleted test is removed but before authorized spec synchronization, the old main requirement is expected to appear uncovered. The implementation's meaningful pre-sync acceptance uses an equivalent temporary spec tree with both deltas merged and the updated test sources, following `docs/development/spec-test-traceability.md`. No temporary tree is a Git branch or worktree. Run `uv run --locked python -m tools.spec_traceability --repo-root <equivalent-tree> check` there and require zero uncovered requirements/errors. After later authorized synchronization, run the exact root command `uv run --locked python -m tools.spec_traceability check` and require zero uncovered requirements/errors. Never retain the obsolete test or weaken the gate to manufacture a pre-sync pass. The proposal turn does not perform any of these implementation checks or synchronize specs.

### 3. Unaffected references and contracts

There are no other direct retired-key callers, preset fixtures, current spec mentions, or data-contract references outside the manifest. Searches also covered active wilderness changes; none references the retirement target. The following indirect consumers need no source edits.

- `world/skills/tests/test_narration_catalog.py` validates current catalog references and authored-family shape. Deleting both the skill and narration row preserves their join; do not add an absence/copy pin.
- `world/imports/tests/helpers.py` reads the changed example. `test_reference_example.py` validates it without pinning its skill identity. `test_age_bounds.py`, `test_batch_all_or_nothing.py`, `test_capability_imports.py`, `test_degraded_banner.py`, `test_import_portrait_seam.py`, `test_loader_trait_values.py`, `test_npc_persona_cards.py`, `test_record_dispatch.py`, `test_schema.py`, and `test_validation_semantics.py` derive records from that helper and contain no retired-key literal. Their schema/identity/trait contracts do not require the deleted skill. Run the small `world.imports.tests` package as a regression boundary; do not rewrite their fixtures.
- The preset matching-kind sweep and catalog-order test in `world/lore/tests/test_player_presets.py` remain generic or concern the unchanged eight card identities. No new exact-kit approval test is added.
- `world/lore/tests/test_starting_kits.py` concerns equipment/subrace kits, not active skills. `tests/test_creation_parity_contract.py` concerns creation schema/UI bounds and persona summaries; neither references the retired key.
- `world/rules/tests/test_skill_lineage.py`, `world/skills/tests/test_elementless_damage.py`, and `world/rules/tests/test_character_creation/test_preset_activation_kit.py` already provide synthetic affinity, elementless practice, and kit/usability evidence. Preserve those tests and decorators.
- `docs/lore/skill-trees/martial-arts.md` and `docs/lore/skill-trees/cross-lineage-unlock.md` describe the existing sword/shadow routes and sword-route mastery; neither implies a separate paladin art or names the retired key. Their unrelated canopy/mastery descriptions are not the retired single-sword exclusivity narrative and are outside this no-tree-change scope.
- `docs/lore/overview.md`, `docs/lore/items.md`, and `docs/superpowers/specs/2026-08-29-equipment-combat-effects-design.md` mention the 聖騎士團 institution or equipment without asserting a separate sword system. `world/lore/npc_profiles/altoria_guild.py` uses 「劍聖劍術」, a different concept. Leave all unchanged.

Archived retired-key hits are preserved in these directories under `openspec/changes/archive/` (brace lists name exact files).

| Archive directory | Files containing the target |
| --- | --- |
| `2026-07-31-skills-equipment` | `design.md`, `tasks.md` |
| `2026-08-12-fix-friendly-fire-reachability` | `tasks.md` |
| `2026-08-13-preset-skill-kits` | `design.md` |
| `2026-08-13-skill-content-completion` | `design.md` |
| `2026-08-13-weapon-style-stance-split` | `design.md`, `proposal.md`, `tasks.md`, `specs/skill-registry/spec.md` |
| `2026-08-14-fix-dual-wield-style-stance` | `design.md` |
| `2026-08-15-skill-category-registry` | `design.md`, `tasks.md` |
| `2026-09-15-light-spell-catalog` | `design.md` |
| `2026-09-19-elementless-damage-effect` | `design.md`, `proposal.md`, `tasks.md`, `specs/skill-lineage/spec.md` |
| `2026-09-19-enhancement-catalog-alignment` | `design.md`, `specs/skill-lineage/spec.md` |
| `2026-09-19-martial-arts-catalog` | `design.md`, `proposal.md` |

The archived preset design at lines 59-61 contains the single-sword exclusivity narrative. `AGENTS.md:271-273` treats these archives as historical evidence; no archive edit is planned. A scan including ignored files also found two historical `action_commit` entries in `server/logs/server.log:1628,1631`. Do not rewrite operator logs or saved state. This proposal's own target names are planning evidence, not live consumers. The final no-reference sweep excludes archives, this change's artifacts, and local generated/ignored state; the two main-spec hits disappear at authorized synchronization.

### 4. Lore review contract

Use this section of `design.md` as the human review document, not a new executable requirement.

- Delete the entire 光劍架式 bullet from `docs/lore/magic-system.md` §6. Do not move its light-magic lore into `basic_swordplay` or another skill.
- In the traditions paragraph, replace the Kingdom clause with `王國的聖騎士團沿用劍術系統，重視騎士的劍術訓練`. Preserve the surrounding Empire, beastfolk, and dark-elf clauses.
- In the institution bullet, preserve its secular command, honours and investiture account. Replace its final training sentence with `團內沿用劍術系統訓練劍技，並設有光屬性魔法的專門指南。` This keeps existing light-magic education separate from sword-tree identity.
- Remove every current claim of a separate 「聖騎士劍術」 system. Introduce no positive or negative single-sword uniqueness statement, including in comments and updated technical examples. Review meaning as well as literal spelling.

### 5. Requirement shape and verification boundary

There are zero ADDED requirements. REMOVED retires a content-echo requirement instead of transplanting its damage-string pin. MODIFIED retains its short existing mechanism body (under 500 characters), exact identity and all scenarios, changing the obsolete example only. No new requirement pins catalog membership, preset copy, lore wording, or counts. Existing synthetic mechanism tests and existing registered data contracts are sufficient; no additional freeze entry is justified.

The planned checks are the focused package labels in `tasks.md`, `tools.test_data_lint check`, `tools.spec_traceability check` against the correct spec view, and `openspec validate retire-light-sword-style --strict`. The aggregate `tools.contract_gate` runs from the repository root after later authorized synchronization; it includes the root traceability gate and cannot pass against the intentionally stale pre-sync main contract. No full browser suite, content snapshot, new skill test, or balance benchmark is required.

## Risks / Trade-offs

The starter attack will use the existing root's authored SP cost and physical effect instead of the deleted light attack. Do not compensate by editing the root or preset stats. Saved development records naming the old key will fail existing unknown-skill validation; there is deliberately no conversion. Later nodes still require their existing ownership acquisition and practice thresholds.

The broad doc search found two additional technical design files beyond the initially supplied list; omitting them would leave current references behind. Historical archives are deliberately retained and disclosed. The traceability check must use the post-delta contract view before sync; treating the unchanged main-spec view as the new contract would report the intentionally retired requirement.

## Dependency / Conflict Matrix

| Change | Depends on | Runtime/code conflicts | Spec conflicts |
| --- | --- | --- | --- |
| `retire-light-sword-style` | None; the sword root and martial trees are already present | The 14 current-file edits in decision 1 are one atomic cutover; any concurrent skill registry, narration, preset, or listed-doc edit needs serialization | `skill-registry` removed requirement; `skill-lineage` named requirement example |
| Existing `wilderness-camping` and `wilderness-travel-{route,planning,window,leg,log,walking}-ui` proposals | No dependency in either direction | No shared retirement-target edits discovered | No shared capabilities with this change |

One change is sufficient; no Batch dependency metadata is needed for a single-change delivery. There are no unresolved design questions.
