## 1. SkillCategory and SkillDef fields

- [x] 1.1 Add `SkillCategory(StrEnum)` to `world/skills/registry.py` with exactly `ELEMENTAL_MAGIC`,
      `MARTIAL_ARTS`, `ENHANCEMENT`, `INNATE_GIFT`, `MOVEMENT`, `DIVINE_MYSTERY`, `UTILITY`,
      `SEXUAL_ACT`, in that declaration order.
- [x] 1.2 Add `category: SkillCategory` (no default) and `group: str | None = None` to `SkillDef`.
- [x] 1.3 In `SkillDef.__post_init__`, raise `ValueError` naming the skill's key when `group` is
      present and is not a non-empty string.
- [x] 1.4 Add `category` (required) and `group` (optional) parameters to `_skill()` and `_spell()`,
      threading them into the `SkillDef(...)` call in each.

## 2. Bulk classification via existing builders

- [x] 2.1 In `_elemental_spells()`, set `category=SkillCategory.ELEMENTAL_MAGIC` and
      `group=element` on every spell it builds (covers 75 elemental spell entries in one edit —
      verified per-element counts: fire 10, water 10, earth 9, wind 8, lightning 8, ice 10, light 10,
      dark 10; do not assume 79, the remaining 4 are individually built and classified in task 3.2).
- [x] 2.2 In `_body_multiplier()`, set `category=SkillCategory.ENHANCEMENT` on its 3 rows
      (`body_enhancement`, `body_enhancement_extreme`, `body_enhancement_basic`).

## 3. Explicit classification: elemental_magic (masteries and individually built extras)

- [x] 3.1 Classify the 8 element-mastery passives `fire_mastery`, `dark_mastery`, `wind_mastery`,
      `light_mastery`, `water_mastery`, `earth_mastery`, `lightning_mastery`, `ice_mastery` as
      `category=SkillCategory.ELEMENTAL_MAGIC`, `group=<their element key>`.
- [x] 3.2 Classify the 4 individually built elemental extras — `hardened_skin` (`group="earth"`),
      `gale_step` (`group="wind"`), `static_ward` (`group="lightning"`),
      `thunder_gods_haste` (`group="lightning"`) — as `category=SkillCategory.ELEMENTAL_MAGIC` with
      their respective `group`. These are ACTIVE, SELF-target, `self_buff_apply:*` skills built via
      individual `_skill()` calls, not through `_elemental_spells()`, so task 2.1's bulk edit does
      not reach them; verify with `grep -c "^        _skill("` or an AST parse that no other
      individually built skill carrying a non-null `element` was missed.

## 4. Explicit classification: martial_arts

- [x] 4.1 Classify `basic_attack`, `dual_blade_mastery`, `light_sword_style`, `shadow_slash`,
      `dual_wield_style` as `category=SkillCategory.MARTIAL_ARTS`, `group=None`.

## 5. Explicit classification: enhancement

- [x] 5.1 Classify `defense_instinct`, `blade_art_mastery`, `extreme_endurance`,
      `retainer_martial_training`, `guardian_instinct`, `magic_circle_comprehension`,
      `precise_mana_control`, `concentration` as `category=SkillCategory.ENHANCEMENT`, `group=None`.

## 6. Explicit classification: innate_gift, movement, divine_mystery, utility

- [x] 6.1 Classify `reincarnation_boon_elosia`, `reincarnation_boon_yuka`, `elf_longevity` as
      `category=SkillCategory.INNATE_GIFT`, `group=None`.
- [x] 6.2 Classify `flight`, `flash_step` as `category=SkillCategory.MOVEMENT`, `group=None`.
- [x] 6.3 Classify `divine_time_dilation`, `divine_space_distortion`, `divine_matter_transmutation`,
      `divine_life_extension` as `category=SkillCategory.DIVINE_MYSTERY`, `group=None`.
- [x] 6.4 Classify `status_disguise`, `dominion_art` as `category=SkillCategory.UTILITY`,
      `group=None`.

## 7. Explicit classification: sexual_act (existing skills)

- [x] 7.1 Classify `divine_sexual_arts` as `category=SkillCategory.SEXUAL_ACT`, `group="神之秘法"`.
- [x] 7.2 Classify `divine_sexual_mastery` and `reincarnation_boon_yuna` as
      `category=SkillCategory.SEXUAL_ACT`, `group="精通"`.

## 8. flee (world/rules/disengage.py)

- [x] 8.1 Import `SkillCategory` from `world.skills.registry` in `world/rules/disengage.py`.
- [x] 8.2 Add `category=SkillCategory.MOVEMENT` to `flee`'s direct `SkillDef(...)` construction.

## 9. Test-fixture SkillDef construction sites

Every site below adds an explicit `category` keyword argument (`SkillCategory.UTILITY` is an
acceptable default for a synthetic test-only skill never shown to a player, unless the surrounding
test's intent suggests a more fitting category — use judgment, it has no mechanical effect). Import
`SkillCategory` in each file as needed.

- [x] 9.1 `world/quests/tests/test_action_events.py:107` — `test_two_damage_effects_emit_one_defeat`'s
      in-test `SKILL_REGISTRY[skill_key] = SkillDef(...)`.
- [x] 9.2 `world/quests/tests/test_planner.py:44` and `:56` — module-level `CLAW_SKILL` and
      `STRIKE_SKILL` constants.
- [x] 9.3 `world/rules/tests/test_friendly_fire.py:54` and `:540` — module-level `FRIENDLY_DOUBLE`
      constant and the `HealingWithoutPenaltyTests._recovery_skill()` helper.
- [x] 9.4 `world/rules/tests/test_heal_effect_handler.py:186` — the `_grant()` helper's `SkillDef(...)`.
- [x] 9.5 `world/rules/tests/test_effect_handlers.py:44` — module-level `PURIFY_TEST_SKILL` constant.
- [x] 9.6 `world/skills/tests/test_registry.py:247` (`test_direct_construction_observes_immutability_
      and_metadata_bounds`'s `direct` skill — success path, needs `category` to avoid `TypeError`).
- [x] 9.7 `world/skills/tests/test_registry.py:263` and `:275` — both inside
      `assertRaises(ValueError)` blocks (empty label, oversized description); without `category` the
      construction raises `TypeError` first, which `assertRaises(ValueError)` does not catch.
- [x] 9.8 `world/skills/tests/test_registry.py:297` — inside `assertRaises(ValueError)` for an
      unrecognized effect prefix; same reasoning as 9.7.
- [x] 9.9 `world/skills/tests/test_registry.py:318` (`assertRaises(ValueError)`, heal-shape mismatch
      loop) and `:337` (`test_construction_rejects_a_heal_shape_mismatching_the_target_spec`'s
      matching-shape success-path loop).
- [x] 9.10 Confirm `world/skills/tests/test_registry.py:117`
      (`test_constructing_without_metadata_fails_closed`) needs **no** change — it already omits
      `label`/`description` (already-required fields) and expects `TypeError`; a missing `category`
      raises the same exception type, so the test keeps passing unmodified. Do not add `category`
      here; the point of this task is to verify that leaving it alone is correct, not to edit it.
- [x] 9.11 `world/skills/tests/test_registry.py:42` —
      `test_registry_uses_the_exact_forward_declared_contract`'s expected `fields(SkillDef)` list
      gains `category` and `group` between `effects` and `faction_constraint`, matching the new
      dataclass declaration order. Not a fixture site but the same collection-breaking class of
      edit: the assertion is an exact list comparison, so it fails until updated. (The repo-wide
      search in section 9's preamble counted only `SkillDef(...)` *construction* sites; this
      assertion site is listed here for completeness.)

## 10. Structural tests

- [x] 10.1 Add a test asserting every `SKILL_REGISTRY` key (after importing `world.rules.disengage`)
      has a `category` that is a member of `SkillCategory`.
- [x] 10.2 Add a test asserting the union of the eight per-category key sets equals
      `set(SKILL_REGISTRY.keys())` exactly, with no key in more than one set. Additionally assert the
      per-category key sets match design D-4's table exactly (the seven non-elemental categories as
      literals, `ELEMENTAL_MAGIC` as their complement) — the union test alone cannot catch a category
      *swap* between two individually built skills (rubber-duck review finding).
- [x] 10.3 Add a test asserting every `ELEMENTAL_MAGIC` member's `group` equals its own `element.key`
      exactly (not merely that `group` is *some* valid `ELEMENT_REGISTRY` key) — this is the check
      that would catch a mis-paired `group` such as a fire spell tagged `group="water"`.
- [x] 10.4 Add a test asserting every `SEXUAL_ACT` member's `group` is a non-null, non-empty string.
- [x] 10.5 Add a test asserting every member of the other six categories has `group is None`.
- [x] 10.6 Add a test asserting `SkillDef(...)` constructed without `category` raises `TypeError`.
- [x] 10.7 Add a test asserting `SkillDef(...)` constructed with `group=""` raises `ValueError` (and,
      per the spec requirement's "not a non-empty string" wording, `group=123` raises `ValueError`
      naming the key rather than `AttributeError` — rubber-duck review finding; see also spec
      scenario "A non-string group raises at construction").
- [x] 10.8 Add a test asserting `divine_sexual_arts`'s `requires_divine_arts`, `effects`, `kind`,
      `cost`, and `target_spec` are unchanged from their pre-classification values while `category`
      is `SEXUAL_ACT` and `group` is `"神之秘法"`.
- [x] 10.9 Add a test asserting that for every `ELEMENTAL_MAGIC` member, `effects` is unchanged from
      its pre-classification value (a loop over the whole category, not a single spot-check) —
      proves classification touched no other field across the entire category, not just one skill.
      Mastery members are identified by an explicit `_MASTERY_KEYS` set derived from
      `ELEMENT_REGISTRY`, not by a `_mastery` name suffix (rubber-duck review finding).
- [x] 10.11 Add a test asserting `list(SkillCategory)` equals exactly `[ELEMENTAL_MAGIC, MARTIAL_ARTS,
      ENHANCEMENT, INNATE_GIFT, MOVEMENT, DIVINE_MYSTERY, UTILITY, SEXUAL_ACT]` in that order —
      pins the spec's member-set/order scenario to an actual assertion, not an implicit one.
- [x] 10.12 Add a test asserting `SkillDef(...)` constructed with `category` supplied and `group`
      omitted succeeds with `skill.group is None` — pins the dataclass-default scenario (10.6/10.7
      cover only the failure paths).
- [x] 10.13 Add a test asserting `SKILL_REGISTRY["flee"]` (after importing `world.rules.disengage`)
      has `category` `SkillCategory.MOVEMENT` and `group is None` — pins the
      `universal-action-ownership` delta's first scenario; 10.1 covers only that the category is
      *valid*, not that it is specifically `MOVEMENT`.
- [x] 10.10 Add a test asserting `world/rules/disengage.py` fails to import if `flee`'s `SkillDef(...)`
      construction omits `category` (e.g. via a targeted monkeypatch or by asserting the source
      supplies the argument) — makes the fail-closed behavior claimed in the `universal-action-
      ownership` delta spec's scenario traceable to an actual test, not just dataclass semantics.
      Implemented as an AST assertion that finds the unique `SKILL_REGISTRY[...]` `SkillDef` call and
      requires an explicit `category=SkillCategory.MOVEMENT` keyword — tightened to fail if no match
      or more than one match exists (rubber-duck review finding).

## 11. Verification

- [x] 11.1 Run `uv run --locked python -m compileall -q world typeclasses commands server`.
- [x] 11.2 Run the focused test modules touched by sections 9–10:
      `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py world.skills world.quests world.rules`.
- [x] 11.3 Run the **full** non-browser Evennia suite, not just the modules this change directly
      touches — the point of section 9 is that a missed test-fixture site breaks an unrelated test
      module's collection, which only a full run reliably surfaces:
      `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb commands server typeclasses world web.webclient`.
- [x] 11.4 Run `uv run --locked python -m unittest discover -s tests -t .` for repository-wide
      contract tests.
- [x] 11.5 Run `openspec validate skill-category-registry --strict`.
