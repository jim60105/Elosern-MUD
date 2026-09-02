## ADDED Requirements

### Requirement: Quest lifecycle transitions emit boundary events

Every successful quest lifecycle transition (accept, stage transition,
abandon, complete, fail) SHALL emit one `quest_transition` info event
through the `world.observability` facade at the transition's durable
commit point, with `char`, `quest`, `stage_from`, and `stage_to` context.
Rolled-back lifecycle operations MUST NOT emit the event, and best-effort
quest-log restore failures SHALL surface as `rollback_restore_failed` warn
events instead of silent passes. Lifecycle atomicity and validation
semantics MUST NOT change.

#### Scenario: A stage transition leaves one boundary event

- **WHEN** a quest stage transition commits durably
- **THEN** exactly one `quest_transition` event is logged with the quest key
  and the from/to stage identities

#### Scenario: A rolled-back transition emits no event

- **WHEN** a lifecycle operation fails after staging and rolls back
- **THEN** no `quest_transition` event is logged for that attempt, and any
  swallowed quest-log restore failure appears as a `rollback_restore_failed`
  warn event
