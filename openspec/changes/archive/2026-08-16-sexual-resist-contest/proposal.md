## Why

The sexual act system (`docs/superpowers/specs/2026-08-15-sexual-act-system-overview-design.md`,
proposal `B6a` in that document set's implementation sequence) lets a player target another
participant with a bidirectional act. Nothing today lets that target refuse. `sexual-act-registry`
and `sexual-act-effects` (siblings `B4`/`B5`) will define acts and how they apply pleasure, but the
question "does this act land, or does the target resist it" has no answer anywhere in the codebase.

`climax-settlement` (already shipped) went further and left an explicit seam for this proposal: an
entity stuck in `進行中` can be extended indefinitely by a later act
(`SexualState.stage_climax_extension()`), and that design's own risk log states the escape valve —
"the resist opening at the sixth climax turn" — is "intentionally deferred to
`sexual-resist-contest`". Until this lands, nothing bounds indefinite climax suppression even in
principle.

This proposal supplies the missing piece: a pure, deterministic resist verdict that a later
proposal (`sexual-resist-turn-cost`, `B6b`) wires into actual turn consumption. It is scoped as a
standalone pure function specifically so it can be built and tested independently of the acts that
will call it.

## What Changes

- Add `world/rules/sexual_resist.py` with `resist_verdict(actor, resister, *, rng=roll_d100) ->
  ResistVerdict`, a pure function with no state mutation. The contest is strictly two-party (one
  caster, one resisting participant), so — unlike `_attempt_flee`, which searches a whole battlefield
  for the fastest pursuer — it takes no `battlefield` argument. It reuses `disengage.py`'s contest
  shape (`roll_d100() + resist_score >= COMBAT_YAML["to_hit"]["defender_constant"] + actor_score`,
  both scores read through `evaluate_combat_modifiers_no_create()`, the no-create query that never
  materializes the `sexual` handler) rather than inventing a second contest
  idiom, with each score itself a weighted blend of effective `agility` and `atk_phys` (new weights
  in `sexual_resist.yaml` — resisting a hold is a strength-and-speed contest, unlike fleeing, which
  is agility alone).
- Add `world/rules/rulebook/sexual_resist.yaml`: the stat-blend weights for the contest scores, and
  a per-affinity-stage resist modifier table keyed to the seven shipped `affinity_config.py` stages,
  where the two stages at and above the natural cap (`至愛`, `絕對羈絆`) carry `auto_comply: true`
  instead of a numeric modifier.
- `resist_verdict()` short-circuits to compliance (no roll) when either holds:
  - the resister is an `NPC` whose affinity stage toward the actor carries `auto_comply: true`
    (read through the existing `RelationHandler.stage_for()`), or
  - the resister's `entity.sexual.climax_phase.level == "進行中"` and
    `entity.sexual.climax_turns <= 5` (reusing the exact fields `climax-settlement` already shipped
    on `SexualState`).
- From the resister's sixth consecutive settlement point in `進行中` (`climax_turns > 5`), or for
  any resister the affinity table does not grant `auto_comply`, the ordinary d100 contest applies —
  reading through `evaluate_combat_modifiers_no_create()` means an entity at `pleasure`'s `極限` band
  automatically resists worse via the already-shipped `high_arousal_agility_accuracy_penalty`
  (`agility: -20%`), with no new rule authored for that effect.
- A `Monster` resister has no affinity record (`RelationHandler` requires an `NPC` owner) and always
  resolves through the plain stat contest; it can never `auto_comply`.

**No effect handler, act, or turn-cost wiring is added here.** This proposal ships a callable
verdict function and its data table only; `sexual-resist-turn-cost` (`B6b`) is the sibling proposal
that calls it from a live action and spends turns based on the result.

## Capabilities

### New Capabilities
- `sexual-resist-contest`: the deterministic resist verdict — contest formula, affinity-stage
  modifier and `auto_comply` table, and the climax-turn short circuit — that a target's compliance
  or refusal of a bidirectional sexual act resolves through.

### Modified Capabilities
(none — this proposal adds a new, self-contained pure-function capability and reads existing
`climax-settlement`, `affinity-system`, and `disengage-action` state without changing any of their
requirements)

## Impact

- **New files:** `world/rules/sexual_resist.py`, `world/rules/rulebook/sexual_resist.yaml`, and
  their test module.
- **Reads (no changes) from:** `world/rules/disengage.py` (contest shape reference only — not
  imported, to avoid a real dependency on the flee-specific skill machinery),
  `world/rules/combat_modifiers.py::evaluate_combat_modifiers_no_create`, `world/rules/combat.py::COMBAT_YAML`,
  `world/rules/affinity_config.py` (`AffinityStage`, `get_config().stage_for_value`),
  `typeclasses/entities.py` (`LivingEntity.relations`), `typeclasses/npcs.py` (`NPC`),
  `typeclasses/monsters.py` (`Monster`), `typeclasses/characters.py` (`PlayerCharacter`),
  `world/rules/sexual_state.py` (`SexualState.climax_phase`, `SexualState.climax_turns`).
- **No production call site is added in this proposal.** `resist_verdict()` has no caller until
  `sexual-resist-turn-cost` lands; this proposal's own tests call it directly.
- **Dependencies:** `climax-settlement` (`B3`, shipped — supplies `climax_turns`) and
  `sexual-act-registry` (`B4`, not yet shipped — this proposal does not import anything from it and
  can be implemented before it lands, but its own design references `B4`'s eventual act-def shape
  only informally, never by import).
