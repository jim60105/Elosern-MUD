## MODIFIED Requirements

### Requirement: Casting a resistible act resolves one resist contest per non-actor target before its effects apply
`world/rules/action.py`'s `ActionResolver.resolve()` SHALL call `resist_verdict(actor, target,
rng=roll_d100)` (`world/rules/sexual_resist.py`, unmodified) exactly once for every entity in the
resolved target list other than the acting entity, whenever the cast skill's key is present in
`SEXUAL_ACT_REGISTRY` and the corresponding `SexualActDef.resistible` is `True`. A non-catalog skill explicitly declaring a resistible interaction policy SHALL use the same single contest per non-actor target. A skill without either entitlement, including ordinary non-catalog spells and non-resistible sexual acts, SHALL trigger no contest. Declaring both sources SHALL never cause duplicate rolls.

#### Scenario: A resistible single-target act rolls one contest against its target
- **WHEN** an actor casts a `resistible=True`, `TargetSpec.SINGLE` act against one target
- **THEN** `resist_verdict(actor, target, rng=roll_d100)` is called exactly once with that actor/target
  pair

#### Scenario: A non-resistible act triggers no resist contest
- **WHEN** an actor casts a sexual act whose `SexualActDef.resistible` is `False`
- **THEN** `resist_verdict` is never called during that cast's resolution

#### Scenario: A non-sexual-act skill triggers no resist contest
- **WHEN** an actor casts a skill whose key is absent from `SEXUAL_ACT_REGISTRY` and has no resistible interaction policy
- **THEN** `resist_verdict` is never called during that cast's resolution

#### Scenario: A non-catalog contact spell uses one contest
- **WHEN** a spell outside the sexual-act catalog declares a resistible contact policy
- **THEN** it resolves one ordinary resist contest per non-actor target and emits the existing sexual_resist outcome contract


### Requirement: The actor's own effects and the cast's resource, time, and practice cost are never gated by a target's resist outcome
For acts declared in `SEXUAL_ACT_REGISTRY` (not generic contact spells), regardless of any target's `ResistVerdict`, `ActionResolver.resolve()` SHALL apply the cast's own
`actor_counters` and the actor's own pleasure share to the acting entity, SHALL deduct the skill's
declared resource cost from the actor, SHALL grant skill-practice XP to the actor, and SHALL return
`ActionResult.outcome == "success"` — none of these SHALL depend on whether any target resisted, including
when every target in the cast resists.

#### Scenario: A fully-resisted single-target cast still succeeds and still costs the actor
- **WHEN** an actor casts a `resistible=True`, `TargetSpec.SINGLE` act whose one target's contest
  resolves `resisted=True`
- **THEN** `ActionResult.outcome` equals `"success"`, the actor's declared resource cost is deducted, and
  every counter named in the act's `actor_counters` is credited to the actor

#### Scenario: A fully-resisted cast still applies the actor's own pleasure share
- **WHEN** an actor casts a `resistible=True` act whose only target's contest resolves `resisted=True`
- **THEN** the actor's own `pleasure` increases by the share computed from the act's `base_pleasure`
  and `actor_pleasure_ratio` over the post-resist participant set (the actor remains a participant even
  when every target resists; the participant-count crowd multiplier is applied to the post-resist set,
  per design D-7), and the resisting target's `pleasure` is unchanged
