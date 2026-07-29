## Context

This is roadmap item #3 (design doc §11), depending on change 1 (`bootstrap-container-evennia`,
which provides the running Evennia 6.1.0 project and the empty `typeclasses/`/`world/rules/` stub
packages) and change 2 (`lore-world-data`, which provides `RaceProfile`, `MonsterTier`, and the
other frozen-dataclass registries in `world/lore/`). No code exists yet for this change's scope —
`typeclasses/` and `world/rules/` are currently empty packages.

Design doc §5.2 sketches `LivingEntity` as a diagram with seven handlers (`traits`, `sexual`,
`buffs`, `equipment`, `skills`, `relations`, `persona`) and three subclasses
(`PlayerCharacter`/`NPC`/`Monster`) each with extra fields. This change's job is narrow: build the
`traits` handler and the class hierarchy it sits on, and declare — but not implement — every other
handler and non-trait field, so later changes (5, 6, 7, 15, 16, 19) have a stable seam to attach to
instead of having to modify the base class shape when their turn comes.

Design doc §4 (the Contrib Reuse Matrix) is verified against the installed Evennia 6.1.0 and is
authoritative for every module path and class name this design cites.

## Goals / Non-Goals

**Goals:**
- `typeclasses/entities.py::LivingEntity` — the shared base for characters, NPCs, and monsters,
  mounting `TraitHandler` (`evennia.contrib.rpg.traits`) with the setting's eight-key trait set and
  `ComponentHolderMixin` (`evennia.contrib.base_systems.components`) per §4's assignment of that
  contrib to this exact module.
- `PlayerCharacter`, `NPC`, `Monster` subclasses with the extra fields §5.2 names, each field
  explicitly marked as either built now (trait/stat surface) or a declared seam for a later change.
- Race-driven (and monster-tier-driven) derivation of every trait's initial value from change 2's
  registries — no hardcoded per-race number lives in entity code.
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
- No import schema, validation CLI, or loader (change 4) — this change only provides the typeclasses
  change 4 will instantiate into.
- No guild-rank progression, quest-log population, or wallet earn/spend logic (changes 15, 16, 19) —
  fields exist as seams; behavior is out of scope.
- No backward-compatibility, migration, or deprecation handling — the project is unreleased with
  zero users, and `typeclasses/`/`world/rules/` currently contain no code beyond change 1's empty
  stubs.

## Decisions

### D-1. `LivingEntity(ComponentHolderMixin, DefaultCharacter)`.

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

### D-2. `Monster` gets its own file, `typeclasses/monsters.py` — a small, judgment-call extension
to design doc §3.2's tree.

§3.2 names `typeclasses/characters.py` (`PlayerCharacter`) and `typeclasses/npcs.py`
(`NPC`/`LLMNPC`) but no file for `Monster`, even though §5.2 clearly wants a `Monster(LivingEntity)`
class. Folding `Monster` into `npcs.py` would conflate two conceptually different subclasses (one
dialogue/schedule-driven, one threat-tier/loot-driven) in one file for no reason. **Judgment call**:
add `typeclasses/monsters.py`, mirroring the one-subclass-per-file pattern the other two files
already establish. If this is wrong, it is a one-file move, not a redesign — flagged here the same
way change 1 flagged its own directory-naming judgment call (D-4 in that change's design.md).

### D-3. Trait scale derivation: `RaceProfile` drives `hp`/`mp`/`sp`/`magic_level` directly; a
derived race scale factor drives `atk_phys`/`agility`/`defense`, since `RaceProfile` has no
dedicated combat-stat field.

Design doc §5.1's `RaceProfile` (frozen by change 2) has exactly six fields: `key`, `lifespan`,
`magic_cap`, `vital_baseline`, `learning_multiplier`, `can_use_divine_arts`. `vital_baseline`
(a `Vitals(hp, mp, sp)` of `(baseline, gifted_ceiling)` tuples) maps directly onto the three gauge
traits' max, and `magic_cap` maps directly onto the `magic_level` counter's max. But there is no
`RaceProfile` field for physical combat stats, and the task explicitly requires the
three-orders-of-magnitude gap to "come from lore, never hardcoded numbers in the entity code" for
the entity surface as a whole, not just HP.

**Resolution**: `world/rules/traits.py` defines a single reference baseline for a nominal human
starting adventurer —

```python
REFERENCE_STATIC_BASELINE = {"atk_phys": 10, "agility": 10, "defense": 10}
```

— and a `race_scale_factor(race: RaceProfile) -> float` that returns
`race.vital_baseline.hp[0] / RACE_REGISTRY["human"].vital_baseline.hp[0]` (100 for elf, 1.5 for
beastfolk, 1.0 for human by construction). Every static trait's initial `base` is
`REFERENCE_STATIC_BASELINE[key] * race_scale_factor(race)`. This keeps the *ratio* between races
lore-derived (driven by the same `vital_baseline.hp` values change 2 already asserts a ≥50x human
vs. elf gap on) while keeping exactly three numbers hardcoded anywhere in this change — a single,
documented, race-independent reference point, not a magic number per race. This is a **judgment
call**, not something design doc §5.1/§5.2 states directly — flagged here so a future reader doesn't
mistake it for a literal transcription from the design doc.

**Alternative considered**: Extending `RaceProfile` itself with `combat_baseline` fields. Rejected
because `RaceProfile` is change 2's frozen contract (its own design.md D-1 says "exactly these six
fields... adding descriptive fields nobody reads risks the dataclass drifting from the contract
other changes design against"); reopening it here would touch an already-landed change's data
model rather than build on top of it.

`guild_merit` (counter) starts at `base=0` with no upper bound (`max=None`) — `world_info.md`/design
doc give no cap for guild merit, unlike `magic_level`.

### D-4. `Monster` trait baselines are bridged from `MonsterTier`'s ordering, since `MonsterTier`
(unlike `RaceProfile`) carries no numeric vitals.

Change 2's `MonsterTier` dataclass is `key`, `display_name_zh`, `guild_rank_range`,
`example_monsters_zh`, `description` — no HP/attack/defense numbers, only a qualitative threat band
(F-E / D-C / B-A / 災厄級) and example monster names. `Monster` is a `LivingEntity` and therefore
needs the same eight traits mounted, but there is no `RaceProfile`-equivalent numeric source to
derive them from. This is a real gap between what change 2 shipped and what this change needs — see
also the Open Questions below.

**Resolution**: `world/rules/traits.py` defines an order-of-magnitude multiplier keyed to
`MonsterTier`'s own documented ordering, not a fabricated per-monster number:

```python
MONSTER_TIER_SCALE = {
    "low": 10 ** 0,       # F-E
    "mid": 10 ** 1,       # D-C
    "high": 10 ** 2,      # B-A
    "calamity": 10 ** 3,  # 災厄級
}
```

`initial_trait_config_for_monster_tier(tier_key)` applies this multiplier to the same human
reference baseline (`REFERENCE_STATIC_BASELINE` and `RACE_REGISTRY["human"].vital_baseline`) that
`race_scale_factor` uses, so a 災厄級 monster's HP is ~1000x a human's baseline HP — consistent with
the setting's stated three-orders-of-magnitude spirit, and traceable to `MonsterTier`'s own
documented ordering (index 0–3) rather than an invented number per monster. This is flagged as a
judgment call bridging a genuine data gap, not a literal reading of either design doc §5.1 or §5.2.
`Monster.threat_tier` (a `MonsterTier` key) is therefore built in this change, not declared as a
seam, because the trait-scale mechanism needs it to exist.

**Alternative considered**: Leave `Monster` trait initialization entirely unimplemented (a pure
seam) until a future change adds numeric bestiary data. Rejected because `Monster(LivingEntity)` is
explicitly in this change's scope per the task framing ("`PlayerCharacter`, `NPC`, and `Monster`
subclasses — but only the trait/stat surface"), and an entity class that cannot be constructed with
valid trait values is not a usable seam for change 5/8/9 to build on.

### D-5. `disguised_stats` lives in `world/rules/traits.py`, not a separate module.

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
the two live in unrelated attributes with no code path between them.

### D-6. The disguise boundary is enforced by a source-scanning regression test, not a new
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

### D-7. Non-trait `LivingEntity` handlers are declared as typed placeholder attributes with an
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

### D-8. Subclass extra fields: built vs. declared-seam split.

| Class | Field | Status | Rationale |
|---|---|---|---|
| `PlayerCharacter` | `guild_rank` | seam (`None`) | Progression logic is change 16's; the field would need game-design input (does everyone start unranked, or at F?) this change shouldn't make. |
| `PlayerCharacter` | `quest_log` | seam (`[]`) | Explicitly named in the task as deferred. |
| `PlayerCharacter` | `wallet` | seam (`0`) | Earn/spend logic and starting-copper balance are change 16's economic decisions, not this change's. |
| `NPC` | `dialogue_memory` | seam (`None`) | Explicitly named in the task as deferred; shape depends on change 19's `LLMNPC` chat-memory design. |
| `NPC` | `schedule` | seam (`None`) | No owning change identified yet — see Open Questions. |
| `Monster` | `threat_tier` | **built** (`MonsterTier` key, required) | Needed by D-4's trait-scale derivation; without it `Monster` cannot be constructed with valid trait values. |
| `Monster` | `loot_table` | seam (`[]`) | Explicitly named in the task as deferred; item/equipment data model is change 5's. |
| `Monster` | `behaviour_tree` | seam (`None`) | Explicitly named in the task as deferred; no owning change identified yet — see Open Questions. |

## Risks / Trade-offs

- **[Risk] `race_scale_factor` and `MONSTER_TIER_SCALE` are judgment calls, not literal design-doc
  transcriptions, and a future reader could "correct" them back toward inventing per-race numbers.**
  → Mitigation: both are documented in D-3/D-4 with the reasoning, and the test suite asserts the
  exact derived values and the invariant that only `race.vital_baseline.hp` (and, for monsters, tier
  ordering) drive the multiplier — no other hardcoded per-race/per-tier combat number is permitted
  anywhere in `world/rules/traits.py`.
- **[Risk] The `DefaultCharacter` base-class assumption (D-1) could be wrong if Evennia 6.1.0's
  `DefaultCharacter` carries player-puppet-only behavior that misbehaves for `NPC`/`Monster`
  instances that are never puppeted.** → Mitigation: task list includes an explicit verification
  step (mirroring changes 1 and 2's own "verify before trusting" discipline) — instantiate one of
  each subclass in an `EvenniaTest` and confirm no puppet-only hook fires unexpectedly at creation.
- **[Risk] The source-scanning boundary test (D-6) is weaker than a true import-linter contract — it
  catches literal string matches, not renamed imports or indirection (e.g., `getattr(module,
  "get_display_value")`).** → Accepted trade-off for a one-day change; flagged as an open question
  for whoever eventually adds a project-wide import-linter contract for the §3.1 AI/rules boundary,
  at which point this test's job can be folded into that contract.
- **[Risk] `MonsterTier` carrying no numeric baseline is a gap in change 2's shipped data model, and
  this change's bridge (D-4) is a workaround, not a correction of the underlying gap.** → Accepted;
  documented as an open question rather than silently reopening change 2's already-specified
  `MonsterTier` dataclass. A future bestiary-focused change can supersede `MONSTER_TIER_SCALE` with
  real per-species data without breaking `Monster`'s trait-mounting mechanism, since the mechanism
  only depends on `threat_tier` resolving to *some* multiplier.
- **[Risk] `ComponentHolderMixin` is mixed into `LivingEntity` now, before any `Component` subclass
  exists to attach to it.** → Accepted; this is exactly what "declare the seam" means for this piece
  — the cost of adding the mixin now is one base-class entry, and the alternative (adding it later)
  would require every existing `LivingEntity` instance to be aware of a base-class change.

## Migration Plan

Not applicable in the backward-compatibility sense — the project is unreleased with zero users, and
`typeclasses/`/`world/rules/` currently contain no code beyond change 1's empty stubs. The only
sequencing concern is that this change must land after change 2 (needs `RaceProfile`/`MonsterTier`
importable) and before changes 4–7, 15, 16, and 19 (each of which attaches to a seam this change
declares).

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
  in D-7 rather than this change asserting an ownership design doc §11 doesn't state.
- **Should `MonsterTier` eventually gain numeric baseline fields**, making D-4's bridge unnecessary?
  Left as a question for whoever next touches the bestiary — this change's `MONSTER_TIER_SCALE`
  bridge is deliberately isolated to `world/rules/traits.py` so it can be superseded without
  touching `Monster`'s class shape.
- **Exact `TraitHandler.add()` call shape** (keyword names for gauge rate, counter bounds, etc.) is
  left to the implementer to confirm against the installed Evennia 6.1.0 `evennia.contrib.rpg.traits`
  source, consistent with the verification discipline changes 1 and 2 already established — design
  doc §4 confirms the classes exist and are usable directly, but does not itself pin every
  constructor keyword.
