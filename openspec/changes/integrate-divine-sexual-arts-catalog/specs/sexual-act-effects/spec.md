## RENAMED Requirements

- FROM: `### Requirement: sexual_event:<name> entries in an act's effects reuse the existing handler and dispatch table unchanged`
- TO: `### Requirement: sexual_event:<name> entries resolve through the participant-scoped handler with no name-based exception table`

## MODIFIED Requirements

### Requirement: sexual_event:<name> entries resolve through the participant-scoped handler with no name-based exception table
Every `sexual_event:<name>` string an effect list carries (appended by `_act_family()` per
`sexual-act-registry`'s corresponding requirement, or hand-declared) SHALL resolve through the
existing `_handle_sexual_event` handler and `SexualEventEffect` dispatch branch. The handler SHALL
apply the event to **every participant** of the cast — `participants(actor, targets)`, exactly like
the pleasure and counter handlers — with **no name-based recipient exception**:
`_builder.py`'s `_LEGACY_TARGET_SCOPED_EVENTS` SHALL NOT exist in any form, and the handler SHALL
NOT read any event-name exception set. Recipient scope SHALL be decided statically by the effect
prefix alone: `sexual_event:` participant-scoped, `sexual_event_actor:` actor-scoped,
`sexual_event_target:` target-scoped (see the added requirement). `_FORBIDDEN_SEXUAL_EVENTS` is
unrelated to recipient scope and remains the act-catalog emission prohibition alone.

#### Scenario: An act's declared event calls apply_event for every participant
- **WHEN** an act whose `sexual_events` includes `"breast_sex_performed"` is cast against one target
- **THEN** `apply_event` is invoked with event name `"breast_sex_performed"` for the actor and for
  the target — never the target alone

#### Scenario: stimulus_applied is no longer name-special-cased in the participant handler
- **WHEN** a hypothetical skill declares `effects=["sexual_event:stimulus_applied"]` and is cast
  against one target
- **THEN** `apply_event` is invoked with `"stimulus_applied"` for every participant including the
  actor — the old target-scoped exception is gone and the plain prefix is unambiguously
  participant-scoped for every name

#### Scenario: A SELF act's event still reaches exactly the actor
- **WHEN** a `TargetSpec.SELF` act whose `sexual_events` includes `"masturbation_climax"` is cast
- **THEN** `apply_event` is invoked with `"masturbation_climax"` for the actor exactly once

#### Scenario: The builder keeps no legacy recipient table
- **WHEN** `world/skills/sexual_acts/_builder.py`'s module namespace is inspected
- **THEN** no `_LEGACY_TARGET_SCOPED_EVENTS` binding exists, while `_FORBIDDEN_SEXUAL_EVENTS` remains
  present and unchanged

## ADDED Requirements

### Requirement: sexual_event_target:<name> applies the named event to the resolved targets only
`world/rules/action.py` SHALL register the `sexual_event_target:<name>` prefix (surfaces
`frozenset({"sexual"})`, no required event context), parsed by `world/skills/effects.py`'s
`TargetSexualEventEffect(event_name)`. The handler SHALL stage one `PendingEffect` calling
`apply_event(target, event_name, ...)` per resolved target and SHALL never apply the event to the
acting entity, mirroring `sexual_event_actor:<name>` with the roles exchanged. A missing or empty
event name SHALL be rejected the same way the actor-scoped handler rejects it. An empty `targets`
list (a fully resisted cast) SHALL be an ordinary no-op outcome, never a rejection. The prefix SHALL
not carry observer gating: `watched_during_activity` remains reachable only through the actor-scoped
channel's gated vocabulary.

#### Scenario: divine_sexual_arts stimulates the target and never the caster
- **WHEN** `divine_sexual_arts` (declaring `sexual_event_target:stimulus_applied`) is cast against
  one non-resisting target
- **THEN** `apply_event` is invoked with `"stimulus_applied"` for the target only, and the actor's
  sexual state is untouched by that event

#### Scenario: A fully resisted target-scoped cast succeeds as a no-op
- **WHEN** `divine_sexual_arts` is cast against a sole target whose resist contest resolves
  `resisted=True`
- **THEN** the cast succeeds, the resist verdict is logged, `apply_event` is not invoked for the
  event, and no `RejectedAction` is raised

#### Scenario: An AREA target-scoped event reaches every surviving target
- **WHEN** a hypothetical skill declaring `sexual_event_target:breast_sex_performed` is cast at an
  AREA whose resolved targets are three entities besides the actor
- **THEN** `apply_event` is invoked once for each of the three targets and never for the actor

#### Scenario: An empty event name is rejected
- **WHEN** a skill declaring `effects=["sexual_event_target:"]` is cast
- **THEN** the cast is rejected with `RejectReason.EFFECT_RESOLUTION_FAILED`, mirroring the
  actor-scoped handler's rejection
