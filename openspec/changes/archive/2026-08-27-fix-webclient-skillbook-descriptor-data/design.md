## Context

`web/webclient/presentation/character.py` builds the `character` OOB panel from
`world/rules/status_query.py:build_character_read_model`, which reads `active_keys` / `passive_keys`
(bare skill keys owned by the entity) and groups them via `group_skill_keys`. `_serialize_skill_groups`
then turns each key into `{key, label}` for both actives and passives — the label comes from
`group_skill_keys`'s own category/group traversal, not from `SKILL_REGISTRY` directly, so today the
serializer never touches `SKILL_REGISTRY` for anything but the label.

`world/rules/combat_view.py`'s `_build_skills` already does the richer job for the in-combat skill list:
for each owned key it resolves `SKILL_REGISTRY[key]` and builds a `SkillDescriptorView` carrying `cost`,
`target_spec`, `element`, `enabled`/`reason_code` (combat-availability gating), `valid_target_ids`,
`shorthands` (via `preview.shorthands`, battlefield-dependent), and `freeform_scales` (via the
free-standing `_freeform_scales_for_skill(actor, skill)` helper, which needs only `actor` and `skill` —
no battlefield state).

`SkillDef` (`world/skills/registry.py`) already carries `cost: dict[str, int]`,
`target_spec: TargetSpec`, and `usable_out_of_combat: bool` for every registered skill — the character
panel's presenter simply never reads them.

`web/webclient/presentation/combat_panel.py` already validates a richer skill descriptor for the
in-combat panel: `TARGET_SPECS` (a module-level `frozenset({"none","self","single","area"})`),
`MAX_COST_KEYS`, an inline bounded cost-dict check (arbitrary identifier keys, non-negative int
amounts), and `_validate_freeform_scales(value, base_mp)` (strict-ascending, canonical-label,
scaled-mp-cost-consistent). `character.py`'s new active-row validator needs the same three checks; the
design below reuses them instead of writing a second, potentially-diverging copy.

**Every module path below was confirmed against the actual file, not assumed** — an earlier draft of
this design named `world/rules/cost_tiers.py` as the relocation target for the freeform-scale helper;
that path does not exist (the real module is `world/skills/cost_tiers.py`) and the relocation as
originally drafted would have created a circular import between `world/skills/cost_tiers.py` and
`world/rules/progression.py`. The corrected target is `world/rules/progression.py` (see Decisions).

## Goals / Non-Goals

**Goals:**
- Populate `cost`, `target_spec`, `usable_out_of_combat`, and (where eligible) `freeform_scales` on
  every **active** skill row the character panel serializes, sourced from the same `SKILL_REGISTRY`
  entry and the same `_freeform_scales_for_skill` helper `combat_view.py` already uses — no duplicated
  math, no new derivation logic.
- Keep passive rows exactly `{key, label}` — the design draft's passive tab shows no cost/target data
  either (only a static "被動" badge, which is a client-side label, not payload data), and
  `SkillDef` costs are meaningless for a skill you own passively rather than cast.
- Keep the new fields optional/omittable so a key that resolves to nothing in `SKILL_REGISTRY` (the
  "unregistered-key fallback row" `SkillBook.vue` already documents and tests) still renders — with no
  detail fields, same as today.

**Non-Goals:**
- No `shorthands` field on the character panel. `combat_view.py` derives it from `preview.shorthands`,
  which needs a live battlefield/participant roster (e.g. "who counts as `all-enemies`") that has no
  meaning outside an active combat session. Inventing a placeholder here would violate the truthful-data-
  scope rule both roadmaps set. The design draft's own example only shows a shorthand cell inside its
  combat pane, never inside `#dr-skill` — corroborating that this is a combat-only field, not a gap.
- No change to `enabled` / `reason_code` / `reason_message` / `valid_target_ids` — those are
  combat-availability gates with no meaning for "what do I own" outside combat. The character panel has
  never had a concept of a skill being "disabled," and this change does not introduce one.
- No `CHARACTER_SCHEMA_VERSION` bump. Additive optional fields on a row that already had a strict
  `_require_exact_fields` check need the check's field set widened (the new fields marked `"optional"`
  in the `conditional` dict `_require_exact_fields` already accepts, matching the pattern
  `combat_panel.py`'s `_validate_skill` uses for its own optional `freeform_scales`), not a version
  bump — no existing consumer parses this shape by a fixed field count, and 0 released users means no
  back-compat burden either way. The number stays `3` on both the Python constant and the JS mirror's
  `payload.schema_version !== 3` check — both sides are updated in this change, so there is no window
  where one side expects a version the other does not send.
- No UI redesign of `SkillBook.vue` beyond the one new OOC pill needed to prove the field renders. The
  category/group visual language (colour dots, count+chevron summaries, free-cost styling) and the
  drawer chrome (icon, close-button glyph, tabs, search icon, footer hint) are separate, independently
  schedulable changes — bundling them here would blow the one-workday budget and would tangle a
  server-adjacent data change together with a pure-CSS one.

## Decisions

- **Split the shared row validator instead of widening it in place.** `_validate_passive_row` today is
  called for both actives and passives via `_validate_character_skill_group`. Adding optional fields to
  it would let a passive row accidentally carry a `cost`/`target_spec` the presenter never populates for
  passives, silently passing validation while lying about the schema's intent. Two named validators
  (`_validate_passive_row` unchanged, new `_validate_active_skill_row`) keep the two shapes honest and
  make `_validate_character_category_group`'s caller pass which validator to use, mirroring how
  `_validate_trait_row` and `_validate_equipment_row` are already separate, purpose-named functions in
  this file.
- **Enrich in `_serialize_active_skill_groups`, not in `group_skill_keys`.** `group_skill_keys` (shared
  with `combat_view.py`, per the blast-radius list) only knows keys/labels/categories — it has no actor
  reference and is used by both presenters, so teaching it about `cost`/`freeform_scales` would leak a
  character-panel-specific concern into shared grouping code. The enrichment step stays local to
  `character.py`, looking up `SKILL_REGISTRY[key]` per row after grouping, the same layering
  `combat_view.py`'s `_build_skills` already uses (group first, enrich second).
- **Relocate `_freeform_scales_for_skill` into `world/rules/progression.py` (renamed
  `freeform_scale_entries_for`, made public), not into `world/skills/cost_tiers.py`.**
  `_freeform_scales_for_skill`'s body (`world/rules/combat_view.py:345-365`, confirmed by direct read)
  calls `is_freeform_eligible` (from `world.skills.cost_tiers`) plus `FREEFORM_CAST_SCALES`,
  `freeform_scales_for`, and `scaled_mp_cost` — all three defined in `world/rules/progression.py` and
  already imported into `combat_view.py` from there. `progression.py` itself already does
  `from world.skills.cost_tiers import spell_tier_for` (confirmed at `world/rules/progression.py:14`),
  so adding `is_freeform_eligible` to that same import line is a same-direction addition, not a new
  edge. Putting the function in `cost_tiers.py` instead — the earlier, incorrect draft of this design —
  would require `cost_tiers.py` to import `FREEFORM_CAST_SCALES`/`freeform_scales_for`/`scaled_mp_cost`
  from `progression.py`, which already imports `cost_tiers.py`: a two-module import cycle that fails at
  process-start, not at runtime. `progression.py` is the only home with no new cycle.
  `combat_view.py`'s `_build_skills` now imports `freeform_scale_entries_for` from
  `world.rules.progression` and drops its four now-unused direct imports, so there is exactly one
  implementation, not a second, divergent copy and not a private cross-module import.
- **Reuse `combat_panel.py`'s cost/target_spec/freeform_scales validators by making them public,
  instead of writing character-panel-specific copies.** `TARGET_SPECS` and `MAX_COST_KEYS` are already
  module-level public names (no underscore) in `combat_panel.py`, so `character.py` imports them
  directly. `_validate_freeform_scales` is renamed to public `validate_freeform_scales` (its one
  internal call site in `combat_panel.py`'s `_validate_skill` is updated) and imported the same way.
  Confirmed no circular-import risk: `combat_panel.py` does not import from `character.py` (only a
  comment references "the character panel" conceptually); the only file importing both is
  `web/webclient/presentation/registry.py`, which imports each independently — that is not a cycle.
  This also directly fixes a cost-validation-shape question raised during review: rather than
  independently re-describing "a bounded `{mp?, sp?}` mapping" and risking a stricter or looser rule
  than `combat_panel.py`'s actual (arbitrary-identifier-keyed) check, `character.py` now runs the exact
  same tested function, so the two presenters cannot drift.
- **The client-side JS schema mirror (`protocol.js`) is updated in the same change, not deferred.**
  `character.py`'s own module docstring states the payload shape is mirrored by
  `web/static/webclient/js/elosern/protocol.js`, and that mirror is what `web/webclient-app/lib/protocol.js`
  re-exports for the Vue store (`stores/elosern.js`'s `Protocol.createStore()`) to validate every
  incoming `character` OOB message against, `SkillBook.vue` included. Confirmed by direct read:
  `validateCharacterSkillGroup` (protocol.js) calls `validateCharacterPassiveRow` (`["key","label"]`
  only) for both `actives` and `passives`, and `requireExactFields` throws on any field outside its
  known set. Shipping only the Python change would make the live client throw on every active skill row
  — a regression, not a fix. `validateCharacterActiveSkillRow` mirrors the new Python validator field-
  for-field (same optional set: `cost`/`target_spec`/`usable_out_of_combat`/`freeform_scales`, same
  bounds), and `validateCharacterSkillGroup`/`validateCharacterCategoryGroup` take an explicit row
  validator so the `actives` and `passives` call sites (`validateCharacterPanel`'s two
  `payload.actives.forEach(...)` / `payload.passives.forEach(...)` lines) diverge the same way the
  Python `validate_character`'s two call sites do.
- **The second `SKILL_REGISTRY.get(key)` lookup in the new serialization step is an accepted, bounded
  duplication, not a refactor of `group_skill_keys`.** `world/rules/status_query.py:507`'s
  `group_skill_keys` (shared by both `character.py` and `combat_view.py`) already resolves
  `SKILL_REGISTRY.get(key)` once to build each row's label. Threading its resolved `SkillDef` through to
  the character-panel enrichment step would avoid a second lookup, but `group_skill_keys` is shared
  grouping code with no actor reference and no character-panel-specific concern today (see the
  `_serialize_active_skill_groups` decision above) — changing its return shape to carry a `SkillDef`
  reference risks a wider, unrelated diff across both presenters for a saving that is bounded by
  `MAX_ACTIVE_ROWS = 32` lookups per panel build (a dict `.get()`, not a query). This change accepts the
  duplication rather than touching shared grouping code.
- **`usable_out_of_combat` is new to every presenter, not retrofitted into `combat_view.py` too.**
  `SkillDetailPane.vue`'s own comment records a prior, deliberate decision (H3 design D14) not to invent
  a `戰鬥外` badge in the combat detail pane because no presenter served the flag. That decision is
  about the *combat* pane specifically; it does not forbid a different presenter — the character
  panel — from serving the flag for the first time. Retrofitting `combat_view.py` and
  `SkillDetailPane.vue` to also show it is out of scope here (the user's own scoping keeps this change
  to "the skill-book," not the combat menu) and is a natural, separately-sized follow-up if wanted.

## Risks / Trade-offs

- **A row whose registry lookup fails silently loses its detail fields.** This is the existing,
  documented "unregistered-key fallback row" behaviour (`SkillBook.vue`'s own comment already describes
  it and `web/webclient-app/tests/data/skill_book.test.js` already covers `legacy_stance`); this change
  does not alter that contract, it only adds more fields that can be present or absent the same way.
- **Renaming/relocating a function used by the combat view's test suite risks an import-path miss.** →
  `world/rules/combat_view.py:345`'s body was read directly during design: `_freeform_scales_for_skill`
  reads only `actor` (traits/element-mastery) and `skill` (cost/element), never `battlefield` or
  `record`, so the move to `cost_tiers.py` is a pure relocation. Every existing call site and test
  import of the old private name is updated in the same commit (`grep -rn
  _freeform_scales_for_skill` before removing it).
- **Widening `_require_exact_fields`'s optional-field set for the active row could mask a genuinely
  malformed payload from a future refactor.** → Every optional field keeps its own type/shape check
  when present (bounded `cost` mapping, enum `target_spec`, bool `usable_out_of_combat`, bounded
  `freeform_scales` list), so a malformed value still fails closed; only its *presence* is optional.
- **Shipping the Python presenter change without the JS mirror update breaks the live panel.** → See the
  "client-side JS schema mirror" decision above; `tasks.md` §4a makes the `protocol.js` split an
  explicit, required step in the same change, and §6 adds a test that runs a Python-serialized active
  row through the JS validator (not just through the Python one) so this class of drift cannot ship
  silently again.
- **A 32-row active payload with cost + target_spec + usable_out_of_combat + a full 5-entry
  `freeform_scales` on every row could approach `MAX_CANONICAL_JSON_BYTES` (65,536).** → `tasks.md` §6
  adds an explicit worst-case-envelope test instead of relying on a manual estimate; if it turns out to
  be tight, `freeform_scales` — the largest addition per row — is the first field to bound further
  (e.g. cap to the actor's currently-unlocked scale count, which `freeform_scale_entries_for` already
  computes, so no new size-reduction logic would be needed).

## Migration Plan

Not applicable — 0 released users, no persisted data shape to migrate, and the schema change is
additive/optional so no rollback coordination is needed beyond reverting the commit.

## Open Questions

None outstanding.
