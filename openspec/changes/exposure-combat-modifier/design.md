## Context

`world/rules/rulebook/combat_modifiers.yaml` is a single declarative table evaluated by one condition
engine (`world/rules/combat_modifiers.py::evaluate_combat_modifiers`, reusing
`world/rules/rulebook/schema.py::evaluate_condition`). It already mixes three condition origins in
one table with no source-level branching between them: buff-presence rows (`poison_agility_penalty`,
`fear_agility_and_accuracy_penalty`), sexual-field-threshold rows
(`high_arousal_agility_accuracy_penalty`, `climax_in_progress_locks_actions`), and skill-ownership
rows (`defense_instinct_defense_bonus` and seven others). The shipped `combat-modifier-table` spec's
own stated purpose is that this table is evaluated by one condition engine with no special-case
branch between origins — a new sexual-field row is exactly the kind of addition the table was already
generalized to accept.

This proposal is part of the
[Sexual Act System document set](../../../docs/superpowers/specs/2026-08-15-sexual-act-system-overview-design.md),
proposal `B7` in its [Sexual Pleasure Model](../../../docs/superpowers/specs/2026-08-15-sexual-pleasure-model-design.md)
§4. It is scheduled in the set's first parallel batch, independent of every other proposal, because
it reads `entity.sexual.exposure` — a field that already exists on the shipped `SexualState` and that
no other proposal in the set changes.

## Goals / Non-Goals

**Goals:**
- Give `exposure` a combat cost, matching the treatment `arousal` and `climax_phase` already receive.
- Keep the change to a single table row plus its structurally-required test, touching no production
  Python.

**Non-Goals:**
- An offensive payoff for `exposure`. That is delivered by 羞恥線 act effects (distraction debuffs
  applied to the entities who can see the exposed actor) in a later proposal in the set, not by a
  modifier on the exposed entity itself. One defensive row is the complete modifier-table surface
  this proposal adds.
- Any change to `world/rules/combat_modifiers.py`, `evaluate_condition()`, or the adjustment-bundle
  vocabulary. `defense` is already a consumed bundle key (see `guardian_instinct_defense_bonus` and
  `defense_instinct_defense_bonus`), and `field`/`gte` is already a supported condition shape (see
  `high_arousal_agility_accuracy_penalty`). Nothing new is introduced at the mechanism level.
- Any interaction with `pleasure-gauge` (B1). `arousal` becomes a derived-but-still-comparable view
  in that later proposal; `exposure` is untouched by it, so this proposal has no ordering dependency
  on B1 landing first or after.

## Decisions

**D-1: One `ADDED Requirement`, not a `MODIFIED` one.** Every shipped requirement in the
`combat-modifier-table` capability already covers a new row in general terms without its text
changing:

- "combat_modifiers.yaml SHALL contain both buff-presence rules... and sexual-field-threshold rules...
  and `combat_modifiers.py` SHALL evaluate every rule... through the identical `evaluate_condition()`
  function" — already true after this row lands; the requirement names *at least one* sexual-field
  rule as an example, not an exhaustive set.
- "For every `Rule.id` present in `combat_modifiers.yaml`, `test_combat_modifiers.py` SHALL define
  exactly one test function named `test_rule_<id>`" — a general correspondence requirement. Its
  worked-example scenario lists the five rules that existed when it shipped; that scenario remains
  true verbatim after a sixth row is added, since it does not claim the five are exhaustive.
- No existing requirement enumerates `combat_modifiers.yaml`'s row set as closed, and none names
  `exposure` as a field the table must never read.

So none of the five existing requirements needs editing — a `MODIFIED Requirements` delta would be
the wrong shape here (per the skill's own guardrail against a no-op `MODIFIED` that "loses detail at
archive time" if done carelessly). Instead the delta spec adds one small, new, narrowly-scoped
`ADDED Requirement` pinning this specific row's existence and exact adjustment magnitude. This gives
the new behaviour a stable requirement id for `tools.spec_traceability` to anchor
`test_rule_high_exposure_defense_penalty` against, matching this project's spec-test-traceability
discipline, while keeping every other requirement in the capability untouched.

**D-2: `-15`, a flat penalty — not a percentage. This was wrong in an earlier draft; corrected after
review.** An earlier draft of this proposal used `defense: "-20%"`, reasoning by analogy to
`agility: "-20%"` on the sibling `high_arousal_agility_accuracy_penalty` row. That analogy does not
hold, and building on it would have shipped a crash:

`agility`'s percentage adjustments are consumed by `world/rules/combat.py::_apply_percent_mod`
(parses a `[+-]\d+(?:\.\d+)?%` string and scales the base stat). **No equivalent function exists for
`defense`.** `defense`'s only consumer, `world/rules/combat.py::_adjusted_defense`
(`float(entity.skills.effective_value("defense")) + evaluate_combat_modifiers(entity).get("defense",
0)`), does a direct numeric addition — a percentage string there raises `TypeError` the first time
the row matches and `_adjusted_defense` is called (every combat round, `combat.py`'s damage-resolution
loop, and again by `overwhelm.py`'s expected-damage estimator). Every existing `defense` row in
`combat_modifiers.yaml` (`defense_instinct_defense_bonus`, `guardian_instinct_defense_bonus`) is
already a flat `defense: 5` for exactly this reason — `defense` simply has no percentage-shaped
consumer anywhere in this codebase, unlike `agility`.

A second, independent reason a percentage was wrong even setting the crash aside:
`world/rules/combat_modifiers.py::_merge_adjustments` only combines two adjustments on the same key
when *both* are numeric or *both* match the percentage regex; a flat int and a percent string on the
same key silently fall through to "last-evaluated value wins" rather than merging. A percentage row
would therefore have silently discarded (or been discarded by) `defense_instinct_defense_bonus`/
`guardian_instinct_defense_bonus` whenever both matched the same entity, directly contradicting this
proposal's own delta-spec merge scenario.

`-15` (three times the existing `+5` bonus magnitude) is chosen to read as a real, felt combat cost
rather than a token one, while staying the same *kind* of number (a flat integer) as every other
`defense` row in the table — there is no other `defense`-scale precedent to calibrate against more
precisely than "clearly larger than a passive +5 perk, since this is an active state's cost."

**D-3: Threshold at `高` (index 3 of 5), matching `arousal`'s `高度` threshold shape.** Both
`exposure` and `arousal` are five-level `OrderedLevelTrait` vocabularies
(`world/lore/sexual_vocab.py::EXPOSURE_LEVELS`, `AROUSAL_LEVELS`), and `high_arousal_agility_
accuracy_penalty` fires at the second-highest level (`高度`, index 3 of `平靜/微興奮/中等/高度/極限`).
`高` is `EXPOSURE_LEVELS`'s equivalently-positioned level (`極低/低/中等/高/極高`, index 3). Matching
the sibling row's threshold position keeps the two sexual-field combat rows readable as a pair rather
than requiring a reader to learn two different intensity conventions.

## Risks / Trade-offs

[Risk] The percentage-vs-flat mistake in D-2's original draft was a real crash, caught only by an
independent review reading `combat.py::_adjusted_defense` directly rather than trusting this
document's own initial reasoning by analogy. → Mitigation: the fix (flat `-15`) removes the risk at
its root — the row can no longer reach a code path that does not know how to parse it. Task 2.2 below
adds a regression test that exercises the row through `_adjusted_defense`/real damage resolution, not
only through `evaluate_combat_modifiers()` in isolation, specifically so this class of mismatch
cannot recur silently for a future row added to this table by a later proposal.

[Risk] A future proposal (the 羞恥線 act catalog) could tune `exposure`'s rate of increase without
revisiting this row's threshold, producing an unintended pacing mismatch (e.g. `高` becoming trivial
to reach in one act). → Mitigation: none needed at this proposal's landing — `exposure`'s only writers
today are the existing `exposure_up_on_clothing_damaged` rule and future act effects, and the
threshold value is a single YAML scalar with no other consumer to keep in sync. Re-tuning later is a
one-line change.

[Risk] None identified for rollback: this is an additive YAML row with no migration, no schema
change, and no interaction with persisted entity state (the row is read at evaluation time, not
stored).

## Migration Plan

None required. This project has zero released users (per `AGENTS.md`); the row is additive and
inert for any entity whose `exposure` has not been raised above `低`, which is every entity today
since no production code path currently raises `exposure` above its floor level outside the existing
`exposure_up_on_clothing_damaged` rule.

## Open Questions

None. The row's shape, threshold, and adjustment magnitude are fully determined by the conventions
already established by `high_arousal_agility_accuracy_penalty` (percentage, second-highest-level
threshold) and by the `defense` field's existing dual-school mitigation role in damage resolution.
