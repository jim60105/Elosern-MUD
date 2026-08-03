## MODIFIED Requirements

### Requirement: SINGLE and AREA target specs filter candidates differently
Target-shape validation SHALL run before candidate validation. `TargetSpec.NONE` SHALL accept no candidates. `TargetSpec.SELF` SHALL accept empty input normalized to the actor or exactly one explicit candidate identical to the actor, preserving trusted direct policy requests while rejecting every other shape. `TargetSpec.SINGLE` SHALL require exactly one explicit candidate and SHALL reject shorthand. `TargetSpec.AREA` SHALL require either a nonempty explicit candidate list with no duplicate object identity or one approved shorthand. A shape violation SHALL reject with `RejectReason.TARGET_SPEC_MISMATCH` before candidate validation. After shape validation, SELF and SINGLE candidate failure SHALL reject the entire action with the first of the four ordered validation reasons. AREA candidates SHALL be validated independently and invalid candidates SHALL be silently dropped; a valid AREA input whose final target list is empty after filtering SHALL reject with `RejectReason.NO_VALID_TARGETS_IN_AREA` before effect resolution or resource deduction.

#### Scenario: SINGLE rejects the whole action on one invalid target
- **WHEN** a `TargetSpec.SINGLE` skill is resolved against one dead target
- **THEN** the action rejects with `RejectReason.TARGET_DEAD` and no `PendingEffect` is staged

#### Scenario: AREA silently drops one invalid candidate among several valid ones
- **WHEN** a `TargetSpec.AREA` skill is resolved against three distinct candidates, one of which is dead
- **THEN** the action proceeds to effect resolution against the two surviving candidates, and the dead candidate is absent from the final target list with no rejection

#### Scenario: AREA rejects when every candidate is filtered out
- **WHEN** a `TargetSpec.AREA` skill's valid shorthand expands to candidates that are all dead or all absent
- **THEN** the action rejects with `RejectReason.NO_VALID_TARGETS_IN_AREA` before any resource is deducted

#### Scenario: NONE rejects supplied targets
- **WHEN** a NONE skill receives any explicit target or shorthand
- **THEN** it rejects with `RejectReason.TARGET_SPEC_MISMATCH` rather than silently ignoring caller input

#### Scenario: SELF binds only the request actor
- **WHEN** a SELF skill receives no caller target
- **THEN** target resolution binds and validates the actor; a trusted direct request containing exactly that actor behaves identically, while any other explicit candidate rejects as a shape mismatch

#### Scenario: Duplicate AREA input cannot repeat an effect
- **WHEN** an explicit AREA list contains the same object identity more than once
- **THEN** it rejects with `RejectReason.TARGET_SPEC_MISMATCH` before filtering, effect staging, or resource deduction

### Requirement: Combat shortcuts expand to an explicit list and pass the same four validations
`expand_target_shorthand(actor, context, shorthand)` SHALL resolve `all-enemies`, `all-allies`, and `all` into an explicit deterministic candidate list of live entity values drawn from `context.battlefield.roster`. Shorthand SHALL be accepted only for a `TargetSpec.AREA` skill. When the roster is a mapping keyed by entity key, expansion SHALL use its values rather than its keys. The resulting candidates SHALL be validated by the identical four-step AREA-filtering logic used for an explicitly supplied target list; no validation SHALL be skipped. `all-allies` SHALL include both `Relation.ALLY` entities and the actor's `Relation.SELF` entity.

#### Scenario: A dead ally on the roster is filtered out of all-allies, not included
- **WHEN** `all-allies` expands to a roster mapping that includes one dead ally
- **THEN** the final target list, after the four validations run against every expanded entity, excludes the dead ally exactly as it would if that entity had been listed explicitly

#### Scenario: A mapping roster expands to entities rather than keys
- **WHEN** a battlefield roster is a `dict[str, LivingEntity]`
- **THEN** shorthand expansion returns the `LivingEntity` values and never passes string keys to `relation_to()` or the four validators

#### Scenario: all-allies includes the actor
- **WHEN** `all-allies` is expanded for an actor with one other same-team member
- **THEN** the candidate list contains both the actor and the other ally

#### Scenario: Shorthand tokens are meaningless out of combat
- **WHEN** `all-enemies` is supplied to `expand_target_shorthand()` with a context whose `battlefield` is `None`
- **THEN** it rejects with `RejectReason.TARGET_SPEC_MISMATCH`

#### Scenario: SINGLE cannot use a shorthand that happens to yield one target
- **WHEN** a SINGLE skill receives `all-enemies` in a battlefield containing exactly one enemy
- **THEN** target-shape validation rejects with `RejectReason.TARGET_SPEC_MISMATCH` before expansion can authorize it
