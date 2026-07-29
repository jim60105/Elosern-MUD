## 1. Package layout

- [ ] 1.1 Confirm `typeclasses/` and `world/rules/` exist as empty stub packages from change 1; add
      `typeclasses/tests/__init__.py` and `world/rules/tests/__init__.py`.
- [ ] 1.2 Create `typeclasses/entities.py`, `typeclasses/characters.py`, `typeclasses/npcs.py`,
      `typeclasses/monsters.py` (new file — see design.md D-2), and `world/rules/traits.py` as
      empty modules with module docstrings referencing design doc §5.2 and this change.

## 2. LivingEntity base (`typeclasses/entities.py`)

- [ ] 2.1 Define `LivingEntity(ComponentHolderMixin, DefaultCharacter)` per design.md D-1. Verify,
      against the installed Evennia 6.1.0, that `ComponentHolderMixin`
      (`evennia.contrib.base_systems.components`) and `DefaultCharacter` compose cleanly (no
      metaclass or hook conflict) before proceeding — same verify-before-trusting discipline
      changes 1 and 2 already established for Evennia base-class assumptions.
- [ ] 2.2 Mount `entity.traits` as a `TraitHandler` (`evennia.contrib.rpg.traits`) in
      `at_object_creation()` (or the hook confirmed in task 2.1), with no traits added yet — trait
      population happens in task 3.
- [ ] 2.3 Declare the six non-trait handler placeholders (`sexual`, `buffs`, `equipment`, `skills`,
      `relations`, `persona`) as `None`-defaulting attributes per design.md D-7, each with a
      comment naming its owning change (or "unassigned — see design.md Open Questions").
- [ ] 2.4 Declare the `disguised_stats` attribute convention (`entity.db.disguised_stats`,
      `dict[str, int] | None`, default `None`) per design.md D-5. No accessor logic yet — that is
      task 4.

## 3. Race- and tier-driven trait scale derivation (`world/rules/traits.py`)

- [ ] 3.1 Define `REFERENCE_STATIC_BASELINE = {"atk_phys": 10, "agility": 10, "defense": 10}` and
      `race_scale_factor(race: RaceProfile) -> float` per design.md D-3, importing `RACE_REGISTRY`
      from `world.lore.races`.
- [ ] 3.2 Define `initial_trait_config(race: RaceProfile) -> dict[str, dict]` mapping each of the
      eight trait keys to the kwargs needed to construct it: `hp`/`mp`/`sp` gauge max + regen rate
      from `race.vital_baseline`; `atk_phys`/`agility`/`defense` static base from
      `REFERENCE_STATIC_BASELINE[key] * race_scale_factor(race)`; `magic_level` counter max from
      `race.magic_cap`; `guild_merit` counter with `base=0`, `max=None`. Confirm the exact
      `TraitHandler.add()` keyword names against the installed Evennia 6.1.0
      `evennia.contrib.rpg.traits` source before wiring this up (see design.md Open Questions).
- [ ] 3.3 Define `GAUGE_REGEN_RATE_PCT` (a single flat placeholder regen-rate percentage of max,
      applied uniformly across gauges and races — actual tick-driven regen application is change
      11's job; this change only needs a concrete, non-`None` rate for `GaugeTrait` construction).
- [ ] 3.4 Define `MONSTER_TIER_SCALE = {"low": 1, "mid": 10, "high": 100, "calamity": 1000}` (keyed
      to `MonsterTier`'s F-E/D-C/B-A/災厄級 ordering) and
      `initial_trait_config_for_monster_tier(tier_key: str) -> dict[str, dict]` per design.md D-4,
      applying the multiplier to the same human reference baseline `initial_trait_config` uses.
      Raise a clear error if `tier_key` does not resolve in `MONSTER_TIER_REGISTRY`.
- [ ] 3.5 Wire `PlayerCharacter`/`NPC` creation to call `initial_trait_config(race)` (given a race
      key already set on the entity) and populate `entity.traits` from it; wire `Monster` creation
      to call `initial_trait_config_for_monster_tier(threat_tier)` instead. Document that the
      caller (change 4's import loader, or a test helper in this change) is responsible for setting
      race/`threat_tier` before trait population runs, since `at_object_creation()` fires before
      either is necessarily known for a generically spawned object.

## 4. Disguised-stats accessor and boundary (`world/rules/traits.py`)

- [ ] 4.1 Implement `get_display_value(entity, trait_key: str) -> int` per design.md D-5: returns
      `entity.db.disguised_stats[trait_key]` when present, else `getattr(entity.traits,
      trait_key).value`. Docstring names the exactly three permitted callers (appearance rendering
      `look`, guild registration records, appraisal items) and states that combat, resolution, and
      damage must never call it.
- [ ] 4.2 Write `world/rules/tests/test_disguise_boundary.py`'s source-scanning regression test per
      design.md D-6: scans `world/rules/combat.py`, `world/rules/action.py`, `world/rules/dice.py`,
      `world/rules/targeting.py` (skipping any that don't exist yet) for the literal strings
      `disguised_stats` and `get_display_value`, failing if either is found.
- [ ] 4.3 Write the positive boundary test: construct a `LivingEntity` with true trait values and a
      `disguised_stats` dict holding different values for a subset of keys; assert
      `get_display_value()` returns the disguised value where set and the true value where absent,
      and assert `entity.traits.<key>.value` equals the true value for every key regardless of what
      `disguised_stats` holds.

## 5. Subclasses (`typeclasses/characters.py`, `npcs.py`, `monsters.py`)

- [ ] 5.1 Define `PlayerCharacter(LivingEntity)` with `guild_rank` (default `None`), `quest_log`
      (default `[]`), `wallet` (default `0`) — all declared seams per design.md D-8, no behavior.
- [ ] 5.2 Define `NPC(LivingEntity)` with `dialogue_memory` (default `None`), `schedule` (default
      `None`) — declared seams per design.md D-8, no behavior.
- [ ] 5.3 Define `Monster(LivingEntity)` with `threat_tier` (a `MonsterTier` key, required — used by
      task 3.5's trait derivation), `loot_table` (default `[]`), `behaviour_tree` (default `None`)
      — the latter two are declared seams per design.md D-8.

## 6. Tests

- [ ] 6.1 `typeclasses/tests/test_entities.py` (`EvenniaTest`-based) — every subclass instantiates
      without error; `LivingEntity`'s component-holder API is present; the six non-trait handler
      placeholders are all `None` on a fresh instance; no `SexualState`/`BuffHandler`/
      `EquipmentHandler`/`SkillHandler`/`RelationHandler`/`PersonaStore` class exists anywhere in
      the codebase added by this change.
- [ ] 6.2 `typeclasses/tests/test_subclasses.py` — `PlayerCharacter` exposes `guild_rank`,
      `quest_log`, `wallet`; `NPC` exposes `dialogue_memory`, `schedule`; `Monster` exposes
      `threat_tier`, `loot_table`, `behaviour_tree`; none of the seam fields has an associated
      state-mutating method.
- [ ] 6.3 `world/rules/tests/test_traits.py` — all eight trait keys present with the correct trait
      type (gauge/static/counter) per requirement; gauge traits have a max and non-`None` rate;
      static traits compute from base+mod.
- [ ] 6.4 `world/rules/tests/test_race_scale.py` — elf `hp` max equals
      `RACE_REGISTRY["elf"].vital_baseline.hp[0]`; human `hp` max equals
      `RACE_REGISTRY["human"].vital_baseline.hp[0]`; elf `magic_level` max equals
      `RACE_REGISTRY["elf"].magic_cap`; elf `hp` max is at least 50x human `hp` max (mirrors change
      2's own race power-gap assertion, propagated to the entity level); human static trait bases
      equal `REFERENCE_STATIC_BASELINE` exactly; elf static trait bases scale by the same ratio as
      elf vs. human `vital_baseline.hp[0]`; `guild_merit` starts at 0 with no maximum.
- [ ] 6.5 `world/rules/tests/test_monster_scale.py` — a 災厄級-tier `Monster`'s trait values are at
      least 10x a F-E-tier `Monster`'s for the same trait; constructing a `Monster` with an unknown
      `threat_tier` raises rather than silently defaulting.
- [ ] 6.6 `world/rules/tests/test_disguise_boundary.py` — the source-scanning regression test (task
      4.2) and the positive accessor test (task 4.3).

## 7. Verification

- [ ] 7.1 Run the full `typeclasses/tests/` and `world/rules/tests/` suites and confirm all tests
      pass.
- [ ] 7.2 Instantiate one `PlayerCharacter`, one `NPC`, and one `Monster` in a live (or
      `EvenniaTest`) session and confirm `entity.traits` resolves all eight keys with sane values
      for a representative race (elf) and monster tier (災厄級), with no unhandled exception.
- [ ] 7.3 Confirm no module added by this change contains a hardcoded HP/MP/SP/magic-cap/combat-stat
      number for any specific race or monster tier outside `REFERENCE_STATIC_BASELINE`,
      `GAUGE_REGEN_RATE_PCT`, and `MONSTER_TIER_SCALE` (grep `world/rules/traits.py` by hand as a
      spot check).
- [ ] 7.4 Confirm `get_display_value` is not referenced anywhere outside `world/rules/traits.py`
      and its own tests at the end of this change (it has no real caller yet — the three consumers
      are built by later changes).
