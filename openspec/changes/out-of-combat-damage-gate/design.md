## Context

The approved brainstorming design for this work is
`docs/superpowers/specs/2026-09-10-field-combat-initiation-design.md`; this
change implements its D-3 rejection, hoisted ahead of the rest of the sequence
so no intermediate commit is unsafe.

Current state:

- `world/rules/action.py:310` holds the pipeline's only combat-state
  conditional: `if not skill.usable_out_of_combat and request.context.battlefield is None`.
- `world/rules/action_preview.py:141` mirrors it for the shared side-effect-free
  preview, which also backs the combat-session submission revalidation.
- `world/rules/targeting.py::RoomActionContext` reports every co-located
  non-self entity as `Relation.ALLY`. Out of combat there is no way to express
  hostility, so `FactionConstraint.ANY` damage skills would pass faction
  validation against an NPC.
- `"damage"` is the only HP-damage effect handler in the project
  (`world/rules/combat.py:349`). A static `DamageEffect` read over a skill
  definition's parsed effects is therefore a complete test for "this skill can
  subtract HP".
- Verified inertness: of the skills that declare `usable_out_of_combat=True`
  today — `flight`, `flash_step`, `status_disguise`, `dominion_art`, the four
  `divine_*` mysteries, `divine_sexual_arts`, the generated `_body_multiplier`
  tiers, and the whole sexual-act catalog — none carries a `DamageEffect`.

Constraint from `openspec/specs/action-resolution-pipeline/spec.md`: the
resolver and targeting layers are required to contain no combat-state branch
other than one explicitly marked gate. Adding a second gate is a spec change,
not a quiet edit.

## Goals / Non-Goals

**Goals:**

- Make "a damaging action never resolves without a battlefield" an enforced
  invariant of the deterministic core rather than an accident of registry data.
- Report it through the shared preview as well as the resolver, so a UI shows
  the skill disabled with a stable reason instead of discovering it at commit
  time.
- Land while inert, so the change is safe in isolation and can be verified by
  asserting that nothing shipping today changes behaviour.

**Non-Goals:**

- Routing a monster-targeted damage cast into combat. That is
  `field-combat-initiation`; until it lands, a damage skill flagged usable
  outside combat is simply refused everywhere outside a battlefield.
- Changing any skill's `usable_out_of_combat` value. That is
  `skill-field-availability`.
- Item use. `resolve_item_use` carries its own `in_combat` argument and its own
  contract; a damaging consumable is a separate question this change does not
  answer.
- Any change to `RoomActionContext`'s ally-by-default relation model.

## Decisions

**D-1. The gate lives in the resolver, mirrored by preview — not only at the
call site.** `settle_out_of_combat_cast` is one caller today, but the invariant
is about what the deterministic core is willing to resolve. Enforcing it at the
resolver means a future caller cannot reintroduce the hole by constructing a
`RoomActionContext` request directly.

Alternatives rejected:

- *Enforce only in `commands/action.py` routing.* Rejected: the command layer
  is a presentation seam; a rules-layer invariant enforced in a command is one
  refactor away from being lost.
- *Enforce only in `cast_settlement.settle_out_of_combat_cast()`.* Rejected for
  the same reason, and because the preview would still advertise the skill as
  available.
- *Make `RoomActionContext` report monsters as enemies instead.* Rejected: it
  would silently change faction outcomes for every existing out-of-combat
  cast, including the sexual-act catalog, and the pipeline spec deliberately
  pins that context's ally-by-default behaviour.

**D-2. The condition is `DamageEffect` present **and** no battlefield — not a
target inspection.** The resolver has no notion of `Monster`, and giving it one
would put a typeclass dependency into the deterministic pipeline. "No
battlefield" is the resolver-shaped way to say "this is not a fight", and from
exploration a battlefield exists only because combat was opened on a monster.
The reason name therefore describes the player-facing rule while the
implementation stays typeclass-agnostic.

**D-3. Gate order: the flag first, the damage gate second.** A damage skill
that is not flagged usable outside combat should keep reporting
`SKILL_NOT_USABLE_OUT_OF_COMBAT`, which is the more specific and more
actionable answer ("this skill cannot be selected here at all"). The new gate
speaks only for skills the registry does permit outside combat. Reversing the
order would mask the flag for every damage skill and make
`skill-field-availability`'s audit unobservable.

**D-4. The static effect read is the whole test.** No simulation, no magnitude
estimate. A skill either declares a `DamageEffect` or it does not. Indirect HP
movement (`SexualDrainEffect`, which drains a target's pleasure into the
caster's own pools) is deliberately not covered, consistent with
`combat-opening-seams`'s `commanded_damage_reaches_enemy()`, so the two
damage-shaped questions in the codebase answer from the same definition.

**D-5. Preview and resolver must agree by construction.** The condition is
expressed once as a shared predicate over `(skill, context)` and consumed by
both sites, so the pipeline's existing "preview and preflight agree"
requirement cannot drift.

## Risks / Trade-offs

- **[The gate is inert on landing, so a green test suite proves little about
  the eventual behaviour.]** → Mitigated by asserting the gate directly with a
  synthetic skill definition that carries a `DamageEffect` and
  `usable_out_of_combat=True`, plus an inventory assertion that no shipping
  skill matches that shape today. The behaviour is tested even though no
  content triggers it.
- **[Modifying an archived requirement's "exactly one gate" wording could look
  like weakening the no-combat-branching discipline.]** → The modified
  requirement enumerates both gates by name and keeps the token scan, so the
  discipline stays enforceable and any third gate is still a spec violation.
- **[The reason name mentions monsters while the condition tests for a
  battlefield.]** → Documented at both enforcement sites and in the
  requirement text: the message states the rule a player can act on, the
  condition states the invariant the core enforces. The two coincide because
  opening combat on a co-located monster is the only exploration path to a
  battlefield.
- **[A damaging skill flagged usable outside combat becomes unusable between
  this change and `field-combat-initiation`.]** → Accepted and intended. That
  window is exactly the hazard this change closes, and no such skill exists
  until `skill-field-availability` lands, which depends on this change.
