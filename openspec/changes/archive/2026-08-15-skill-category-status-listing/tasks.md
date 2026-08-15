## 1. status_query.py: corrected reads and grouping helper

- [x] 1.1 Implement `_split_active_passive_keys(entity) -> tuple[tuple[str, ...], tuple[str, ...]]`
      per design.md D-3: iterate `entity.skills.owned_keys()` with a `seen: set[str]` dedup guard
      (`owned_keys()` does **not** de-duplicate — verified against `world/skills/handler.py`, do not
      assume otherwise); for each key, look up `SKILL_REGISTRY.get(key)` (never `SKILL_REGISTRY[key]`
      — see task 1.1a for why); route by `skill.kind` when found, and when not found, route by
      whether the key appears in `entity.db.skills["active"]` (falling back to the passive bucket
      otherwise), matching the pre-existing raw-list membership rather than raising.
- [x] 1.1a Add a regression test proving `_split_active_passive_keys()` does not raise for an entity
      whose `entity.db.skills = {"active": [], "passive": ["no_such_skill"]}` — the exact scenario
      `web/webclient/presentation/tests/test_character_panel.py::
      test_unknown_item_and_skill_degrade_to_their_keys` already constructs and currently passes
      against the pre-change code; this task exists because a direct `SKILL_REGISTRY[key]` index
      would regress that passing test with an unhandled `KeyError`.
- [x] 1.2 Add `active_keys: tuple[str, ...]` and rewrite `passive_keys` on `CharacterReadModel`, both
      populated from `_split_active_passive_keys()` in `build_character_read_model()`.
- [x] 1.3 Add `CharacterSkillRow(key: str, label: str)`, `CharacterSkillGroupView(group: str | None,
      label: str | None, skills: tuple[CharacterSkillRow, ...])`, and
      `CharacterCategoryGroupView(category: str, label: str, groups: tuple[CharacterSkillGroupView, ...])`
      frozen dataclasses.
- [x] 1.4 Build a category-key-to-Traditional-Chinese-label mapping in `status_query.py`
      (`元素魔法`/`武技`/`強化`/`天賦`/`移動`/`神之秘法`/`特殊`/`性愛行為`, plus `未知技能` for the
      synthetic fallback bucket in task 1.5). This is a deliberately independent copy of the
      equivalent mapping `skill-category-combat-panel`'s `combat_view.py` task 1.3 builds — see
      design.md D-2's note on this label-text duplication risk, tracked alongside the existing
      ordering-duplication risk in the Open Questions cross-reference.
- [x] 1.5 Implement `group_skill_keys(keys: Sequence[str]) -> tuple[CharacterCategoryGroupView, ...]`:
      look up each key via `SKILL_REGISTRY.get(key)`, never a direct index; iterate `SkillCategory` in
      declaration order and, for each category with at least one matching key, build sub-groups
      following the same rule as `combat_view.group_skill_views()` (elemental_magic iterates
      `ELEMENT_REGISTRY` order per element; sexual_act groups by first-seen `group` among the given
      keys; every other category emits exactly one `group=None` sub-group); omit any category or
      sub-group with zero matching keys; append one synthetic `category="unknown"`, `label="未知技能"`
      group *after* every real category (never interleaved, since `"unknown"` has no position in
      `SkillCategory`'s declaration order) containing exactly one `group=None` sub-group listing every
      key absent from `SKILL_REGISTRY`, each row's `label` equal to its own `key` (mirroring
      `character.py`'s existing `_skill_label()` fallback).
- [x] 1.6 Export `active_keys`/`passive_keys` fields, `CharacterSkillRow`, `CharacterSkillGroupView`,
      `CharacterCategoryGroupView`, `group_skill_keys` from `status_query.py`'s public surface.

## 2. character.py presenter: schema version 3

- [x] 2.1 Bump `CHARACTER_SCHEMA_VERSION` to `3` in `web/webclient/presentation/character.py`.
- [x] 2.2 Add `_validate_character_skill_group()` (validates a `{group, label, skills}` object with
      `{key, label}` rows reusing the existing `_validate_passive_row()` shape) and
      `_validate_character_category_group()` to `character.py`.
- [x] 2.3 Update `validate_character()`'s exact-fields set to add `actives` alongside `passives`, both
      validated as arrays of category groups via `_validate_character_category_group()`.
- [x] 2.4 Update `_serialize()` to call `status_query.group_skill_keys(model.active_keys)` and
      `group_skill_keys(model.passive_keys)` independently, serializing each into the `actives` and
      `passives` payload sections.
- [x] 2.5 Add an explicit flattened-count check to `validate_character()`: the total count of skill
      rows across every category and sub-group, flattened, for `passives` SHALL NOT exceed
      `MAX_PASSIVE_ROWS`, and for `actives` SHALL NOT exceed a new `MAX_ACTIVE_ROWS` (same numeric
      value, `32`, tracked as an independent constant since active and passive counts are
      independent quantities). This does **not** carry over automatically from the v2 flat-array
      check (`len(passives) > MAX_PASSIVE_ROWS`): applying the same check to the new top-level
      `passives` array would instead bound the *category-group* count (at most `len(SkillCategory)`,
      currently 8), a materially weaker check — the same gap identified and fixed in
      `skill-category-combat-panel`'s `MAX_SKILLS` handling (design.md D-5 there), reproduced here
      deliberately rather than left implicit a second time.

## 3. Client-side parity and production menu rendering

- [x] 3.1 Update `web/static/webclient/js/elosern/protocol.js`'s character-panel validator for the
      v3 nested shape and the new `actives` field.
- [x] 3.2 Update the dual-direction parity test asserting the Python and JS validators agree on the
      v3 schema.
- [x] 3.3 Update `web/static/webclient/js/elosern/character_menu.js`'s `buildMenu()` to flatten the
      nested `category → groups → skills` structure for both `actives` and `passives`, building a new
      "主動技能" (or similarly labeled) menu section for `actives` alongside the existing "被動技能"
      section for `passives`, each iterating flattened `{key, label}` rows exactly as the current
      `passives.forEach(row => row.label)` loop does today.
- [x] 3.4 Confirm `web/static/webclient/js/plugins/character_dock.js` needs no change (it does not
      reference `passives`/`actives` directly) — a quick grep, not a code edit; record the result in
      the commit so a future reader does not re-investigate this.

## 4. Tests

- [x] 4.1 Add a regression test in `world/rules/tests/` (status_query test module) asserting a freshly
      created character's `active_keys` contains `flee` and `basic_attack` — pinning the bug this
      change fixes.
- [x] 4.2 Add tests for `group_skill_keys()`: category order follows `SkillCategory` declaration
      order; `elemental_magic` sub-group order follows `ELEMENT_REGISTRY` order; an empty category is
      omitted; a category with no `group` produces exactly one `group=None` sub-group; row order
      matches `owned_keys()` order; a key absent from `SKILL_REGISTRY` lands in the synthetic
      `"unknown"` bucket appended after every real category, with its row's `label` equal to its `key`.
- [x] 4.3 Add a test asserting `_split_active_passive_keys()` (or `owned_keys()`-derived reads more
      generally) de-duplicates a key appearing in both an entity's stored `active` and `passive` lists
      — `owned_keys()` itself does not de-duplicate, so this must be asserted at this layer.
- [x] 4.4 Add a test asserting `validate_character()` rejects a hand-constructed nested `passives` (or
      `actives`) payload whose flattened row count exceeds `MAX_PASSIVE_ROWS`/`MAX_ACTIVE_ROWS` even
      when its category-group count is well under `len(SkillCategory)` — mirrors
      `skill-category-combat-panel`'s equivalent `MAX_SKILLS` test (that proposal's task 6.2).
- [x] 4.5 Update `web/webclient/presentation/tests/test_character_panel.py`, in particular
      `test_unknown_item_and_skill_degrade_to_their_keys`, for the v3 nested `actives`/`passives`
      shape — it must keep asserting an unknown skill key renders with `label == key`, now inside the
      synthetic `"unknown"` category group rather than as a bare top-level row.
- [x] 4.6 Update `web/static/webclient/js/tests/character_menu.test.js` and `protocol.test.js` for
      the v3 payload shape, including the new `actives` field and the omitted-empty-category case.

## 5. Verification

- [x] 5.1 Run `uv run --locked python -m compileall -q world typeclasses commands server`.
- [x] 5.2 Run `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py world.rules.tests`
      (or the specific status_query test module) `web.webclient`.
- [x] 5.3 Run `node --test web/static/webclient/js/tests/character_menu.test.js web/static/webclient/js/tests/protocol.test.js`.
- [x] 5.4 Run `openspec validate skill-category-status-listing --strict`.
