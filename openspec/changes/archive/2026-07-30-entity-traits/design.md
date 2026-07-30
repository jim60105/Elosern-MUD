## Context

This is roadmap item #3 (design doc §11), depending on change 1 (`bootstrap-container-evennia`,
which provides the running Evennia 6.1.0 project and the empty `typeclasses/`/`world/rules/` stub
packages) and change 2 (`lore-world-data`, which provides `RaceProfile`, `Subrace`, `MonsterTier`,
and the other frozen-dataclass registries in `world/lore/`). No code exists yet for this change's
scope — `typeclasses/` and `world/rules/` are currently empty packages.

Design doc §5.2 sketches `LivingEntity` as a diagram with seven handlers (`traits`, `sexual`,
`buffs`, `equipment`, `skills`, `relations`, `persona`) and three subclasses
(`PlayerCharacter`/`NPC`/`Monster`) each with extra fields. This change's job is narrow: build the
`traits` handler and the class hierarchy it sits on, and declare — but not implement — every other
handler and non-trait field, so later changes (5, 6, 7, 15, 16, 19) have a stable seam to attach to
instead of having to modify the base class shape when their turn comes.

**Correction round 1.** The first draft of this design computed two derived values —
`atk_phys`/`agility`/`defense` static-trait bases from a hardcoded human reference scaled by the
elf/human HP ratio, and monster trait baselines from an invented `10⁰`–`10³` decade ladder keyed to
`MonsterTier` ordering — because at the time, `RaceProfile` and `MonsterTier` carried no numeric
data for those axes. Change 2 has since been corrected to carry that data directly
(`RaceProfile.static_baseline`, `STATIC_TIER_REGISTRY`, `Subrace.static_modifiers`/
`vital_overrides`, `MonsterTier.static_band`/`hp_band`), all derived from `world_info.md` rather
than invented. This design was rewritten to read those fields directly instead of computing a
ratio — see D-4, D-5, and D-6 below.

**Correction round 2.** Round 1 still left `STATIC_TIER_REGISTRY` and every position within a
`MonsterTier`'s band unreachable — every entity landed at its species/tier *floor* unconditionally,
with tier-aware construction flagged as an open question for change 4. That was itself an unowned
seam of exactly the kind that produced round 1's invented formulas: change 9 (`dice-combat`) will
need to construct a mid-tier opponent to write repeatable combat tests against, and leaving that
unowned invites someone downstream to invent their own scale rather than read
`STATIC_TIER_REGISTRY`/`MonsterTier.static_band` as intended. D-4 and D-6 below now give
`build_initial_traits()` an optional `tier` parameter and
`build_initial_traits_for_monster_tier()` an optional `position` parameter, both still direct,
deterministic lore reads — no randomization, stat-point allocation, or level-up curve.

Design doc §4 (the Contrib Reuse Matrix) remains verified against the installed Evennia 6.1.0 and
is authoritative for every module path and class name this design cites; nothing about §4 changed
in either correction round.

## Goals / Non-Goals

**Goals:**
- `typeclasses/entities.py::LivingEntity` — the shared base for characters, NPCs, and monsters,
  mounting `TraitHandler` (`evennia.contrib.rpg.traits`) with the setting's eight-key trait set and
  `ComponentHolderMixin` (`evennia.contrib.base_systems.components`) per §4's assignment of that
  contrib to this exact module.
- `PlayerCharacter`, `NPC`, `Monster` subclasses with the extra fields §5.2 names, each field
  explicitly marked as either built now (trait/stat surface) or a declared seam for a later change.
- Every trait's initial value read directly from change 2's lore registries
  (`RaceProfile.vital_baseline`/`static_baseline`/`magic_cap` for `PlayerCharacter`/`NPC`;
  `MonsterTier.static_band`/`hp_band` for `Monster`) — no derived ratio, no hardcoded per-race or
  per-tier number anywhere in this change's code.
- Optional, explicit tier-aware construction: a caller may name a `STATIC_TIER_REGISTRY` tier (for
  `PlayerCharacter`/`NPC`) or a band position (for `Monster`) to land inside a specific named power
  band instead of the species/tier floor — still a single deterministic value per call, validated
  against the entity's race where applicable.
- `Subrace.static_modifiers` and `Subrace.vital_overrides` applied in a fixed, tested order on top
  of the race baseline.
- An explicit boundary: every trait value this change stores or derives is a **base** value,
  pre-skill-multiplier — skill multipliers are never baked into `entity.traits`.
- The `disguised_stats` display layer (D2): storage separate from `TraitHandler`, one sanctioned
  accessor, and an automated, testable boundary so combat/resolution/damage cannot silently start
  reading it.

**Non-Goals:**
- No `SexualState`, `BuffHandler`, `SkillHandler`, `EquipmentHandler`, `RelationHandler`, or
  `PersonaStore` implementation — changes 5, 6, and 7 own these, plus whichever later change ends up
  owning `relations`/`persona` (see Open Questions). This change declares each as a typed
  placeholder attribute, not a working handler.
- No quest log, dialogue memory, loot table, or behaviour tree implementation — declared seams only,
  per the task framing.
- No `ActionResolver`, targeting, combat formulas, or damage resolution (changes 8–10) — this change
  only guarantees that whatever those changes build will read `entity.traits.<key>.value`, never
  `disguised_stats`.
- No skill-multiplier application. §5.3's corrected import example and the sample character cards
  both make clear that a stat like `88*1000` is a base value (`88`) plus a skill-supplied multiplier
  (`×1000`), never a stored `88000`. Applying that multiplier at resolution time is change 5's
  (skill effects) and change 9's (combat math) job; this change only guarantees `entity.traits`
  never holds an already-multiplied value.
- No randomization, stat-point allocation, or level-up curve for tier-aware construction (D-4/D-6).
  A caller names one tier (or, for monsters, one band position) and gets one deterministic value;
  rolling a specific individual within a tier, or a progression system that moves an entity between
  tiers over time, belongs to a later change (skills-equipment/progression, or whichever change
  eventually owns character advancement).
- No import schema, validation CLI, or loader (change 4) — this change only provides the typeclasses
  change 4 will instantiate into, plus the `race`/`subrace` attributes it will populate.
- No guild-rank progression, quest-log population, or wallet earn/spend logic (changes 15, 16, 19) —
  fields exist as seams; behavior is out of scope.
- No backward-compatibility, migration, or deprecation handling — the project is unreleased with
  zero users, and `typeclasses/`/`world/rules/` currently contain no code beyond change 1's empty
  stubs.

## Decisions

### D-1. `LivingEntity(ComponentHolderMixin, ObjectParent, DefaultCharacter)`.

Design doc §4's row for `typeclasses/entities.py` names `evennia.contrib.base_systems.components` —
`Component`, `ComponentHolderMixin`, `ComponentProperty` — with the note that `QuestGiver` /
`Merchant` / `GuildStaff` are project-authored `Component` subclasses attaching to whatever this
module defines. Mixing `ComponentHolderMixin` into `LivingEntity` now means those later,
role-specific components (owned by quest-runtime/guild-economy, changes 15–16) can attach to any
`LivingEntity` without a base-class change when their turn comes — this change adds the mixin and
nothing else; no `Component` subclass is authored here.

`DefaultCharacter` (not `DefaultObject`) is chosen as the other base because §4's `ai/npc_dialogue.py`
row already commits to `LLMNPC(DefaultCharacter)` (change 19) as an `NPC` subclass's eventual mixin
target, and Evennia's own convention is that anything which acts, is looked at, and can be attacked
— including non-puppeted NPCs and monsters — is typically a `DefaultCharacter` subclass, not a bare
`DefaultObject`. **Flagged for implementer verification**, matching the caution already established
by changes 1 and 2 for any Evennia base-class or hook assumption: confirm `DefaultCharacter`'s
`at_object_creation()` signature and any player-puppet-only behavior that would need suppressing for
`NPC`/`Monster` instances, against the installed Evennia 6.1.0, before wiring this in.

**Alternative considered**: `DefaultObject` directly, avoiding any puppet-related machinery
monsters/NPCs don't need. Rejected because it would diverge from the `LLMNPC(DefaultCharacter)` base
§4 already commits a later change to, forcing an awkward multiple-inheritance reconciliation in
change 19 instead of a clean subclass.

The generated project already routes all located typeclasses through its empty `ObjectParent`
mixin so future common hooks can be added once. `LivingEntity` retains that seam between
`ComponentHolderMixin` and `DefaultCharacter`; the installed Evennia 6.1.0 MRO and lifecycle hooks
are covered by the integration tests.

### D-2. `Monster` gets its own file, `typeclasses/monsters.py` — a small, judgment-call extension
to design doc §3.2's tree.

§3.2 names `typeclasses/characters.py` (`PlayerCharacter`) and `typeclasses/npcs.py`
(`NPC`/`LLMNPC`) but no file for `Monster`, even though §5.2 clearly wants a `Monster(LivingEntity)`
class. Folding `Monster` into `npcs.py` would conflate two conceptually different subclasses (one
dialogue/schedule-driven, one threat-tier/loot-driven) in one file for no reason. **Judgment call**:
add `typeclasses/monsters.py`, mirroring the one-subclass-per-file pattern the other two files
already establish. If this is wrong, it is a one-file move, not a redesign — flagged here the same
way change 1 flagged its own directory-naming judgment call (D-4 in that change's design.md).

### D-3. `LivingEntity` gains `race: str | None` and `subrace: str | None` attributes.

This correction surfaced a gap in the first draft: `build_initial_traits()` (D-4/D-5) needs a race
key and, optionally, a subrace key as inputs, but the original design never specified where an
entity itself stores which race/subrace it has — it only ever passed a `RaceProfile` object into a
derivation function. `LivingEntity` gains two `None`-defaulting attributes, `race` and `subrace`,
holding the lore-registry keys (`RACE_REGISTRY`/`SUBRACE_REGISTRY`). `Monster` does not use these —
it is driven by `threat_tier` instead (D-6) — but they live on `LivingEntity` rather than only on
`PlayerCharacter`/`NPC`, since both subclasses need them identically and a shared base attribute
avoids duplicating the field declaration.

Setting `race`/`subrace` and triggering trait construction from them is a two-step, explicit
operation (`entity.race = "elf"; entity.apply_race_baseline()`), not something `at_object_creation()`
does automatically — a generically spawned object doesn't know its race yet, and forcing the hook to
guess would reintroduce exactly the kind of invented default this correction round removed
elsewhere. `import-contract` (change 4) is expected to be the primary caller of
`apply_race_baseline()` once it has validated `race`/`subrace` against the lore registries; this
change's own tests call it directly as a test helper.

### D-4. Race-driven initial trait values are direct reads of `RaceProfile.vital_baseline`,
`static_baseline`, and `magic_cap` — no derived scale factor.

**What this replaces.** The first draft computed `atk_phys`/`agility`/`defense` bases by scaling a
hardcoded human reference constant (`REFERENCE_STATIC_BASELINE = {"atk_phys": 10, ...}`) by
`race.vital_baseline.hp[0] / human.vital_baseline.hp[0]` — a ~100× ratio for elf. This was
mathematically invalid: change 2's `RaceProfile` (corrected after this change's first draft) shows
that vital pools (hp/mp/sp) and static combat stats (atk_phys/agility/defense) scale by
**independently documented, different** factors between races — vitals ~100× human→elf, statics
only ~10× (`world_info.md`: 「身體素質為人類精銳戰士的10倍」). The removed formula would have given
every elf a 100× physical-stat multiplier instead of the correct ~10×, and separately assumed human
physical stats sit in the tens, when the source's own sample cards put them in single digits
(Lidzia, an elite retainer, is atk_phys/agility/defense 8/9/7 — nowhere near the 60-90 range an
earlier version of this brief mistakenly assumed).

`RaceProfile` now carries `static_baseline: StaticBand` (species-wide floor-to-ceiling band for
`atk_phys`/`agility`/`defense`, shared across the three axes) alongside `vital_baseline`, so no
formula is needed — every trait's initial value is a direct attribute read:

```python
def race_floor(race: RaceProfile) -> dict[str, int]:
    """Species-wide floor for every trait this change mounts, read directly
    from RaceProfile -- no derived ratio anywhere in this function."""
    return {
        "hp": race.vital_baseline.hp[0],
        "mp": race.vital_baseline.mp[0],
        "sp": race.vital_baseline.sp[0],
        "atk_phys": race.static_baseline.atk_phys[0],
        "agility": race.static_baseline.agility[0],
        "defense": race.static_baseline.defense[0],
        "magic_level": 0,   # counter *current* value starts at 0; race.magic_cap is the *max*
    }
```

The species **floor** (`[0]`) is used as the starting point for both vitals and statics — the same
convention the first draft already used for gauge maxes, now applied uniformly instead of being
mixed with a computed ratio for statics. The species ceiling (e.g., human
`static_baseline.atk_phys[1] == 22`, the 大劍豪/S-rank value) represents a rare individual, not a
freshly constructed entity's default; `magic_cap` remains the counter's *maximum*, not its starting
value — a new character starts at `magic_level` 0 and progresses toward the race's cap.

**`STATIC_TIER_REGISTRY` is read when a caller explicitly asks for a tier — never as an implicit
default.** Change 2 also added `STATIC_TIER_REGISTRY` (named power bands within each race's
`static_baseline`, e.g. `human_adventurer`, `elf_prodigy`), which is a genuine gap-closer: without
it, every entity this change constructs sits at its species floor forever, which makes the registry
decorative until some far-later change reads it, and leaves change 9 (`dice-combat`) with no way to
construct a mid-tier opponent to write combat tests against. `build_initial_traits()` therefore
takes an optional `tier` parameter (see below) — when omitted, behavior is unchanged (species
floor); when supplied, the named tier's band supplies the static values instead. This is still a
direct lore read, not an invented default: the caller names the tier, `STATIC_TIER_REGISTRY`
supplies the number, and no policy for "which tier does a role-unknown entity get" is invented
anywhere in this module.

```python
def build_initial_traits(
    race_key: str,
    subrace_key: str | None = None,
    tier: str | None = None,
) -> dict[str, int]:
    """Order: (1) race baseline OR named tier band, (2) subrace
    static_modifiers, (3) subrace vital_overrides. See below for how `tier`
    substitutes into step 1, and D-5 for steps 2-3."""
    race = RACE_REGISTRY[race_key]
    values = race_floor(race)                                # (1) race baseline

    if tier is not None:
        static_tier = STATIC_TIER_REGISTRY[tier]              # KeyError if tier doesn't exist
        if static_tier.race_key != race_key:
            raise ValueError(
                f"tier {tier!r} belongs to race {static_tier.race_key!r}, not {race_key!r}"
            )
        tier_floor = static_tier.band[0]
        values["atk_phys"] = tier_floor
        values["agility"] = tier_floor
        values["defense"] = tier_floor

    # ... steps (2)-(3), unchanged from D-5 below, follow here.
    return values
```

`tier` only ever replaces the *static* three axes' starting point (`atk_phys`/`agility`/`defense`)
— `hp`/`mp`/`sp`/`magic_level` still come from `race_floor()` unconditionally, since
`STATIC_TIER_REGISTRY` (per its own name and change 2's D-2c) is a static-combat-stat concept only,
with no vital or magic dimension. **Cross-race requests fail loudly, not silently**: every
`StaticTier` carries its own `race_key` (change 2's D-2c), so asking for `human_swordmaster` on an
elf raises a `ValueError` naming the mismatch, rather than either ignoring the request or returning
a human-scale value on an elf entity. A test (task 6.8) asserts this raises. No randomization, stat
point allocation, level-up curve, or per-individual variance is introduced — a caller asks for one
named tier and gets one deterministic value (the tier band's floor), the same category of
determinism `race_floor()` already provides; anything richer (rolling a specific individual within
a tier, level-up progression) belongs to a later change.

**No hardcoded per-race number remains anywhere in `world/rules/traits.py`** — every value
`race_floor()` and the `tier`-substitution branch above produces is a direct attribute read from
`RaceProfile`/`STATIC_TIER_REGISTRY`.

### D-5. `Subrace.static_modifiers` and `Subrace.vital_overrides` apply in a fixed, tested order:
race baseline → `static_modifiers` → `vital_overrides`.

Change 2's `Subrace` now carries `static_modifiers: StatModifiers` (three fractional deltas over
`atk_phys`/`agility`/`defense`, always summing to `0.0` per beastfolk subspecies) and
`vital_overrides: dict[str, tuple[int, int]] | None` (currently only `foxkin`, raising the MP band
to `(50, 70)` against the species `(30, 50)`). Both must be applied when a `PlayerCharacter` or `NPC`
has a subrace, and the order matters: `static_modifiers` are *relative* deltas computed against the
race baseline, while `vital_overrides` is an *absolute replacement* of one gauge's band — applying
them in the wrong order, or blending an override with the baseline instead of replacing it, would
corrupt one or the other.

Continuing `build_initial_traits()` from D-4's snippet (steps (2) and (3), appended after the
`tier`-substitution block and before `return values`):

```python
    if subrace_key is not None:
        subrace = SUBRACE_REGISTRY[subrace_key]
        for axis in ("atk_phys", "agility", "defense"):          # (2) static_modifiers
            delta = getattr(subrace.static_modifiers, axis)
            values[axis] = round(values[axis] * (1 + delta))
        if subrace.vital_overrides:                               # (3) vital_overrides
            for stat_key, band in subrace.vital_overrides.items():
                values[stat_key] = band[0]

    return values
```

**Why this order and not another**: `static_modifiers` is meaningless without a baseline to apply a
percentage delta to, so it must come after step 1 (which is now "race floor, optionally overridden
by a named tier's floor" per D-4, but is still resolved before any subrace adjustment is applied).
`vital_overrides` *replaces* `RaceProfile.vital_baseline` outright for the named stat (change 2's
D-3: `vital_overrides=None` means "use `RaceProfile.vital_baseline` unmodified") — it is not a delta
and has nothing to do with `static_modifiers`' axes (`atk_phys`/`agility`/`defense` vs. `mp`), so its
position relative to step 2 does not change the arithmetic result, but it is placed last so the
function reads as one direction — baseline (or tier), then adjust the static axes, then apply any
full override — with no step depending on a later one. A test (task 6.5) constructs a `foxkin`
entity and asserts the final `mp` gauge max is exactly `50` (the override's floor), not a value
derived from `vital_baseline.mp[0]` (`30`) or blended with it — proving the override wins outright
rather than being averaged with the baseline.

### D-6. Monster trait baselines read `MonsterTier.static_band` and `.hp_band` directly — no
derived multiplier.

**What this replaces.** The first draft, finding `MonsterTier` carried no numeric fields at the
time, invented a `MONSTER_TIER_SCALE` decade ladder (`10⁰`–`10³`) keyed to tier ordering. Change 2
has since added `static_band: StaticBand` and `hp_band: tuple[int, int]` to `MonsterTier`, derived
from `world_info.md`'s own guild-rank correspondence (F-E inside `human_adventurer`, D-C exceeding
`human_elite`, B-A at or above `human_swordmaster`, 災厄級 above `elf_common`). The invented ladder
is removed entirely; this change reads the two bands directly:

```python
def _resolve_band_position(band: tuple[int, int | None], position: str) -> int:
    """Deterministic position within a closed band -- no distribution, no
    randomness. `position` is one of "floor" / "mid" / "ceiling"."""
    floor, ceiling = band
    if position == "floor":
        return floor
    if ceiling is None:
        raise ValueError(f"position {position!r} requires a closed band; {band!r} is open-ended")
    if position == "ceiling":
        return ceiling
    if position == "mid":
        return (floor + ceiling) // 2
    raise ValueError(f"unknown position {position!r}")

def build_initial_traits_for_monster_tier(tier_key: str, position: str = "floor") -> dict[str, int]:
    """Reads MonsterTier's own static_band/hp_band directly -- no ladder,
    no formula. `position` selects where within the tier's band to land
    ("floor" default, "mid", or "ceiling") -- still a single deterministic
    value per call, not a distribution. Raises KeyError if tier_key doesn't
    resolve in MONSTER_TIER_REGISTRY, so a Monster can never be constructed
    with a silently-defaulted trait scale."""
    tier = MONSTER_TIER_REGISTRY[tier_key]
    static_value_getter = lambda band: _resolve_band_position(band, position)
    return {
        "hp": _resolve_band_position(tier.hp_band, position),
        "mp": 0,   # world_info.md documents no monster MP/SP band (change 2's
        "sp": 0,   # own Non-Goals: "MonsterTier carries exactly the two numeric
                   # bands world_info.md specifies -- physical stats, HP"); 0 is
                   # the non-inventing default, not a fabricated number
        "atk_phys": static_value_getter(tier.static_band.atk_phys),
        "agility": static_value_getter(tier.static_band.agility),
        "defense": static_value_getter(tier.static_band.defense),
        "magic_level": 0,
    }
```

Every one of change 2's four `MonsterTier` bands (`hp_band` and all three `static_band` axes) is
fully closed (no `None` ceiling), so `position="mid"`/`"ceiling"` always resolves in practice today;
`_resolve_band_position()` still guards the open-ended case for robustness rather than assuming it
can never happen. `position` is a caller-chosen discrete selector, not a random roll or a stat-point
budget — change 9 (`dice-combat`) can now construct, say, a `mid`-tier monster at `position="mid"`
to write a repeatable combat test against, without this change inventing anything beyond "which of
three fixed points in an already-documented band."

`magic_level`'s counter *maximum* for a `Monster` is likewise `0` rather than reading any race's
`magic_cap`, which doesn't apply to monsters — consistent with change 2's own scope boundary that
bestiary magic/resistances are not part of what `MonsterTier` specifies. `guild_merit` stays at the
same `base=0`, `max=None` every `LivingEntity` gets; monsters are not guild members, but the field
still exists uniformly since it is part of the shared eight-key trait set every `LivingEntity`
mounts. `Monster.threat_tier` (a `MonsterTier` key) remains built, not a declared seam, per the
original design — it is what this function needs to resolve a `Monster`'s trait scale.

### D-7. Stored trait values are BASE values; skill multipliers are never baked into `entity.traits`.

Design doc §5.3's import example (`atk_phys: 88000`) has been corrected: the notation `88*1000` on
the source character cards means a **base** value of `88` with a `×1000` multiplier supplied by a
*skill* the character has (身體超強化), not a stored value of `88000`. Change 2's D-2b already
states this boundary on the lore-registry side ("skill multipliers ... are a third, independent
layer applied at resolution time and are never baked into `static_baseline` or any stored stat");
this change carries the identical boundary onto the entity/runtime side.

**Consequence for `world/rules/traits.py`**: every value `build_initial_traits()` /
`build_initial_traits_for_monster_tier()` produces, and every value `TraitHandler` stores for
`atk_phys`/`agility`/`defense`, is a **base** value in the same single/double/(elf) low-hundreds
range `StaticBand`/`StaticTier`/`MonsterTier.static_band` document — never a value with a skill
multiplier already applied. `StaticTrait`'s `mod` component is reserved for **additive** modifiers
from `BuffHandler` (change 6) — e.g. a poison debuff subtracting from `defense` — not for
multiplicative skill effects. Multiplicative skill multipliers (×10 for a partial effect, ×100 for
身體強化, ×1000 for 身體超強化) are **never** written into `entity.traits` at all; they are applied
at resolution time by whichever module computes effective combat power (change 5's skill-effect
resolution and/or change 9's combat math), reading `entity.traits.<key>.value` as an input and
producing a separate, transient effective value for that one calculation.

This change adds regression tests (tasks 6.3 and 7.5) asserting that each pre-subrace static
baseline stays inside the exact `StaticBand`/`static_band` range and each post-subrace result equals
its documented fractional adjustment. A subrace modifier may legitimately cross the original band
edge and is not clamped; a value in the tens of thousands (i.e., a baked-in skill multiplier) still
fails immediately because it cannot equal that documented adjustment.

**Alternative considered**: storing the skill-multiplied "effective" value directly in
`entity.traits` and letting combat read it as-is. Rejected — this is exactly the error this
correction fixed, and it would make `entity.traits.atk_phys.value` ambiguous (base, or already
skill-boosted?) for every future reader, including the disguise layer (D-8/D-9), which would then
need to know whether the value it compares against is base or multiplied.

### D-8. `disguised_stats` lives in `world/rules/traits.py`, not a separate module.

Design doc §3.2's `world/rules/` tree names `traits · sexual_state · buffs · progression` — no
dedicated "disguise" module. Since `disguised_stats` is, per D2, "a pure display layer" tightly
coupled to the same trait keys `traits.py` already defines, adding a new unlisted module for roughly
thirty lines of accessor code would be scope creep against §3.2's tree. **Decision**: the storage
convention (a plain `db.disguised_stats: dict[str, int] | None` attribute on `LivingEntity`) and the
one sanctioned accessor live in `world/rules/traits.py` alongside the trait-scale derivation code.

```python
def get_display_value(entity, trait_key: str) -> int:
    """The ONLY sanctioned way to read a possibly-disguised stat value.

    Permitted callers (per design doc D2): appearance rendering (`look`),
    guild registration records, and appraisal items — nothing else.
    Combat, resolution, and damage MUST read entity.traits.<key>.value
    directly and MUST NEVER call this function.
    """
    disguised = entity.db.disguised_stats or {}
    if trait_key in disguised:
        return disguised[trait_key]
    return getattr(entity.traits, trait_key).value
```

True-trait reads never consult `disguised_stats` — `entity.traits.atk_phys.value` is computed
entirely from `TraitHandler` state and is structurally incapable of seeing the disguise dict, since
the two live in unrelated attributes with no code path between them. Both the true and disguised
values are base values per D-7 — e.g. Yuka's true `atk_phys` base is `88` (within the `elf_common`
`static_baseline` band of 70-95) with `disguised_stats["atk_phys"] = 60` (below that band, so she
reads as noticeably weaker than a typical elf while disguised).

### D-9. The disguise boundary is enforced by a source-scanning regression test, not a new
import-linter dependency.

The task asks that the combat/resolution/damage-never-reads-disguised-stats boundary be "testable."
Design doc §3.1 mentions an import-linter contract for the AI/rules boundary, but that contract does
not exist in the repository yet (change 1 did not add one), and introducing a new dependency and
CI wiring for a single-module boundary is disproportionate to a one-day change. **Decision**: a
plain Python test that scans the deterministic-core module paths design doc §3.2 names for combat
and resolution — `world/rules/combat.py`, `world/rules/action.py`, `world/rules/dice.py`,
`world/rules/targeting.py` — none of which exist yet — for the literal strings `disguised_stats` and
`get_display_value`:

```python
FORBIDDEN_MODULES = [
    "world/rules/combat.py",
    "world/rules/action.py",
    "world/rules/dice.py",
    "world/rules/targeting.py",
]

def test_no_forbidden_module_reads_disguised_stats():
    for path in FORBIDDEN_MODULES:
        if not os.path.exists(path):
            continue  # not built yet; this test starts enforcing the moment it is
        source = pathlib.Path(path).read_text()
        assert "disguised_stats" not in source
        assert "get_display_value" not in source
```

This is deliberately a tripwire, mirroring change 1's D-7 rationale for its contrib-matrix
regression check ("intentionally dumb... but it is the cheapest possible protection"): most of the
scanned files don't exist yet, so the test is a no-op today, but the moment change 8/9 create
`action.py`/`combat.py`, any accidental `get_display_value` call starts failing this test
immediately instead of being caught only by code review. A second, positive test exercises D2
directly: construct a `LivingEntity` with true traits and `disguised_stats` set to different values
for the same keys, and assert (a) `get_display_value()` returns the disguised value for keys present
in the dict and the true value for keys absent, and (b) `entity.traits.<key>.value` equals the true
value regardless of what `disguised_stats` holds.

**Alternative considered**: An `import-linter` "forbidden contract." Rejected for this change's
scope — it would require adding a new dependency and a `.importlinter` config for a boundary that
today has zero real modules to check against; the source-scan test achieves the same tripwire
property with no new dependency, and is trivial to replace with a proper import-linter contract
later once `world/rules/combat.py` etc. actually exist (flagged as an open question).

### D-10. Non-trait `LivingEntity` handlers are declared as typed placeholder attributes with an
owning-change comment, not stub classes.

`sexual`, `buffs`, `equipment`, `skills`, `relations`, `persona` are named in §5.2's diagram but out
of this change's scope. Rather than authoring empty handler *classes* (which would invite later
changes to subclass or extend something this change never validated), each is declared as a plain
`None`-defaulting `AttributeProperty` (or equivalent) directly on `LivingEntity`, with a comment
naming the change that will replace it with a real handler:

```python
# Non-trait handlers — declared seams only, per design doc §5.2. Each is a
# plain placeholder attribute until its owning change replaces it with a
# real handler mounted the same way `traits` is mounted above.
sexual = AttributeProperty(default=None)      # change 7 (sexual-state)
buffs = AttributeProperty(default=None)       # change 6 (buffs-rulebook)
equipment = AttributeProperty(default=None)   # change 5 (skills-equipment)
skills = AttributeProperty(default=None)      # change 5 (skills-equipment)
relations = AttributeProperty(default=None)   # unassigned — see Open Questions
persona = AttributeProperty(default=None)     # likely change 4 (import-contract) — see Open Questions
```

This keeps the seam visible (the attribute exists, `hasattr(entity, "sexual")` is `True`) without
this change guessing at an API surface (`SexualState`'s field shape, `BuffHandler`'s mount pattern)
that its owning change hasn't designed yet.

### D-11. Subclass extra fields: built vs. declared-seam split.

| Class | Field | Status | Rationale |
|---|---|---|---|
| `PlayerCharacter` | `guild_rank` | seam (`None`) | Progression logic is change 16's; the field would need game-design input (does everyone start unranked, or at F?) this change shouldn't make. |
| `PlayerCharacter` | `quest_log` | seam (`[]`) | Explicitly named in the task as deferred. |
| `PlayerCharacter` | `wallet` | seam (`0`) | Earn/spend logic and starting-copper balance are change 16's economic decisions, not this change's. |
| `NPC` | `dialogue_memory` | seam (`None`) | Explicitly named in the task as deferred; shape depends on change 19's `LLMNPC` chat-memory design. |
| `NPC` | `schedule` | seam (`None`) | No owning change identified yet — see Open Questions. |
| `Monster` | `threat_tier` | **built** (`MonsterTier` key, required) | Needed by D-6's trait-scale derivation; without it `Monster` cannot be constructed with valid trait values. |
| `Monster` | `loot_table` | seam (`[]`) | Explicitly named in the task as deferred; item/equipment data model is change 5's. |
| `Monster` | `behaviour_tree` | seam (`None`) | Explicitly named in the task as deferred; no owning change identified yet — see Open Questions. |

`PlayerCharacter` and `NPC` also gain the `race`/`subrace` attributes D-3 defines on `LivingEntity`
— not listed in this table since they belong to the base class, not either subclass specifically.

## Risks / Trade-offs

- **[Risk] A future reader could re-derive `atk_phys`/`agility`/`defense` from `vital_baseline`
  again, reintroducing the exact 100×-instead-of-10× error this correction fixed.** → Mitigation:
  D-4 documents the two independently-scaling axes explicitly, with the concrete human/elf numbers
  from `world_info.md`, and the test suite (task 6.3) asserts every pre-subrace baseline stays
  inside `RaceProfile.static_baseline`'s own band — a value produced by any hp-derived ratio would
  fall far outside that band and fail immediately.
- **[Risk] Applying `Subrace.static_modifiers` before the race baseline exists, or blending
  `vital_overrides` instead of replacing, would silently corrupt subrace-adjusted values.** →
  Mitigation: D-5 fixes and documents the exact order, and task 6.5 asserts the `foxkin` MP override
  resolves to exactly `50` (the override's floor), not a value blended with `vital_baseline.mp[0]`
  (`30`).
- **[Risk] A future edit could store a skill-multiplied "effective" value directly into
  `entity.traits`, reintroducing the `88000`-instead-of-`88` error this correction fixed.** →
  Mitigation: D-7's regression tests (tasks 6.3 and 7.5) assert in-band baselines and exact
  post-subrace fractional adjustments; an accidentally-multiplied value fails immediately.
- **[Risk] A caller could request a `STATIC_TIER_REGISTRY` tier that belongs to a different race
  than the entity being constructed (e.g. `human_swordmaster` on an elf), silently producing a
  human-scale value on a race it was never documented for.** → Mitigation: `build_initial_traits()`
  checks `StaticTier.race_key` against the requested `race_key` and raises `ValueError` on mismatch
  (D-4); task 6.8 asserts this raises rather than silently returning a value.
- **[Risk] The `DefaultCharacter` base-class assumption (D-1) could be wrong if Evennia 6.1.0's
  `DefaultCharacter` carries player-puppet-only behavior that misbehaves for `NPC`/`Monster`
  instances that are never puppeted.** → Mitigation: task list includes an explicit verification
  step (mirroring changes 1 and 2's own "verify before trusting" discipline) — instantiate one of
  each subclass in an `EvenniaTest` and confirm no puppet-only hook fires unexpectedly at creation.
- **[Risk] The source-scanning boundary test (D-9) is weaker than a true import-linter contract — it
  catches literal string matches, not renamed imports or indirection (e.g., `getattr(module,
  "get_display_value")`).** → Accepted trade-off for a one-day change; flagged as an open question
  for whoever eventually adds a project-wide import-linter contract for the §3.1 AI/rules boundary,
  at which point this test's job can be folded into that contract.
- **[Risk] `ComponentHolderMixin` is mixed into `LivingEntity` now, before any `Component` subclass
  exists to attach to it.** → Accepted; this is exactly what "declare the seam" means for this piece
  — the cost of adding the mixin now is one base-class entry, and the alternative (adding it later)
  would require every existing `LivingEntity` instance to be aware of a base-class change.

## Migration Plan

Not applicable in the backward-compatibility sense — the project is unreleased with zero users, and
`typeclasses/`/`world/rules/` currently contain no code beyond change 1's empty stubs. The only
sequencing concern is that this change must land after change 2 (needs `RaceProfile`, `Subrace`,
and `MonsterTier`'s current, corrected shape importable) and before changes 4–7, 15, 16, and 19
(each of which attaches to a seam this change declares).

## Open Questions

- **Who owns `NPC.schedule` and `Monster.behaviour_tree`?** Neither is named against a specific
  roadmap change in design doc §11. Left as declared seams with no owning-change comment beyond "a
  later change" — whoever proposes the change that needs them should claim the field rather than
  this change guessing.
- **Who owns `relations` (`RelationHandler`, affinity) and `persona` (`PersonaStore`)?** Design doc
  §5.2 names both as `LivingEntity` handlers, but no roadmap entry in §11 explicitly builds them.
  `persona` is plausibly `import-contract`'s (change 4) job, since §5.2 describes `PersonaStore` as
  persisting *imported* fields verbatim; `relations` is plausibly `npc-dialogue`'s (change 19), since
  its `adjust_relation` intent (§7.4) is the first named consumer. Both are left as unassigned seams
  in D-10 rather than this change asserting an ownership design doc §11 doesn't state.
- **Exact `TraitHandler.add()` call shape** (keyword names for gauge rate, counter bounds, etc.) is
  left to the implementer to confirm against the installed Evennia 6.1.0 `evennia.contrib.rpg.traits`
  source, consistent with the verification discipline changes 1 and 2 already established — design
  doc §4 confirms the classes exist and are usable directly, but does not itself pin every
  constructor keyword.
