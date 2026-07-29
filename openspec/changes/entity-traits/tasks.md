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
- [ ] 2.3 Declare `race: str | None` and `subrace: str | None` attributes (both default `None`) per
      design.md D-3 — the lore-registry keys the trait-derivation functions in task 3 read as input.
- [ ] 2.4 Declare the six non-trait handler placeholders (`sexual`, `buffs`, `equipment`, `skills`,
      `relations`, `persona`) as `None`-defaulting attributes per design.md D-10, each with a
      comment naming its owning change (or "unassigned — see design.md Open Questions").
- [ ] 2.5 Declare the `disguised_stats` attribute convention (`entity.db.disguised_stats`,
      `dict[str, int] | None`, default `None`) per design.md D-8. No accessor logic yet — that is
      task 4.

## 3. Race-, subrace-, and tier-driven trait scale derivation (`world/rules/traits.py`)

- [ ] 3.1 Define `race_floor(race: RaceProfile) -> dict[str, int]` per design.md D-4: reads
      `race.vital_baseline.{hp,mp,sp}[0]`, `race.static_baseline.{atk_phys,agility,defense}[0]`,
      and sets `magic_level` to `0` (current value; `race.magic_cap` is the counter's max, not its
      starting value). No formula, ratio, or hardcoded per-race number — every value is a direct
      attribute read from `RaceProfile`. Import `RaceProfile`/`RACE_REGISTRY` from
      `world.lore.races`.
- [ ] 3.2 Define `build_initial_traits(race_key: str, subrace_key: str | None = None, tier: str |
      None = None) -> dict[str, int]` per design.md D-4/D-5: starts from
      `race_floor(RACE_REGISTRY[race_key])`; if `tier` is given, looks up
      `STATIC_TIER_REGISTRY[tier]`, raises `ValueError` if `.race_key` does not match `race_key`
      (see task 3.2a), and otherwise overwrites the `atk_phys`/`agility`/`defense` entries with the
      tier's `.band[0]` (floor) — `hp`/`mp`/`sp`/`magic_level` are unaffected by `tier`; then, if
      `subrace_key` is given, applies `SUBRACE_REGISTRY[subrace_key].static_modifiers` as fractional
      deltas to `atk_phys`/`agility`/`defense` (`value = round(value * (1 + delta))`), then applies
      `SUBRACE_REGISTRY[subrace_key].vital_overrides` (if any) as absolute band-floor replacements —
      in that exact order (race/tier baseline → static_modifiers → vital_overrides). Import
      `SUBRACE_REGISTRY`/`StatModifiers`/`STATIC_TIER_REGISTRY` from `world.lore.races`.
- [ ] 3.2a Implement the tier/race cross-check inside task 3.2: `STATIC_TIER_REGISTRY[tier]` raises
      `KeyError` if `tier` doesn't exist at all; if it exists but its `.race_key` differs from the
      `race_key` argument, raise a `ValueError` naming both the requested tier and the mismatched
      race (e.g. "tier 'human_swordmaster' belongs to race 'human', not 'elf'") — this must fail
      loudly, never silently return a value or fall back to the species floor.
- [ ] 3.3 Define `initial_trait_config(race_key: str, subrace_key: str | None = None, tier: str |
      None = None) -> dict[str, dict]` that wraps `build_initial_traits()`'s output (passing `tier`
      through unchanged) into the kwargs `TraitHandler.add()` needs per trait type (gauge max +
      regen rate for hp/mp/sp; static base + mod=0 for atk_phys/agility/defense; counter base + max
      for magic_level/guild_merit). Confirm the exact `TraitHandler.add()` keyword names against the
      installed Evennia 6.1.0 `evennia.contrib.rpg.traits` source before wiring this up (see
      design.md Open Questions).
- [ ] 3.4 Define `GAUGE_REGEN_RATE_PCT` (a single flat placeholder regen-rate percentage of max,
      applied uniformly across gauges and races — actual tick-driven regen application is change
      11's job; this change only needs a concrete, non-`None` rate for `GaugeTrait` construction).
- [ ] 3.5 Define `_resolve_band_position(band: tuple[int, int | None], position: str) -> int` per
      design.md D-6: `"floor"` returns `band[0]`; `"ceiling"` returns `band[1]` (raising `ValueError`
      if `band[1] is None`); `"mid"` returns `(band[0] + band[1]) // 2` (same `None`-ceiling guard);
      any other `position` raises `ValueError`. No randomness, no distribution — one deterministic
      value per call.
- [ ] 3.6 Define `build_initial_traits_for_monster_tier(tier_key: str, position: str = "floor") ->
      dict[str, int]` per design.md D-6: reads `MONSTER_TIER_REGISTRY[tier_key]`, then uses task
      3.5's `_resolve_band_position()` against `.hp_band` for `hp` and against each of
      `.static_band.{atk_phys,agility,defense}` for the three static traits (all at the same
      `position`), and sets `mp`, `sp`, and `magic_level` to `0` (no monster MP/SP/magic band exists
      in `MonsterTier` — `0` is the non-inventing default, not a fabricated number). Raise a clear
      error (e.g. the natural `KeyError` from the registry lookup) if `tier_key` does not resolve in
      `MONSTER_TIER_REGISTRY`. Then define `initial_trait_config_for_monster_tier(tier_key: str,
      position: str = "floor") -> dict[str, dict]` wrapping it into `TraitHandler.add()` kwargs, the
      same way task 3.3 does for races. No multiplier, ladder, or tier-ordering-derived formula
      anywhere in either function.
- [ ] 3.7 Wire `PlayerCharacter`/`NPC` to a method (e.g. `apply_race_baseline(tier: str | None =
      None)`) that reads `self.race`/`self.subrace`, calls `initial_trait_config(race, subrace,
      tier)`, and populates `entity.traits` from it; wire `Monster` to a method (e.g.
      `apply_monster_tier(position: str = "floor")`) that reads `self.threat_tier` and calls
      `initial_trait_config_for_monster_tier(threat_tier, position)` instead. Document that the
      caller (change 4's import loader, change 9's test fixtures, or a test helper in this change)
      is responsible for setting `race`/`subrace`/`threat_tier` and then explicitly invoking the
      appropriate method with whatever `tier`/`position` it needs, since `at_object_creation()`
      fires before any of these are necessarily known for a generically spawned object (design.md
      D-3).

## 4. Disguised-stats accessor and boundary (`world/rules/traits.py`)

- [ ] 4.1 Implement `get_display_value(entity, trait_key: str) -> int` per design.md D-8: returns
      `entity.db.disguised_stats[trait_key]` when present, else `getattr(entity.traits,
      trait_key).value`. Docstring names the exactly three permitted callers (appearance rendering
      `look`, guild registration records, appraisal items) and states that combat, resolution, and
      damage must never call it.
- [ ] 4.2 Write `world/rules/tests/test_disguise_boundary.py`'s source-scanning regression test per
      design.md D-9: scans `world/rules/combat.py`, `world/rules/action.py`, `world/rules/dice.py`,
      `world/rules/targeting.py` (skipping any that don't exist yet) for the literal strings
      `disguised_stats` and `get_display_value`, failing if either is found.
- [ ] 4.3 Write the positive boundary test: construct a `LivingEntity` with true trait values and a
      `disguised_stats` dict holding different values for a subset of keys; assert
      `get_display_value()` returns the disguised value where set and the true value where absent,
      and assert `entity.traits.<key>.value` equals the true value for every key regardless of what
      `disguised_stats` holds.

## 5. Subclasses (`typeclasses/characters.py`, `npcs.py`, `monsters.py`)

- [ ] 5.1 Define `PlayerCharacter(LivingEntity)` with `guild_rank` (default `None`), `quest_log`
      (default `[]`), `wallet` (default `0`) — all declared seams per design.md D-11, no behavior.
- [ ] 5.2 Define `NPC(LivingEntity)` with `dialogue_memory` (default `None`), `schedule` (default
      `None`) — declared seams per design.md D-11, no behavior.
- [ ] 5.3 Define `Monster(LivingEntity)` with `threat_tier` (a `MonsterTier` key, required — used by
      task 3.6's trait derivation), `loot_table` (default `[]`), `behaviour_tree` (default
      `None`) — the latter two are declared seams per design.md D-11.

## 6. Tests

- [ ] 6.1 `typeclasses/tests/test_entities.py` (`EvenniaTest`-based) — every subclass instantiates
      without error; `LivingEntity`'s component-holder API is present; `race`/`subrace` default to
      `None`; the six non-trait handler placeholders are all `None` on a fresh instance; no
      `SexualState`/`BuffHandler`/`EquipmentHandler`/`SkillHandler`/`RelationHandler`/`PersonaStore`
      class exists anywhere in the codebase added by this change.
- [ ] 6.2 `typeclasses/tests/test_subclasses.py` — `PlayerCharacter` exposes `guild_rank`,
      `quest_log`, `wallet`; `NPC` exposes `dialogue_memory`, `schedule`; `Monster` exposes
      `threat_tier`, `loot_table`, `behaviour_tree`; none of the seam fields has an associated
      state-mutating method.
- [ ] 6.3 `world/rules/tests/test_traits.py` — all eight trait keys present with the correct trait
      type (gauge/static/counter) per requirement; gauge traits have a max and non-`None` rate;
      static traits compute from base+mod; every constructed entity's `atk_phys`/`agility`/
      `defense` base values fall inside the constructing race's `static_baseline` band (elf
      70-95, human 1-22, beastfolk 4-34) — a value outside the band (e.g. in the thousands) fails
      this test, catching both a reintroduced hp-derived ratio and an accidentally-baked-in skill
      multiplier in one assertion.
- [ ] 6.4 `world/rules/tests/test_race_scale.py` — elf `hp` max equals
      `RACE_REGISTRY["elf"].vital_baseline.hp[0]`; human `hp` max equals
      `RACE_REGISTRY["human"].vital_baseline.hp[0]`; elf `magic_level` max equals
      `RACE_REGISTRY["elf"].magic_cap` with current value `0`; elf `hp` max is at least 50x human
      `hp` max; human static trait bases equal `RACE_REGISTRY["human"].static_baseline`'s floor
      values exactly (single digits); elf static trait bases equal
      `RACE_REGISTRY["elf"].static_baseline`'s floor values exactly (NOT a value derived from the
      elf/human HP ratio); the elf static floor compared against `STATIC_TIER_REGISTRY
      ["human_elite"].band` is roughly 8-10x, not roughly 100x; `guild_merit` starts at 0 with no
      maximum.
- [ ] 6.5 `world/rules/tests/test_subrace_order.py` — per design.md D-5: a `catkin` beastfolk
      entity's `agility` base is higher and `defense` base is lower than a `wolfkin` beastfolk
      entity's (both derived from the same beastfolk race floor, adjusted by each subrace's
      `static_modifiers`); a `foxkin` entity's `mp` gauge max equals exactly `50` (the
      `vital_overrides` band floor), not `30` (the unmodified species floor) and not a blended
      value; a subrace with all-zero `static_modifiers` and `vital_overrides=None` (e.g. `fionnen`)
      produces trait values identical to constructing with no subrace at all.
- [ ] 6.6 `world/rules/tests/test_monster_scale.py` — a `calamity`-tier `Monster`'s `atk_phys` base
      equals `MONSTER_TIER_REGISTRY["calamity"].static_band.atk_phys[0]` and `hp` max equals
      `MONSTER_TIER_REGISTRY["calamity"].hp_band[0]` exactly at the default `position="floor"` (not
      a multiplier-derived value); a `calamity`-tier `Monster`'s stats are higher than a `low`-tier
      `Monster`'s, because the registry's own bands differ, not because of an applied formula;
      `mp`/`sp`/`magic_level` are all `0`; constructing a `Monster` with an unknown `threat_tier`
      raises rather than silently defaulting; `position="mid"` and `position="ceiling"` each land at
      `_resolve_band_position()`'s documented value for `MONSTER_TIER_REGISTRY["mid"].hp_band`
      (floor < mid < ceiling, strictly), and an unrecognized `position` string raises `ValueError`.
- [ ] 6.7 `world/rules/tests/test_disguise_boundary.py` — the source-scanning regression test (task
      4.2) and the positive accessor test (task 4.3).
- [ ] 6.8 `world/rules/tests/test_tier_construction.py` — per this change's tier-aware construction
      addition: constructing a human with `tier="human_swordmaster"` lands `atk_phys`/`agility`/
      `defense` inside `18-22` (`STATIC_TIER_REGISTRY["human_swordmaster"].band`); constructing a
      human with `tier="human_commoner"` lands inside `1-5`
      (`STATIC_TIER_REGISTRY["human_commoner"].band`); constructing an elf with
      `tier="human_swordmaster"` raises `ValueError` (cross-race tier request), not a silently
      returned value; omitting `tier` entirely still reproduces today's species-floor behaviour
      unchanged (a regression guard against this addition altering the no-tier path).

## 7. Verification

- [ ] 7.1 Run the full `typeclasses/tests/` and `world/rules/tests/` suites and confirm all tests
      pass.
- [ ] 7.2 Instantiate one `PlayerCharacter`, one `NPC`, and one `Monster` in a live (or
      `EvenniaTest`) session and confirm `entity.traits` resolves all eight keys with sane values
      for a representative race+subrace (elf/`ciaran`, beastfolk/`foxkin`) and monster tier
      (災厄級/`calamity`), with no unhandled exception.
- [ ] 7.3 Confirm no module added by this change contains a hardcoded HP/MP/SP/magic-cap/combat-stat
      number for any specific race or monster tier outside `GAUGE_REGEN_RATE_PCT` and the `0`
      defaults documented in D-4/D-6 for fields `MonsterTier`/`magic_cap` don't cover (grep
      `world/rules/traits.py` by hand as a spot check).
- [ ] 7.4 Confirm `get_display_value` is not referenced anywhere outside `world/rules/traits.py`
      and its own tests at the end of this change (it has no real caller yet — the three consumers
      are built by later changes).
- [ ] 7.5 Confirm no function in `world/rules/traits.py` multiplies a stored trait value by 10, 100,
      or 1000, and that every static trait value this change's derivation functions can produce
      stays within the constructing race's/tier's documented `StaticBand`/`static_band` — per
      design.md D-7, skill multipliers are never baked into `entity.traits`.
