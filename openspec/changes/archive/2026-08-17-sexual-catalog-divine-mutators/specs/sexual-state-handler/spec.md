## ADDED Requirements

### Requirement: saturate_sensitivity() pins every resolvable body part to the top sensitivity level
`SexualState.saturate_sensitivity()` SHALL set every `world.lore.sexual_vocab.BODY_PARTS` member's
sensitivity to `SENSITIVITY_LEVELS[-1]` (`敏感異常`) for a non-`Monster` entity. For a `Monster`
entity, it SHALL set only the `GENERIC_BODY_PART` sensitivity entry, matching `resolve_part`'s
existing unconditional collapse of every `Monster` target to that one channel.

#### Scenario: Every named body part reaches the top sensitivity level
- **WHEN** `entity.sexual.saturate_sensitivity()` is called on a non-`Monster` entity
- **THEN** `entity.sexual.sensitivity[part].level` equals `"敏感異常"` for every `part` in
  `BODY_PARTS`

#### Scenario: A Monster entity gains only the generic channel
- **WHEN** `entity.sexual.saturate_sensitivity()` is called on a `Monster` entity
- **THEN** `entity.sexual.sensitivity[GENERIC_BODY_PART].level` equals `"敏感異常"`, and no named
  `BODY_PARTS` member is present in that entity's `sensitivity.items()`

### Requirement: clamp_shame_to(level) permanently pins shame's bounds and current value to one level, rejecting a Monster target
`SexualState.clamp_shame_to(level)` SHALL set `shame`'s `min`, `max`, and current `value` all to
`level`'s ordinal, using the same `OrderedLevelTrait` bound-setter mechanism `SexualState.__init__`
already uses to pin a `Monster`'s `shame` at the floor. It SHALL raise `ValueError` without mutating
any state when called on a `Monster` entity, whose `shame` bounds are already permanently pinned to
the floor by construction.

#### Scenario: shame is pinned at the target level and cannot subsequently move
- **WHEN** `entity.sexual.clamp_shame_to("成癮")` is called on a non-`Monster` entity, followed by any
  attempt to change `entity.sexual.shame.value` (directly, or via `decay_tick`)
- **THEN** `entity.sexual.shame.level` reads `"成癮"` both immediately after the call and after the
  subsequent attempt, unchanged

#### Scenario: Calling clamp_shame_to on a Monster is rejected, not silently applied
- **WHEN** `entity.sexual.clamp_shame_to("成癮")` is called on a `Monster` entity
- **THEN** it raises `ValueError` and that entity's `shame` bounds remain `min=max=0` (`"無"`),
  unchanged from construction

### Requirement: mark_submission(caster_key) grows an append-only submission_marks set, defaulting to empty
`SexualState.mark_submission(caster_key)` SHALL add `caster_key` to a `submission_marks` frozenset
stored in the existing `sexual_state` attribute category, without removing any previously-added key.
An entity with no prior `mark_submission()` call SHALL read `submission_marks` as an empty frozenset,
with no baseline-import seeding required.

#### Scenario: Marking adds the caster's key without removing any other
- **WHEN** `entity.sexual.mark_submission("alice")` is called, followed by
  `entity.sexual.mark_submission("bob")`
- **THEN** `entity.sexual.submission_marks` equals `frozenset({"alice", "bob"})`

#### Scenario: An unmarked entity reads an empty set
- **WHEN** `entity.sexual.submission_marks` is read on an entity that has never had `mark_submission()`
  called
- **THEN** it returns `frozenset()`

### Requirement: restore_purity() bypasses the public virgin setter without weakening its one-way contract
`SexualState.restore_purity()` SHALL set `virgin` to `True` by writing the underlying attribute
directly, bypassing the public `virgin` property's setter (which is unconditionally a no-op once
`virgin` is `False`). It SHALL NOT modify `experience_types`. Calling it on an entity whose `virgin` is
already `True` SHALL be a no-op producing no error.

#### Scenario: restore_purity reverses a False virgin flag
- **WHEN** `entity.sexual.virgin` has been set to `False` through the public setter, and
  `entity.sexual.restore_purity()` is then called
- **THEN** `entity.sexual.virgin` reads `True` afterward

#### Scenario: experience_types is unaffected by restore_purity
- **WHEN** `entity.sexual.experience_types` contains `"陰道性交"` and `entity.sexual.restore_purity()`
  is called
- **THEN** `entity.sexual.experience_types` still contains `"陰道性交"`, unchanged

#### Scenario: The public setter's one-way guarantee still holds after restore_purity exists
- **WHEN** `entity.sexual.virgin` is set to `False` through the public setter, `restore_purity()` is
  called (setting it back to `True`), and then the public setter is used to attempt setting it `False`
  and then `True` again
- **THEN** the public setter's own existing scenario still holds unmodified: once the public setter
  itself sets `virgin` to `False`, no later mutation through that same public setter can set it back to
  `True` — `restore_purity()` is a separate path and does not change this

#### Scenario: restore_purity on an already-virgin entity is a no-op, not an error
- **WHEN** `entity.sexual.restore_purity()` is called on an entity whose `virgin` is already `True`
- **THEN** `entity.sexual.virgin` remains `True` and no exception is raised
