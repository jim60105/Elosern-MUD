## Why

`docs/design/elosern-redesign/index.html`'s `#dr-skill` drawer shows every active skill with its MP/SP
cost, a `combat`-labelled pill on skills also castable outside combat, and (for scaling spells) the
freeform power-scale costs — because the design's skill descriptors are backed by real registry data
(`world/skills/registry.py`'s `SkillDef.cost` / `SkillDef.target_spec` / `SkillDef.usable_out_of_combat`
and `world/rules/cost_tiers.py`'s freeform-scale math). The shipped client cannot show any of this: the
character panel's presenter (`web/webclient/presentation/character.py:350-369`,
`_serialize_skill_groups`) emits `{key, label}` for **every** active and passive skill row — no `cost`,
no `target_spec`, no `usable_out_of_combat`, no `freeform_scales` — even though `SkillBook.vue` and the
`webclient-component-showcase` spec's "truthful, non-color-only state" requirement already describe
exactly this shape as the display subset of the `context_actions` v5 skill descriptor, "rendered only
when the character's skill data provides them." The Storybook fixture
(`web/webclient-app/stories/fixtures.js`'s `SKILLS_SLICE_SAMPLE`) invents this richer shape for
showcase purposes, which is precisely the mismatch the offline showcase must never hide: the live
client has never sent it, so the live 技能書 renders as bare skill names with none of the cost/target/
combat-availability detail the design and the spec both call for.

This gap is presentation-layer plumbing, not new game mechanics: every field the design needs already
exists on `SkillDef` and is already computed for the in-combat skill list
(`world/rules/combat_view.py`'s `_build_skills` / `_freeform_scales_for_skill`) and validated for the
in-combat panel (`web/webclient/presentation/combat_panel.py`'s `TARGET_SPECS`, cost-dict check, and
`_validate_freeform_scales`). Wiring the same, already-computed and already-tested logic into the
out-of-combat character panel — on both the Python presenter and its client-side JS schema mirror — is
what closes the gap; it invents nothing.

## What Changes

- `web/webclient/presentation/character.py`: replace the shared `_validate_passive_row` use for BOTH
  actives and passives with two distinct row validators — `_validate_passive_row` stays `{key, label}`
  only (unchanged), and a new `_validate_active_skill_row` accepts `key`, `label`, and three
  **optional, omittable** fields: `cost` (a bounded resource-key mapping — reusing
  `combat_panel.py`'s already-tested cost-dict check, made public, instead of a second copy), `target_spec`
  (`combat_panel.py`'s existing public `TARGET_SPECS` enum, imported rather than redeclared), and
  `usable_out_of_combat` (bool, new). A fourth optional field, `freeform_scales` (a bounded list of
  `{scale, label, mp_cost}`, validated by `combat_panel.py`'s `_validate_freeform_scales` — renamed
  public and imported, not reimplemented), is populated only for skills
  `world/skills/cost_tiers.py:is_freeform_eligible` accepts.
- `_serialize_skill_groups` (renamed `_serialize_active_skill_groups` for actives,
  `_serialize_passive_skill_groups` for passives — a passive row's shape does not change) looks each
  active key up in `SKILL_REGISTRY` and, when found, attaches `cost`, `target_spec`,
  `usable_out_of_combat`, and (via a new public `freeform_scale_entries_for(actor, skill)` — the
  existing private `_freeform_scales_for_skill` relocated from `world/rules/combat_view.py` into
  `world/rules/progression.py`, which already houses `FREEFORM_CAST_SCALES`/`freeform_scales_for`/
  `scaled_mp_cost` and already imports `is_freeform_eligible` from `world/skills/cost_tiers.py`, so the
  move adds no new import edge) `freeform_scales`. An owned key absent from the registry (the
  "unregistered-key fallback row" `SkillBook.vue` already documents) renders with no detail fields,
  same as today — nothing is invented for a row the registry cannot resolve.
- **The client-side JS schema mirror is updated in the same change.**
  `web/static/webclient/js/elosern/protocol.js`'s `validateCharacterPassiveRow` /
  `validateCharacterSkillGroup` / `validateCharacterCategoryGroup` today validate BOTH `actives` and
  `passives` identically (`{key, label}` only) and reject any unknown field — so shipping the Python
  change alone would make the live client throw on every active skill row the moment it parses a
  `character` OOB message, breaking the panel outright. This proposal adds a
  `validateCharacterActiveSkillRow` mirroring the new Python validator (same optional fields, same
  bounds) and threads an active/passive choice through `validateCharacterSkillGroup` /
  `validateCharacterCategoryGroup`, exactly as the Python-side split does.
- `shorthands` is deliberately **not** added to the character panel: `combat_view.py` computes it from
  `preview.shorthands`, which needs a live battlefield/participant roster that does not exist outside
  combat, so it cannot be honestly derived here. The design's `火風暴 範圍代號 all-enemies／all` example
  only appears inside its combat pane, not `#dr-skill` — the drawer's own example rows never render a
  shorthand cell, confirming the two surfaces already diverge on this field.
- `SkillBook.vue` renders a small `combat` pill next to a skill's name when `usable_out_of_combat` is
  `true` on that row (data-testid `skill-book__ooc`), reusing the design's literal English-word label so
  the new field has a visible, testable consumer in the same change that adds it.
- `web/webclient-app/stories/fixtures.js`'s `SKILLS_SLICE_SAMPLE` gains an explicit
  `usable_out_of_combat: true` row (on top of its existing cost/target/freeform_scales coverage) so the
  showcase proves the new field's rendering offline before any server wiring is trusted.
- No change to `CHARACTER_SCHEMA_VERSION` (stays `3`): the new fields are additive and optional on the
  active-row shape, and passives are untouched, so no existing consumer's parsing breaks.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

- `webclient-component-showcase`: the "status, character, and skill surfaces present truthful,
  non-color-only state" requirement is amended so the active-skill descriptor subset explicitly
  includes `usable_out_of_combat`, and so the requirement records that the character panel's presenter
  is now the one populating this data (today the requirement describes the shape but the presenter
  never filled it in for any row).

## Impact

- `world/rules/progression.py`: gains public `freeform_scale_entries_for(actor, skill)` (the relocated,
  renamed `_freeform_scales_for_skill`) and an added `is_freeform_eligible` import alongside its
  existing `spell_tier_for` import from `world/skills/cost_tiers.py`.
- `world/rules/combat_view.py`: `_build_skills` imports and calls `freeform_scale_entries_for` from
  `world.rules.progression` instead of defining it locally; its now-unused direct imports of
  `FREEFORM_CAST_SCALES`/`freeform_scales_for`/`scaled_mp_cost`/`is_freeform_eligible` are removed (no
  other call site in this file uses them).
- `web/webclient/presentation/combat_panel.py`: `TARGET_SPECS` and `MAX_COST_KEYS` (already
  module-level public constants) and `_validate_freeform_scales` (renamed public
  `validate_freeform_scales`, no behavior change) become the shared implementation `character.py`
  imports; `_validate_skill`'s call site is updated to the new name.
- `web/webclient/presentation/character.py`: new `_validate_active_skill_row` (built from the imported
  `combat_panel.py` primitives, plus a new `usable_out_of_combat` bool check); `_serialize_skill_groups`
  split into `_serialize_active_skill_groups` (registry-enriched, actor-aware) and
  `_serialize_passive_skill_groups` (unchanged `{key, label}`); `character_presenter` passes `actor`
  through to the new serialization step (it already has `actor` in scope).
- `web/static/webclient/js/elosern/protocol.js`: new `validateCharacterActiveSkillRow`;
  `validateCharacterSkillGroup` / `validateCharacterCategoryGroup` split (or parameterized) to validate
  `actives` rows against the new function and `passives` rows against the unchanged
  `validateCharacterPassiveRow`, mirroring the Python split exactly.
- `web/webclient-app/components/SkillBook.vue`: one new conditional `combat` pill span keyed off
  `row.usable_out_of_combat`; the file's own header comment (which already claims this data shape) is
  corrected to state it is now actually populated for actives.
- `web/webclient-app/stories/fixtures.js`, `web/webclient-app/stories/Data/SkillBook.stories.js`: fixture
  gains an OOC-flagged row; no new story variant needed (`ActiveTab` already renders it).
- Tests: `web/webclient/presentation/tests/test_character_panel.py` (new active-row schema, registry
  enrichment, unregistered-key fallback still renders bare, worst-case 32-row envelope-size check);
  `web/webclient-app/tests/data/skill_book.test.js` (OOC pill renders/hides correctly); a JS protocol
  test exercising `validateCharacterActiveSkillRow` against both a Python-shaped enriched row and a bare
  `{key,label}` row; `world/rules/tests/` coverage for the relocated `freeform_scale_entries_for`
  (import-path + behavior parity with the pre-move function). No browser/Playwright change — no
  `data-testid` on an existing preserved hook moves.
- Player-facing command surface is unchanged (no command added, removed, renamed, or re-aliased), so
  `docs/game/commands.md` / `docs/game/command-reference.md` and `tests/test_command_docs.py` need no
  update.
- Spec-test traceability: the amended requirement keeps a substantively matching test
  (`test_character_panel.py`'s new active-row case); `tools.spec_traceability check` must stay green.
