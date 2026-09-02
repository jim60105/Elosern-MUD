## ADDED Requirements

### Requirement: Successful commits emit an action_commit boundary event

Every deterministic action commit path in `world/rules/action.py` SHALL emit
one `action_commit` info event through the `world.observability` facade after
the durable commit, with `char`, `action`, and `ms` context. Failed or
rolled-back resolutions MUST NOT emit the event. Boundary events MUST NOT
change the all-or-nothing resolution semantics.

#### Scenario: A resolved action leaves one commit event

- **WHEN** an action resolution commits successfully
- **THEN** exactly one `action_commit` event is logged with the actor, the
  action identity, and elapsed milliseconds

#### Scenario: A rolled-back resolution emits no commit event

- **WHEN** resolution fails after staging and the transaction rolls back
- **THEN** no `action_commit` event is logged for that attempt
