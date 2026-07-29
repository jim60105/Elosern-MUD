## Why

This is roadmap item #6 (design doc §11), depending on change 3 (`entity-traits`) for `LivingEntity`'s
declared `buffs` placeholder seam and the base-value trait boundary (D-7, which reserves `StaticTrait`'s
`mod` component specifically for `BuffHandler`). Design doc §5.2 states plainly that `buffs` **is** the
`BuffHandler` on every `LivingEntity`; today it is only a `None`-defaulting placeholder attribute. Three
later changes each need a concrete rule-table shape to attach to before they can be designed responsibly:
change 7 (`sexual-state`) needs `rulebook/sexual.yaml`'s transition-rule grammar to already exist as a
convention, not something it invents from scratch; change 9 (`dice-combat`) needs
`rulebook/combat_modifiers.yaml` populated with the exact poison/paralysis/fear/arousal coupling design
doc §6.4 and D8 describe, in one table with no `is_sexual_debuff` branching; and change 5
(`skills-equipment`) explicitly deferred Elosia's partial magic-growth-rate conferral onto Violet to this
change, since design doc §6.4 assigns "rate of change" to buffs, not skills. Until this change lands, no
module can express a status effect, a combat debuff, or a conferred rate modifier without inventing its
own ad hoc mechanism.

## What Changes

- Mount `evennia.contrib.rpg.buffs.BuffHandler` directly as `entity.buffs` on `LivingEntity`
  (`typeclasses/entities.py`), replacing change 3's placeholder `AttributeProperty` — the same
  handler-mount replacement pattern change 5 already used for `entity.skills`/`entity.equipment`.
  `entity.buffs` **is** the handler; no raw payload is ever assigned to the bare `buffs` name. Duration,
  tick, and stacking are the contrib's own job (§4: "use directly") — this change defines only the
  setting's buff definitions and the glue connecting them to `TraitHandler` and the rulebook.
- Add `world/rules/rulebook/`: a small, shared declarative rule-engine skeleton (`schema.py` — `Rule`,
  a condition grammar covering event/field-threshold/field-changed/buff-presence checks, a YAML loader,
  and a pure `evaluate()` function) that this change's own `combat_modifiers.yaml` table runs on, and
  that change 7's future `sexual.yaml` is expected to import rather than reinvent. Every rule in a table
  this change owns carries an `id`; every `id` has exactly one named unit test (design doc §10).
- Add `world/rules/rulebook/combat_modifiers.yaml` and `world/rules/combat_modifiers.py`: a seed table
  (poison, paralysis, fear, plus the two arousal/climax-phase conditions transcribed verbatim from design
  doc §6.4) evaluated by one condition engine with no special-casing for the sexual-origin rows, and a
  pure query function, `evaluate_combat_modifiers(entity)`, that change 9 will call at combat-resolution
  time. Sexual-field conditions run against a duck-typed context so the table is fully authored and
  tested today, self-arming to a live `entity.sexual` read once change 7 lands (mirroring change 4's
  pluggable skill-registry pattern).
- Add `world/rules/rulebook/buffs.yaml` and `world/rules/buffs.py`: buff *definitions* — not a fourth
  when/then rule table, since a buff is a stateful object with its own contrib-provided apply/tick/expire
  lifecycle, not a condition-triggered transition. Each definition configures which of the three things
  design doc §6.4 says a buff may modify — rate of change, clamped bounds, decay rate — a buff may
  configure any subset, never combat-stat multipliers (that boundary stays change 5's). Seed set: `poisoned`
  (rate), `paralysis` and `fear` (marker buffs read by `combat_modifiers.yaml`), and
  `conferred_growth_rate` — the mechanism inherited from change 5's D-6, modeling Elosia's partial
  magic-growth-rate conferral onto Violet as a buff instance carrying a `source_key` and a `scale`,
  applied via `entity.buffs.add(...)`, exposed through a pure query function,
  `growth_rate_multiplier(entity)`, for whichever future progression change reads it.
- Declare, but do not build, three seams: the sexual state machine's own transitions (change 7), the
  `ActionResolver` step that checks a buff forbids an action and calls the cast-time 統御術-style grant
  creation (change 8), and the world clock's fixed settlement order that ticks buff durations relative to
  regen and sexual decay (change 11) — this change's buff tick hooks are exposed as plain callables for
  that clock to invoke, in no order of this change's own invention.

## Capabilities

### New Capabilities
- `rulebook-schema`: the shared condition grammar, YAML loader, `evaluate()` function, and the
  rule-ID-to-test-name discipline every rule table in the project must follow.
- `buff-handler-integration`: `entity.buffs` mounted as the real `BuffHandler`, the setting's `BaseBuff`
  subclass(es) driven by `buffs.yaml`, the rate/bounds/decay modifier application against `TraitHandler`,
  and the conferred growth-rate mechanism (Elosia → Violet).
- `combat-modifier-table`: `combat_modifiers.yaml`'s seed rules and `evaluate_combat_modifiers()`, sharing
  one condition engine across buff-presence and sexual-field-threshold conditions with no branching.

### Modified Capabilities
- None. `openspec/specs/` is currently empty (changes 1–5 have not been archived yet).

## Impact

- **New files**: `world/rules/rulebook/__init__.py`, `world/rules/rulebook/schema.py`,
  `world/rules/rulebook/combat_modifiers.yaml`, `world/rules/rulebook/buffs.yaml`,
  `world/rules/buffs.py`, `world/rules/combat_modifiers.py`, `world/rules/tests/` (new test modules for
  this change's scope).
- **Modified files**: `typeclasses/entities.py` — replaces the `buffs` placeholder `AttributeProperty`
  (change 3, D-10) with a real handler mount, the identical replacement pattern change 5 already used for
  `skills`/`equipment`. No other attribute or base class change 3 authored is altered.
- **Depends on**: change 3 (`entity-traits`) for `LivingEntity`, the `buffs` seam attribute, and the
  base-value/`mod`-component boundary (D-7). Inherits the `conferred_growth_rate` mechanism's ownership
  from change 5 (`skills-equipment`, D-6), which built the sibling `ConferredSkillGrant` for combat-stat
  multipliers and explicitly deferred the rate-of-change half here.
- **Consumers deferred to later changes**: change 7 (`sexual-state`) imports `rulebook/schema.py`'s
  condition engine for `sexual.yaml` rather than reinventing it, and wires its own `SexualState` fields
  into `combat_modifiers.py`'s duck-typed context; change 8 (`action-resolver`) owns the buff-forbids-action
  check and any cast-time grant creation; change 9 (`dice-combat`) calls
  `evaluate_combat_modifiers()` during combat resolution; change 11 (`world-clock`) owns the fixed
  settlement order that invokes this change's buff-tick hooks.
