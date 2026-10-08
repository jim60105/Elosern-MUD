## Purpose

Define defer active examiner schedules and replay held departures once after settlement as observable deterministic behavior with explicit rejection and acceptance boundaries.

## ADDED Requirements

The complete scheduler hold/read/release behavior defined below SHALL be available independently of production examination starts. Lifecycle SHALL wire activation/release only after this predecessor lands; availability-reader integration belongs to its dependent reader change. Scenarios in this predecessor use real synthetic NPCs and exam identities.

### Requirement: Active exams defer host schedule occurrences and release through shared traversal
Exam-owned persisted timing/hold state SHALL defer movement and state occurrences only for the active host. Terminal settlement SHALL restore normal state then consume held occurrences in authored due/index order via ordinary occurrence/traversal machinery, without a second clock advance. Existing effective-from, silencing, locks/vetoes and per-entry failure isolation SHALL remain authoritative.

#### Scenario: Weekly departure crossed
- **WHEN** combat time crosses the host weekly departure
- **THEN** after settlement the departure traverses its real Exit once and host is not stranded another week

#### Scenario: Other NPC
- **WHEN** another resident has due entries during the held exam
- **THEN** its schedule settles unchanged

### Requirement: Held interval release is recoverable and idempotent
Persisted exam/session timing and authoritative schedule SHALL recover held intervals and consumed-through identity, with storage/cache rollback at release boundaries. Valid resumed exam SHALL retain hold; invalid recovery SHALL close/restore then release. Startup source registration SHALL precede recovery clock settlement. Reader SHALL return unavailable for indeterminate hold, with no booking queue.

#### Scenario: Crash/retry release
- **WHEN** cold start occurs before or after a terminal release commit
- **THEN** pending held occurrences execute once, completed ones do not replay, world tick is not advanced twice

#### Scenario: Fault release
- **WHEN** persistence fails while release is staged
- **THEN** snapshots restore held marker/location/state/caches and retry has no duplicated traversal

