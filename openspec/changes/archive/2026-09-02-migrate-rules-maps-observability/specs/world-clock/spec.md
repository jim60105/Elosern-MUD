## ADDED Requirements

### Requirement: Clock advance and restore failures emit observability events

`WorldClock.advance()` SHALL emit one `clock_advance` info event through the
`world.observability` facade on successful commit, with `tick_from`,
`tick_to`, and `scope` context. Every best-effort attribute-restore failure
inside advance/rollback paths SHALL emit a `rollback_restore_failed` warn
event carrying the failed attribute `key`, the affected `obj` identity, and
the exception chain, instead of passing silently. Emitting events MUST NOT
change the atomic persistence or restore semantics.

#### Scenario: A successful advance leaves one boundary event

- **WHEN** `advance()` commits normally for a supplied scope
- **THEN** exactly one `clock_advance` event is logged with the tick range in
  context

#### Scenario: A swallowed restore failure becomes visible

- **WHEN** a restore during a rolled-back advance raises and is swallowed to
  preserve the original exception
- **THEN** a `rollback_restore_failed` warn event identifies the key, the
  object, and the exception in context, and the original exception still
  propagates unchanged
