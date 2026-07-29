## Why

This is roadmap item #3 (design doc §11), depending on change 1 (`bootstrap-container-evennia`)
for the running Evennia project and change 2 (`lore-world-data`) for `RaceProfile` and the other
typed registries. Every Phase 1+ change after this one needs something concrete to attach to:
`import-contract` (change 4) needs a typeclass to instantiate validated character JSON into,
`skills-equipment` (change 5) needs a handler seam to mount `SkillHandler`/`EquipmentHandler` onto,
`buffs-rulebook` (change 6) needs a seam for `BuffHandler`, and `sexual-state` (change 7) needs a
seam for `SexualState`. Right now `LivingEntity` is only a diagram in design doc §5.2 — nothing
downstream can be built against a class that doesn't exist, and the three-orders-of-magnitude power
gap between races (D1) has nowhere to land at the entity level even though change 2 already encodes
it in `RaceProfile`.

## What Changes

- Add `typeclasses/entities.py`: `LivingEntity`, the shared base for player characters, NPCs, and
  monsters, per design doc §5.2. Mounts `TraitHandler` (`evennia.contrib.rpg.traits`, confirmed by
  §4) with the setting's eight-key trait set — `hp`/`mp`/`sp` as **gauges** (max + regen rate),
  `atk_phys`/`agility`/`defense` as **static** (base + mod), `magic_level`/`guild_merit` as
  **counters**. Uses `ComponentHolderMixin` (`evennia.contrib.base_systems.components`, per §4's
  assignment of that contrib to `typeclasses/entities.py`) so later changes can attach
  `QuestGiver`/`Merchant`/`GuildStaff` components without a base-class change.
- Add `world/rules/traits.py`: the derivation logic that seeds a `LivingEntity`'s initial trait
  values by **reading change 2's lore fields directly** — `RaceProfile.vital_baseline` (hp/mp/sp
  gauge maxes), `RaceProfile.static_baseline` (atk_phys/agility/defense static bases — a distinct
  field from `vital_baseline`, since the two scale by different, independently documented factors:
  ~100× human→elf for vitals, ~10× for statics), and `RaceProfile.magic_cap` (magic_level counter
  max). `Subrace.static_modifiers` (per-subspecies fractional deltas) and `Subrace.vital_overrides`
  (per-subspecies band replacements, e.g. 狐人's raised MP ceiling) are applied on top, in a fixed,
  tested order (see design.md D-5). `Monster` trait baselines are read directly from
  `MonsterTier.static_band`/`hp_band` (see design.md D-6). No formula derives one stat axis from
  another anywhere in this module — every value is a direct lore-registry read. Every stored value
  is a **base** value, pre-skill-multiplier (see design.md D-7): the sample cards' `88*1000`
  notation is base `88` plus a `×1000` skill multiplier, never a stored `88000`, and skill
  multipliers are applied only at resolution time by change 5/9, never baked into `entity.traits`.
- Add `race: str | None` and `subrace: str | None` attributes on `LivingEntity` (see design.md D-3)
  — the lore-registry keys `world/rules/traits.py`'s derivation functions read as input, and
  `import-contract` (change 4) is expected to populate once it validates a character record.
- Add `typeclasses/characters.py::PlayerCharacter(LivingEntity)`, `typeclasses/npcs.py::NPC
  (LivingEntity)`, and `typeclasses/monsters.py::Monster(LivingEntity)` (a new file; §3.2's tree
  doesn't name one — see design.md D-2) with the extra fields §5.2 names, split into what this
  change builds and what it only declares as a seam:
  - `PlayerCharacter`: `guild_rank`, `quest_log`, `wallet` — all declared seams (later: change 16,
    change 15, change 16 respectively).
  - `NPC`: `dialogue_memory`, `schedule` — declared seams (later: change 19, unassigned/TBD).
  - `Monster`: `threat_tier` — built now (a `MonsterTier` key, needed to derive trait baselines);
    `loot_table`, `behaviour_tree` — declared seams (later: change 5, unassigned/TBD).
  - The other six `LivingEntity` handlers named in §5.2 (`sexual`, `buffs`, `equipment`, `skills`,
    `relations`, `persona`) are declared as typed placeholder attributes only, each commented with
    the change that owns building it. Only `traits` is a working handler after this change.
- Add the `disguised_stats` display layer per decision D2: stored as a plain attribute on
  `LivingEntity`, entirely separate from `TraitHandler`, with exactly one sanctioned accessor
  function (`world/rules/traits.py::get_display_value()`) documented for exactly three consumers —
  appearance rendering (`look`), guild registration records, and appraisal items. Combat,
  resolution, and damage read `entity.traits.<key>.value` directly and never call this accessor.
  Add a regression test that scans the deterministic rules modules design doc §3.2 names (most of
  which don't exist yet) for any reference to the accessor or to `disguised_stats`, so the boundary
  starts being enforced the moment a later change creates `combat.py`/`action.py`/etc., rather than
  being enforced only by code review discipline.
- Add test suites: `typeclasses/tests/` (`EvenniaTest`-based, entity creation and subclassing) and
  `world/rules/tests/` (trait-scale derivation, race power-gap propagation, disguise boundary).

## Capabilities

### New Capabilities
- `living-entity-hierarchy`: `LivingEntity` and its three subclasses (`PlayerCharacter`, `NPC`,
  `Monster`), the extra fields §5.2 names for each, and the explicit seam/built split for every
  non-trait handler.
- `entity-trait-scales`: the `TraitHandler` mount, the eight-key trait set with correct trait types,
  and the race-driven (and monster-tier-driven) derivation of initial values from change 2's lore
  registries.
- `disguised-stats-boundary`: the `disguised_stats` storage, the single accessor function, and the
  automated boundary check that combat/resolution/damage never read it.

### Modified Capabilities
- None. `openspec/specs/` is currently empty (changes 1 and 2 have not been archived yet).

## Impact

- **New files**: `typeclasses/entities.py`, `typeclasses/characters.py`, `typeclasses/npcs.py`,
  `typeclasses/monsters.py`, `world/rules/traits.py`, `typeclasses/tests/`, `world/rules/tests/`.
- **Modified files**: none outside this change's new files — `typeclasses/` and `world/rules/`
  currently exist only as empty stub packages from change 1.
- **Depends on**: change 1 (Evennia skeleton, pinned Evennia 6.1.0) and change 2's current,
  corrected shape of `RaceProfile` (`static_baseline`, `STATIC_TIER_REGISTRY`), `Subrace`
  (`static_modifiers`, `vital_overrides`), and `MonsterTier` (`static_band`, `hp_band`).
- **Consumers deferred to later changes**: `import-contract` (4) instantiates these typeclasses
  from validated JSON and populates `persona`/`sexual_baseline`/etc.; `skills-equipment` (5) mounts
  `SkillHandler`/`EquipmentHandler` onto the declared seams and builds `Monster.loot_table`;
  `buffs-rulebook` (6) mounts `BuffHandler`; `sexual-state` (7) mounts `SexualState`;
  `guild-economy` (16) builds `PlayerCharacter.guild_rank`/`wallet` behavior; `npc-dialogue` (19)
  builds `NPC.dialogue_memory`. This change does not implement any of their behavior, only the
  attribute seam each will attach to.
