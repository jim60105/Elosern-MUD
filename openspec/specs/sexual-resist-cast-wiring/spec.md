# sexual-resist-cast-wiring Specification

## Purpose

Define the in-combat resist wiring that turns a `resistible=True` sexual act's cast into an actual
resist contest: `ActionResolver.resolve()` calls `resist_verdict()` once per non-actor resolved target,
emits the `sexual_resist` `EventEntry` contract that `sexual-resist-turn-cost`'s coercion scan already
consumes, and excludes a successfully-resisting target from the act's pleasure, counter, and
sexual-event effects while never gating the actor's own effects or the cast's resource, time, or
practice cost on any target's outcome.

## Requirements

### Requirement: Casting a resistible act resolves one resist contest per non-actor target before its effects apply
`world/rules/action.py`'s `ActionResolver.resolve()` SHALL call `resist_verdict(actor, target,
rng=roll_d100)` (`world/rules/sexual_resist.py`, unmodified) exactly once for every entity in the
resolved target list other than the acting entity, whenever the cast skill's key is present in
`SEXUAL_ACT_REGISTRY` and the corresponding `SexualActDef.resistible` is `True`. A skill absent from
`SEXUAL_ACT_REGISTRY`, or a sexual act declaring `resistible=False`, SHALL trigger no resist contest and
SHALL behave exactly as before this change.

#### Scenario: A resistible single-target act rolls one contest against its target
- **WHEN** an actor casts a `resistible=True`, `TargetSpec.SINGLE` act against one target
- **THEN** `resist_verdict(actor, target, rng=roll_d100)` is called exactly once with that actor/target
  pair

#### Scenario: A non-resistible act triggers no resist contest
- **WHEN** an actor casts a sexual act whose `SexualActDef.resistible` is `False`
- **THEN** `resist_verdict` is never called during that cast's resolution

#### Scenario: A non-sexual-act skill triggers no resist contest
- **WHEN** an actor casts a skill whose key is absent from `SEXUAL_ACT_REGISTRY`
- **THEN** `resist_verdict` is never called during that cast's resolution

### Requirement: A resistible AREA-target act resolves one independent contest per resolved target
`ActionResolver.resolve()` SHALL NOT branch its resist-contest logic on `SkillDef.target_spec`: for a
`TargetSpec.AREA` cast resolving against more than one target, it SHALL call `resist_verdict()` once per
resolved target, independently, so each target's outcome depends only on that target's own contest.

#### Scenario: An AREA act rolls one independent contest per target
- **WHEN** an actor casts a `resistible=True`, `TargetSpec.AREA` act that resolves against two targets
- **THEN** `resist_verdict` is called exactly twice, once for each target, and one target's verdict does
  not determine the other's

### Requirement: A successfully-resisting target receives none of the act's pleasure, counter, or sexual-event effects
When a target's `resist_verdict()` call returns `resisted=True`, `ActionResolver.resolve()` SHALL exclude
that target from the target list passed to the cast's `pleasure:`/`sexual_counter:`/`sexual_event:`
effect handlers, so that target's `pleasure`, lifetime counters, and `SexualState` fields are unchanged by
the cast. A target whose verdict returns `resisted=False` (whether by a rolled comply or an
`auto_comply=True` short circuit) SHALL receive the act's effects exactly as it would without this change.

#### Scenario: A resisted target's pleasure and counters are unchanged
- **WHEN** an actor casts a `resistible=True` act against a target whose `resist_verdict()` call resolves
  `resisted=True`
- **THEN** the target's `pleasure` value and every counter named in the act's `participant_counters` are
  unchanged after the cast

#### Scenario: A complying target receives the act's effects as before
- **WHEN** an actor casts a `resistible=True` act against a target whose `resist_verdict()` call resolves
  `resisted=False`
- **THEN** the target's `pleasure` and declared counters change exactly as they would for a
  `resistible=False` act with the same `base_pleasure`, part, and counter declarations

### Requirement: Every resist contest emits a sexual_resist EventLog entry matching the sexual-resist-turn-cost contract
For every target a resist contest is rolled against, the returned `ActionResult.event_log.entries` SHALL
contain exactly one `EventEntry` with `kind == "sexual_resist"`, `target` equal to that target's
`str(target.key)`, and `data` containing exactly the keys `resisted` (`bool`), `auto_comply` (`bool`), and
`roll` (`int` or `None`, `None` exactly when `auto_comply` is `True`), reflecting that target's own
`ResistVerdict`.

#### Scenario: A rolled contest logs its numeric roll
- **WHEN** a target's `resist_verdict()` call resolves with `auto_comply=False` and a numeric `roll`
- **THEN** the cast's `EventLog` contains one `sexual_resist` entry for that target with `data["roll"]`
  equal to that numeric value

#### Scenario: An auto-complied contest logs a null roll
- **WHEN** a target's `resist_verdict()` call resolves with `auto_comply=True`
- **THEN** the cast's `EventLog` contains one `sexual_resist` entry for that target with `data["roll"]`
  equal to `None` and `data["auto_comply"]` equal to `True`

### Requirement: The actor's own effects and the cast's resource, time, and practice cost are never gated by a target's resist outcome
Regardless of any target's `ResistVerdict`, `ActionResolver.resolve()` SHALL apply the cast's own
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
