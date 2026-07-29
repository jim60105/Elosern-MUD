## 1. Package layout

- [ ] 1.1 Confirm `world/skills/` does not exist yet (no earlier change created even an empty stub);
      create `world/skills/__init__.py` and `world/skills/tests/__init__.py`.
- [ ] 1.2 Create `world/skills/registry.py`, `world/skills/handler.py`, `world/skills/equipment.py` as
      empty modules with module docstrings referencing design doc §3.2/§5.2 and this change. The
      `registry.py` docstring additionally states that `SkillKind`/`TargetSpec` are forward-declared
      for change 8 (`action-resolver`) to import rather than redefine (design.md D-2).

## 2. Skill registry (`world/skills/registry.py`)

- [ ] 2.1 Define `SkillKind(StrEnum)` with members `ACTIVE`, `PASSIVE`, and `TargetSpec(StrEnum)` with
      members `NONE`, `SELF`, `SINGLE`, `AREA` — per design.md D-2, zero behavior beyond the enum
      values.
- [ ] 2.2 Define the frozen `SkillDef` dataclass with exactly the seven fields design doc §5.2 gives:
      `key: str`, `kind: SkillKind`, `target_spec: TargetSpec`, `cost: dict[str, int]`,
      `usable_out_of_combat: bool`, `element: Element | None`, `effects: list[str]` — per design.md
      D-3. Import `Element` from `world.lore.elements`.
- [ ] 2.3 Author the seed `SKILL_REGISTRY: dict[str, SkillDef]` per design.md D-4's table (~24
      entries): stat multipliers (`body_enhancement` x100, `body_enhancement_extreme` x1000,
      `body_enhancement_basic` x1.2 — flagged judgment call), elemental mastery (`fire_mastery`,
      `dark_mastery`, `wind_mastery`, `light_mastery`, each `PASSIVE` with `element` set and
      `effects=["element_mastery_rank:主宰"]`), direct spells (`fire_ball`, `wind_blade`, `flight`),
      weapon arts (`dual_wield_style`, `light_sword_style`, `shadow_slash`, `flash_step`), the
      display-only skill (`status_disguise`), the conferral skill (`dominion_art`), ordinary passives
      (`defense_instinct`, `blade_art_mastery`, `extreme_endurance`, `magic_circle_comprehension`,
      `precise_mana_control`, `retainer_martial_training`, `guardian_instinct`), and the
      per-character-unique 轉生特典 pattern (`reincarnation_boon_elosia`, `reincarnation_boon_yuka`,
      `reincarnation_boon_yuna`), each with a distinct `effects` entry.
- [ ] 2.4 Encode the `stat_multiply:<trait_key>:<multiplier>` convention (design.md D-5) inside the
      `effects` list of every stat-multiplier `SkillDef`, and document in `registry.py`'s module
      docstring that this is the one effect-ID convention `SkillHandler` itself interprets — every
      other effect ID is opaque, owned by change 6's future rulebook engine.

## 3. Skill handler and resolution-time multiplier (`world/skills/handler.py`)

- [ ] 3.1 Implement `SkillHandler.__init__(self, entity)` and `_raw` per design.md D-10: reads
      `entity.skills`, defaulting to `{"active": [], "passive": []}` when `None`, with no assumption
      that the attribute has ever been touched by change 4's loader.
- [ ] 3.2 Implement `SkillHandler.owned_keys()` returning the combined active+passive key list.
- [ ] 3.3 Implement `_parse_stat_multiply(effect_id: str) -> tuple[str, float] | None` per design.md
      D-5: parses the `stat_multiply:<trait_key>:<multiplier>` convention only; returns `None` for
      every other effect ID shape (no exception, since most effect IDs are legitimately opaque here).
- [ ] 3.4 Implement `SkillHandler.effective_value(trait_key: str) -> int` per design.md D-5: reads
      `entity.traits.<trait_key>.value` as the base, multiplies by every owned active skill's matching
      `stat_multiply` effect (multiplicative combination across multiple owned multiplier skills) and
      every applicable `ConferredSkillGrant`'s `scale` (task 3.6), and returns the rounded product.
      This function and every other function in this module MUST NOT assign to
      `entity.traits.<anything>.value`, `.base`, or `.mod` anywhere.
- [ ] 3.5 Define the frozen `ConferredSkillGrant` dataclass (`source_key: str`, `skill_key: str`,
      `trait_keys: tuple[str, ...]`, `scale: float`) per design.md D-6.
- [ ] 3.6 Implement `SkillHandler.conferred_grants()` (reads `entity.db.skill_grants`, defaulting to
      `[]`) and `SkillHandler.grant_conferred(source_key, skill_key, trait_keys, scale)` (appends a new
      `ConferredSkillGrant` to `entity.db.skill_grants`) per design.md D-6 — a plain, unconditional
      data write with no ownership or resource check; wire task 3.4's `effective_value()` to fold in
      every grant whose `trait_keys` contains the requested trait.
- [ ] 3.7 Implement `apply_disguise_effect(entity, overrides: dict[str, int]) -> None` per design.md
      D-7: the complete effect body for `status_disguise`, setting `entity.db.disguised_stats =
      overrides` and containing no reference to `entity.traits` anywhere in the function.
- [ ] 3.8 Add `skill_handler` as a property on `LivingEntity` (`typeclasses/entities.py`) returning
      `SkillHandler(self)`, per design.md D-10 — additive only; do not remove or alter the existing
      `skills = AttributeProperty(default=None)` declaration change 3 authored, so change 4's
      `entity.skills = {...}` write pattern continues to work unmodified.

## 4. Equipment and inventory (`world/skills/equipment.py`)

- [ ] 4.1 Define `EquipmentSlot(StrEnum)` with exactly `WEAPON_MAIN`, `WEAPON_OFF`, `ARMOR`,
      `ACCESSORY` per design.md D-8. Docstring flags evadventure's actual `WieldLocation` member names
      as unverified against a locally installed Evennia 6.1.0 — confirm before assuming any literal
      reuse, per this project's established contrib-verification discipline (changes 1-4).
- [ ] 4.2 Implement `EquipmentHandler.__init__(self, entity)` and `_raw` per design.md D-8/D-10: reads
      `entity.equipment`, defaulting to `{"weapon_main": None, "weapon_off": None, "armor": None,
      "accessories": []}` when `None` or `{}`.
- [ ] 4.3 Implement `EquipmentHandler.equip(slot, item_key)`, `.unequip(slot)`,
      `.slot_contents(slot)` per design.md D-8: the three single-item slots (`WEAPON_MAIN`,
      `WEAPON_OFF`, `ARMOR`) hold one item key or `None`; `ACCESSORY` holds a list capped at
      `ACCESSORY_MAX_SLOTS = 3` (judgment call, documented as invented — no source states a cap);
      `.equip()` on a full `ACCESSORY` slot raises rather than silently exceeding the cap.
- [ ] 4.4 Add `equipment_handler` as a property on `LivingEntity` (`typeclasses/entities.py`) returning
      `EquipmentHandler(self)`, additive only — do not alter the existing `equipment =
      AttributeProperty(default=None)` declaration, so change 4's `entity.equipment = {...}` write
      pattern continues to work unmodified.
- [ ] 4.5 Implement `add_item(entity, item_key)`, `remove_item(entity, item_key)`, `list_items(entity)`
      per design.md D-9: plain functions operating directly on `entity.db.inventory` (the raw
      attribute change 4's D-13 already established), tolerating `None` as "empty."

## 5. Combat-state-blindness guard

- [ ] 5.1 Write a regression test that enumerates every public callable in
      `world/skills/handler.py` and `world/skills/equipment.py` via `inspect.signature()` and asserts
      no parameter name matches `in_combat`, `combat_state`, `is_combat`, or `turn` — per design.md
      D-11.
- [ ] 5.2 Write a source-scanning check (mirroring change 3's D-9 tripwire style) asserting neither
      module's source contains a conditional branch keyed on a combat-state concept, and that no
      `ActionResolver`-like class or turn-scheduling dispatch exists anywhere in `world/skills/`.

## 6. Tests

- [ ] 6.1 `world/skills/tests/test_registry.py` — per the `skill-registry` capability: `SKILL_REGISTRY`
      is importable at `world.skills.registry.SKILL_REGISTRY` and non-empty; every `SkillDef` exposes
      exactly the seven documented fields via `dataclasses.fields()`; `kind`/`target_spec` are valid
      enum members; every non-`None` `element` resolves in `ELEMENT_REGISTRY`; `cost` values are all
      non-negative integers; `TargetSpec`/`SkillKind` have exactly their documented members and no
      extra methods; the seed set includes the three stat-multiplier tiers, all four elemental-mastery
      skills, exactly one conferral skill and one disguise skill, and at least three distinct
      per-character-unique passives.
- [ ] 6.2 `world/skills/tests/test_handler.py` — per the `skill-handler` capability:
      `entity.skill_handler` reads `entity.skills` correctly and tolerates `None`; assigning
      `entity.skills` directly still works; `effective_value()` multiplies correctly for a known base
      value and known active multiplier skill; `effective_value()` never mutates
      `entity.traits.<key>.value`; grep-based assertion that `world/skills/handler.py` contains no
      assignment to `entity.traits.<anything>`; an entity with no matching multiplier skill returns
      the unmultiplied base; every constructed entity's static trait base values stay within the
      documented `StaticBand`/`static_band` range regardless of how many times `effective_value()` is
      called (reusing change 3's band-check fixtures).
- [ ] 6.3 `world/skills/tests/test_conferral.py` — per the `skill-handler` capability's conferral
      requirement: a `ConferredSkillGrant` with `scale=0.1` on a ×100 source skill produces a ×10
      effective value, not the source's own ×100; `grant_conferred()` performs no ownership/resource
      check and never raises for an unknown `source_key`; confirm no code path in this change's
      modules creates a `ConferredSkillGrant` autonomously (i.e., without an explicit test or future
      `ActionResolver` call).
- [ ] 6.4 `world/skills/tests/test_disguise_effect.py` — per the `skill-handler` capability's D2
      requirement: `apply_disguise_effect()` sets `entity.db.disguised_stats` and leaves every
      `entity.traits.<key>.value` unchanged; source-scan assertion that the function's definition
      contains no reference to `entity.traits` or `get_display_value`.
- [ ] 6.5 `world/skills/tests/test_combat_blindness.py` — the two regression checks from tasks 5.1
      and 5.2.
- [ ] 6.6 `world/skills/tests/test_equipment.py` — per the `equipment-inventory` capability:
      `EquipmentSlot` has exactly its four documented members; a dual-wielded pair occupies
      `WEAPON_MAIN`/`WEAPON_OFF` independently; `entity.equipment_handler` reads equipment change 4's
      loader already wrote and tolerates `None`/`{}`; assigning `entity.equipment` directly still
      works; accessories can be equipped up to `ACCESSORY_MAX_SLOTS` and equipping one more raises.
- [ ] 6.7 `world/skills/tests/test_inventory.py` — per the `equipment-inventory` capability:
      `add_item`/`remove_item`/`list_items` behave correctly against `entity.db.inventory`, including
      the `None`-tolerance case and reflecting an inventory already populated by change 4's
      `instantiate_character()`.

## 7. Cross-change contract verification

- [ ] 7.1 Run change 4's full `world/imports/tests/` suite and confirm
      `test_skill_registry_self_arming.py` (change 4's task 7.3a) is no longer reported as skipped —
      it now executes and passes, asserting an unknown skill key is rejected via `_check_skills()`.
- [ ] 7.2 Run `python -m world.imports.validate world/imports/examples/example_character.json` (the
      change-4 reference example) and confirm the degraded-mode banner naming `skill-registry` no
      longer appears, since `world.skills.registry.SKILL_REGISTRY` is now importable — this is the
      visible, operator-facing sign that change 4's validation has tightened from WARNING to REJECT
      automatically, with no edit to change 4 itself.
- [ ] 7.3 Confirm the change-4 reference example's `skills`/`passives` keys either resolve in this
      change's `SKILL_REGISTRY` or, if they do not (the reference example was authored against no
      registry), update nothing in change 4 — instead confirm this is a pre-existing, expected gap
      documented in change 4's own design (its reference example was authored before any registry
      existed) and not a regression this change introduces silently.

## 8. Verification

- [ ] 8.1 Run the full `world/skills/tests/` suite and confirm all tests pass.
- [ ] 8.2 Confirm no function in `world/skills/handler.py` assigns to `entity.traits.<anything>`,
      `.base`, or `.mod` (grep by hand as a spot check, mirroring change 3's task 7.5 discipline).
- [ ] 8.3 Confirm `typeclasses/entities.py`'s diff is additive only for this change — the existing
      `skills`/`equipment` `AttributeProperty` declarations from change 3 are unchanged, and only the
      two new `skill_handler`/`equipment_handler` properties are added.
- [ ] 8.4 Run `openspec validate skills-equipment --strict` and confirm it passes.
