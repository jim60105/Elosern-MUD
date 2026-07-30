## MODIFIED Requirements

### Requirement: Combat shortcuts expand to an explicit list and pass the same four validations
`expand_target_shorthand(actor, context, shorthand)` SHALL resolve `"all-enemies"`,
`"all-allies"`, and `"all"` into an explicit candidate list of live entity values drawn from
`context.battlefield.roster`. When the roster is a mapping keyed by entity key, expansion SHALL use
its values rather than its keys. The resulting candidates SHALL be validated by the identical
four-step, `AREA`-filtering logic used for an explicitly named target list — no validation SHALL be
skipped for shorthand-expanded candidates.
`"all-allies"` SHALL include both `Relation.ALLY` entities and the actor's `Relation.SELF` entity.

#### Scenario: A dead ally on the roster is filtered out of all-allies, not included
- **WHEN** `"all-allies"` expands to a roster mapping that includes one dead ally
- **THEN** the final target list, after the four validations run against every expanded entity,
  excludes the dead ally exactly as it would if that entity had been listed explicitly

#### Scenario: A mapping roster expands to entities rather than keys
- **WHEN** a battlefield roster is a `dict[str, LivingEntity]`
- **THEN** shorthand expansion returns the `LivingEntity` values and never passes string keys to
  `relation_to()` or the four validators

#### Scenario: all-allies includes the actor
- **WHEN** `"all-allies"` is expanded for an actor with one other same-team member
- **THEN** the candidate list contains both the actor and the other ally

#### Scenario: Shorthand tokens are meaningless out of combat
- **WHEN** `"all-enemies"` is supplied to `expand_target_shorthand()` with a context whose
  `battlefield` is `None`
- **THEN** it rejects with `RejectReason.TARGET_SPEC_MISMATCH`
