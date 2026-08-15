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
- Keep the change to one table row, the minimal context-builder extension that makes the row
  reachable, and the tests those two steps structurally require — no new mechanism anywhere.

**Non-Goals:**
- An offensive payoff for `exposure`. That is delivered by 羞恥線 act effects (distraction debuffs
  applied to the entities who can see the exposed actor) in a later proposal in the set, not by a
  modifier on the exposed entity itself. One defensive row is the complete modifier-table surface
  this proposal adds.
- Any change to `world/rules/combat_modifiers.py`'s condition evaluator, `_merge_adjustments()`,
  or the adjustment-bundle vocabulary. `defense` is already a consumed bundle key (see
  `guardian_instinct_defense_bonus` and `defense_instinct_defense_bonus`), and `field`/`gte` is
  already a supported condition shape (see `high_arousal_agility_accuracy_penalty`). The three
  condition-context builders (combat_modifiers.py's two and status_query.py's one) gain `exposure`
  (D-4) — nothing else in either module changes.
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

**D-4: The condition context is an explicit allowlist — `exposure` must be added to all three
combat-modifier context builders. This was wrong in the planning drafts; corrected after review of
the actual code.** `evaluate_condition()` resolves a `field` condition purely from the context
dictionary handed to it, and a field absent from the context evaluates as not-satisfied. There are
three context builders that feed `matched_combat_modifiers()` — `_build_context` in
`world/rules/combat_modifiers.py` (used by `evaluate_combat_modifiers()`, i.e. live combat math),
`build_no_create_condition_context()` (used by `evaluate_combat_modifiers_no_create()` for preview
and revalidation), and `_sexual_condition_context()` in `world/rules/status_query.py` (used by
`build_status_read_model()`'s player-visible matched-condition list) — and all three originally
exposed exactly `arousal` and `climax_phase` and nothing else. The original drafts of this proposal
asserted the row needed no production code at all on the strength of "`field`/`gte` is already a
supported condition shape" — true but insufficient: the shape is supported, but the field was not in
the contexts it evaluates against, so the row could never have matched. D-4's correction adds
`exposure` to all three builders, and the two bullets below record why the first two and the third
are each individually non-optional:

- The combat_modifiers.py pair (`_build_context`, `build_no_create_condition_context()`) must move
  together: the no-create path feeds the action preview, and a preview that silently omitted the
  penalty while resolution applies it would violate the preview/preflight/resolve agreement the
  `combat-modifier-table` capability already pins for cost adjustments — the same divergence class
  this proposal's damage-resolution regression test exists to catch.
- The status_query.py builder was initially left out, and the first review round (independent
  rubber-duck review after implementation) blocked that: `build_status_read_model()` presents every
  condition that `matched_combat_modifiers()` matches, and the shipped `webclient-status-presentation`
  requirement ("Status conditions use deterministic matched modifiers") mandates that sexual-state
  entries appear while their canonical combat predicates match. Leaving `exposure` out would have
  sentenced players to a live, unexplained `defense: -15` with a `status_display.yaml` label that
  could never render. Restoring it also aligns with the sexual `high_arousal_agility_accuracy_penalty`
  row, whose matched condition the status panel already shows. Scope note: `status_query.py` is also
  scheduled for edits by later proposals in the set (pleasure-gauge's no-create pleasure remap, and
  the skill-category status listing); both changes edit different code regions (the pleasure remap
  replaces this same field/levels loop, the listing reads `owned_keys()`), so the single-function
  conflict is textual and trivial to merge when the branches land sequentially.
- No change to `evaluate_condition()` itself: it already handles every condition shape this row
  uses. The "no special-casing by condition origin" invariant of the main spec is preserved —
  `exposure` rides the same `field`/`gte` path as `arousal`.

**D-5: The row requires an entry in `status_display.yaml`, enforced at import time — this file is
in scope.** `world/rules/status_display.py::_build_display_metadata()` fails closed unless the
display table covers exactly the buff keys and the current `combat_modifiers.yaml` rule IDs, and it
runs at module import — the new row cannot land without a matching display entry. The entry uses the
same severity as the two sibling sexual-field rows (`warning`, where `high_arousal_agility_accuracy_
penalty` and `climax_in_progress_locks_actions` both sit) and a Traditional Chinese label in the
established `<level><trait>減損` shape (`高露出防禦減損`). Because D-4 extends the status read
model's context, the entry is reachable: the matched condition renders with this label, exactly as
`high_arousal_agility_accuracy_penalty`'s entry does.

## Risks / Trade-offs

[Risk] The percentage-vs-flat mistake in D-2's original draft was a real crash, caught only by an
independent review reading `combat.py::_adjusted_defense` directly rather than trusting this
document's own initial reasoning by analogy. → Mitigation: the fix (flat `-15`) removes the risk at
its root — the row can no longer reach a code path that does not know how to parse it. Task 2.6 below
adds a regression test that exercises the row through `_adjusted_defense`/real damage resolution, not
only through `evaluate_combat_modifiers()` in isolation, specifically so this class of mismatch
cannot recur silently for a future row added to this table by a later proposal.

[Risk] The condition-context allowlist (D-4) was a silent never-match bug in this proposal's own
planning drafts: the row as originally scoped would have matched nowhere, because neither
combat_modifiers.py context builder exposes `exposure`. It was caught by reading the actual context
builders during implementation review, not by any test failure. → Mitigation: D-4 scopes the two-line
production change explicitly, both builders move together, and the new test set pins the row through
every evaluation surface it promises (the `evaluate_combat_modifiers()` bundle, the boundary
conditions, the merged bundle, the no-create preview path, and real damage resolution) so a future
row added to this table by a later proposal inherits a test-shape that exercises its real consumers.

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
