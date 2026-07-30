## 1. Package layout

- [x] 1.1 Confirm `world/skills/` does not exist yet (no earlier change created even an empty stub);
      create `world/skills/__init__.py` and `world/skills/tests/__init__.py`.
- [x] 1.2 Create `world/skills/registry.py`, `world/skills/handler.py`, `world/skills/equipment.py` as
      empty modules with module docstrings referencing design doc §3.2/§5.2 and this change. The
      `registry.py` docstring additionally states that `SkillKind`/`TargetSpec` are forward-declared
      for change 8 (`action-resolver`) to import rather than redefine (design.md D-2).

## 2. Skill registry (`world/skills/registry.py`)

- [x] 2.1 Define `SkillKind(StrEnum)` with members `ACTIVE`, `PASSIVE`, and `TargetSpec(StrEnum)` with
      members `NONE`, `SELF`, `SINGLE`, `AREA` — per design.md D-2, zero behavior beyond the enum
      values.
- [x] 2.2 Define the frozen `SkillDef` dataclass with exactly the seven fields design doc §5.2 gives:
      `key: str`, `kind: SkillKind`, `target_spec: TargetSpec`, `cost: dict[str, int]`,
      `usable_out_of_combat: bool`, `element: Element | None`, `effects: list[str]` — per design.md
      D-3. Import `Element` from `world.lore.elements`.
- [x] 2.3 Author the seed `SKILL_REGISTRY: dict[str, SkillDef]` per design.md D-4's table (~27
      entries): stat multipliers (`body_enhancement` x100, `body_enhancement_extreme` x1000,
      `body_enhancement_basic` x1.2 — flagged judgment call), elemental mastery (`fire_mastery`,
      `dark_mastery`, `wind_mastery`, `light_mastery`, each `PASSIVE` with `element` set and
      `effects=["element_mastery_rank:主宰"]`), direct spells (`fire_ball`, `wind_blade`, `flight`),
      weapon arts (`dual_wield_style`, `light_sword_style`, `shadow_slash`, `flash_step`), the
      display-only skill (`status_disguise`), the conferral skill (`dominion_art`), ordinary passives
      (`defense_instinct`, `blade_art_mastery`, `extreme_endurance`, `magic_circle_comprehension`,
      `precise_mana_control`, `retainer_martial_training`, `guardian_instinct`, `elf_longevity`), and the
      per-character-unique 轉生特典 pattern (`reincarnation_boon_elosia`, `reincarnation_boon_yuka`,
      `reincarnation_boon_yuna`), each with a distinct `effects` entry.
- [x] 2.4 Encode the `stat_multiply:<trait_key>:<multiplier>` convention (design.md D-5) inside the
      `effects` list of every stat-multiplier `SkillDef`, and document in `registry.py`'s module
      docstring that this is the one effect-ID convention `SkillHandler` itself interprets — every
      other effect ID is opaque, owned by change 6's future rulebook engine.
- [x] 2.5 Preserve the exact `dict`/`list` field contract while making every seed `cost` and `effects`
      collection reject nested mutation; add a regression test that balance data cannot be changed
      through a frozen `SkillDef`.

## 3. Skill handler and resolution-time multiplier (`world/skills/handler.py`)

- [x] 3.1 Implement `SkillHandler.__init__(self, entity)` and `_raw` per design.md D-10: reads
      `entity.db.skills` (the private raw-storage attribute, distinct from `entity.skills` itself,
      which will be this handler), defaulting to `{"active": [], "passive": []}` when `None`, with no
      assumption that the attribute has ever been touched by change 4's loader.
- [x] 3.2 Implement `SkillHandler.owned_keys()` returning the combined active+passive key list.
- [x] 3.3 Implement `_parse_stat_multiply(effect_id: str) -> tuple[str, float] | None` per design.md
      D-5: parses the `stat_multiply:<trait_key>:<multiplier>` convention only; returns `None` for
      every other effect ID shape (no exception, since most effect IDs are legitimately opaque here).
- [x] 3.4 Implement `SkillHandler.effective_value(trait_key: str) -> int` per design.md D-5: reads
      `entity.traits.<trait_key>.value` as the base, multiplies by every owned active skill's matching
      `stat_multiply` effect (multiplicative combination across multiple owned multiplier skills) and
      every applicable source skill's matching multiplier times its `ConferredSkillGrant`'s
      fractional `scale` (task 3.6), and returns the rounded product.
      This function and every other function in this module MUST NOT assign to
      `entity.traits.<anything>.value`, `.base`, or `.mod` anywhere.
- [x] 3.5 Define the frozen `ConferredSkillGrant` dataclass (`source_key: str`, `skill_key: str`,
      `trait_keys: tuple[str, ...]`, `scale: float`) per design.md D-6.
- [x] 3.6 Implement read-only `SkillHandler.conferred_grants()` (reads
      `entity.db.skill_grants`, defaulting to `[]`) and the deterministic-core
      `world.rules.skill_effects.record_conferred_grant()` persistence primitive per design.md D-6;
      wire task 3.4's `effective_value()` to fold in every applicable grant.
- [x] 3.7 Implement `world.rules.skill_effects.apply_disguise_effect(entity, overrides) -> None` per
      design.md D-7: the deterministic-core write for `status_disguise`, setting only
      `entity.db.disguised_stats` and containing no reference to `entity.traits`.
- [x] 3.8 In `typeclasses/entities.py`, **replace** change 3's `skills = AttributeProperty(default=
      None)` declaration with a real handler mount per design.md D-10:
      ```python
      @lazy_property
      def skills(self):
          return SkillHandler(self)
      ```
      (`evennia.utils.lazy_property` — confirm the exact caching mechanism against however change 3
      mounted `entity.traits`, per this project's established contrib-verification discipline, before
      assuming `lazy_property` is the right primitive). `entity.skills` is now read-only — there is no
      bare-assignment form, matching `entity.traits`.
- [x] 3.9 Make duplicate occurrences of an active skill key resolution-idempotent and reject a
      contradictory `SkillDef` containing more than one multiplier for the same trait.

## 4. Equipment and inventory (`world/skills/equipment.py`)

- [x] 4.1 Define `EquipmentSlot(StrEnum)` with exactly `WEAPON_MAIN`, `WEAPON_OFF`, `ARMOR`,
      `ACCESSORY` per design.md D-8. Docstring flags evadventure's actual `WieldLocation` member names
      as unverified against a locally installed Evennia 6.1.0 — confirm before assuming any literal
      reuse, per this project's established contrib-verification discipline (changes 1-4).
- [x] 4.2 Implement `EquipmentHandler.__init__(self, entity)` and `_raw` per design.md D-8/D-10: reads
      `entity.db.equipment` (the private raw-storage attribute, distinct from `entity.equipment`
      itself, which will be this handler), defaulting to `{"weapon_main": None, "weapon_off": None,
      "armor": None, "accessories": []}` when `None` or `{}`.
- [x] 4.3 Implement read-only `EquipmentHandler.slot_contents(slot)` plus deterministic-core
      `world.rules.equipment.equip_item()` / `unequip_item()` per design.md D-8: the three
      single-item slots hold one item key or `None`; `ACCESSORY` holds a list capped at
      `ACCESSORY_MAX_SLOTS = 3`, and equipping beyond the cap raises.
- [x] 4.4 In `typeclasses/entities.py`, **replace** change 3's `equipment = AttributeProperty(default=
      None)` declaration with a real handler mount per design.md D-10:
      ```python
      @lazy_property
      def equipment(self):
          return EquipmentHandler(self)
      ```
      `entity.equipment` is now read-only — there is no bare-assignment form, matching
      `entity.traits`.
- [x] 4.5 Implement mutating `add_item(entity, item_key)` / `remove_item(entity, item_key)` under
      `world.rules.equipment` and read-only `list_items(entity)` under `world.skills.equipment` per
      design.md D-9, tolerating `None` as empty.

## 5. Combat-state-blindness guard

- [x] 5.1 Write a regression test that enumerates every public callable in
      `world/skills/handler.py` and `world/skills/equipment.py` via `inspect.signature()` and asserts
      no parameter name matches `in_combat`, `combat_state`, `is_combat`, or `turn` — per design.md
      D-11.
- [x] 5.2 Write a source-scanning check (mirroring change 3's D-9 tripwire style) asserting neither
      module's source contains a conditional branch keyed on a combat-state concept, and that no
      `ActionResolver`-like class or turn-scheduling dispatch exists anywhere in `world/skills/`.
- [x] 5.3 Add an AST tripwire over every production module under `world/skills/` that rejects
      persistent entity-state assignments and imports from `world.rules`, enforcing the
      architecture's single-writer dependency direction.

## 6. Tests

- [x] 6.1 `world/skills/tests/test_registry.py` — per the `skill-registry` capability: `SKILL_REGISTRY`
      is importable at `world.skills.registry.SKILL_REGISTRY` and non-empty; every `SkillDef` exposes
      exactly the seven documented fields via `dataclasses.fields()`; `kind`/`target_spec` are valid
      enum members; every non-`None` `element` resolves in `ELEMENT_REGISTRY`; `cost` values are all
      non-negative integers; `TargetSpec`/`SkillKind` have exactly their documented members and no
      extra methods; the seed set includes the three stat-multiplier tiers, all four elemental-mastery
      skills, exactly one conferral skill and one disguise skill, and at least three distinct
      per-character-unique passives.
- [x] 6.2 `world/skills/tests/test_handler.py` — per the `skill-handler` capability:
      `entity.skills` reads `entity.db.skills` correctly and tolerates `None`; `entity.skills = {...}`
      raises (no bare-assignment form); assigning `entity.db.skills = {...}` directly still works and
      is reflected by `entity.skills`; `effective_value()` multiplies correctly for a known base
      value and known active multiplier skill; `effective_value()` never mutates
      `entity.traits.<key>.value`; grep-based assertion that `world/skills/handler.py` contains no
      assignment to `entity.traits.<anything>`; an entity with no matching multiplier skill returns
      the unmultiplied base; every constructed entity's static trait base values stay within the
      documented `StaticBand`/`static_band` range regardless of how many times `effective_value()` is
      called (reusing change 3's band-check fixtures).
- [x] 6.3 `world/skills/tests/test_conferral.py` — per the `skill-handler` capability's conferral
      requirement: a `ConferredSkillGrant` with `scale=0.1` on a ×100 source skill produces a ×10
      effective value, not the source's own ×100; the deterministic-core persistence primitive stores
      an explicit grant while `SkillHandler` exposes no mutator; confirm no code path performs
      ownership/resource/target validation before change 8's `ActionResolver`.
- [x] 6.4 `world/skills/tests/test_disguise_effect.py` — per the `skill-handler` capability's D2
      requirement: `apply_disguise_effect()` sets `entity.db.disguised_stats` and leaves every
      `entity.traits.<key>.value` unchanged; source-scan assertion that the function's definition
      under `world/rules/skill_effects.py` contains no reference to `entity.traits` or
      `get_display_value`.
- [x] 6.5 `world/skills/tests/test_combat_blindness.py` — the two regression checks from tasks 5.1
      and 5.2.
- [x] 6.6 `world/skills/tests/test_equipment.py` — per the `equipment-inventory` capability:
      `EquipmentSlot` has exactly its four documented members; a dual-wielded pair occupies
      `WEAPON_MAIN`/`WEAPON_OFF` independently; `entity.equipment` reads `entity.db.equipment`
      correctly and tolerates `None`/`{}`; `entity.equipment = {...}` raises (no bare-assignment
      form); assigning `entity.db.equipment = {...}` directly still works and is reflected by
      `entity.equipment`; accessories can be equipped up to `ACCESSORY_MAX_SLOTS` and equipping one
      more raises.
- [x] 6.7 `world/skills/tests/test_inventory.py` — per the `equipment-inventory` capability:
      `add_item`/`remove_item`/`list_items` behave correctly against `entity.db.inventory`, including
      the `None`-tolerance case and reflecting an inventory already populated by change 4's
      `instantiate_character()`.
- [x] 6.8 Update change 3's `typeclasses/tests/test_entities.py` forward-seam regression to expect
      `EquipmentHandler` and `SkillHandler` on every `LivingEntity` subclass while preserving the
      remaining unimplemented seams as `None`.
- [x] 6.9 Add Evennia database round-trip tests proving conferred-grant dataclasses and equipment
      snapshots survive serialization and remain readable through their handlers.

## 7. Cross-change contract verification

- [x] 7.0 Confirm the landed `world/imports/loader.py` already writes imported skill and equipment
      shapes to `entity.db.skills` / `entity.db.equipment`, the private storage locations
      `SkillHandler`/`EquipmentHandler` read per design.md D-10. Do not change
      `CHARACTER_SCHEMA_V1`, `validate.py`, or the reference example.
- [x] 7.1 Run change 4's full `world/imports/tests/` suite and confirm
      `test_skill_registry_self_arming.py` (change 4's task 7.3a) is no longer reported as skipped —
      it now executes and passes, asserting an unknown skill key is rejected via `_check_skills()`.
- [x] 7.2 Run
      `uv run --locked -m world.imports.validate world/imports/examples/example_character.json`
      (the change-4 reference example) and confirm the degraded-mode banner naming `skill-registry`
      no longer appears, since `world.skills.registry.SKILL_REGISTRY` is now importable — this is
      the visible, operator-facing sign that change 4's validation has tightened from WARNING to REJECT
      automatically, with no edit to change 4 itself.
- [x] 7.3 Confirm the change-4 reference example's `skills`/`passives` keys either resolve in this
      change's `SKILL_REGISTRY` or, if they do not (the reference example was authored against no
      registry), update nothing in change 4 — instead confirm this is a pre-existing, expected gap
      documented in change 4's own design (its reference example was authored before any registry
      existed) and not a regression this change introduces silently.

## 8. Verification

- [x] 8.1 Run the full `world/skills/tests/` suite and confirm all tests pass.
- [x] 8.2 Confirm no function in `world/skills/handler.py` assigns to `entity.traits.<anything>`,
      `.base`, or `.mod` (grep by hand as a spot check, mirroring change 3's task 7.5 discipline).
- [x] 8.3 Confirm `typeclasses/entities.py`'s diff for this change touches only the `skills`/
      `equipment` declarations — each replaced with a `@lazy_property` handler mount per design.md
      D-10 — and no other attribute, method, or base class change 3 authored is altered.
- [x] 8.4 Confirm the existing change-4 `loader.py` private-storage writes (task 7.0) remain covered
      by integration tests and populate the new read-only handlers successfully.
- [x] 8.5 Run `openspec validate skills-equipment --strict` and confirm it passes.
