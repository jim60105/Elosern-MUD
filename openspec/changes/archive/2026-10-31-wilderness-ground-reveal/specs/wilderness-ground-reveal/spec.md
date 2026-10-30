# Spec Delta

## Purpose

Record maximum settled sight and derive permanent reveal without read writes. This capability owns its observable mechanism and rejection boundaries.

## ADDED Requirements

### Requirement: Ground observations are monotonic and transactional
Wilderness arrival and positive completed explicit skips SHALL record character-owned maximum ground radius at the final settled cell and tick inside the owning transaction.

#### Scenario: Same-cell daylight and rollback
- **WHEN** a low-sight character waits until larger daylight sight and a later operation fails after writing
- **THEN** successful sight increases without later decrease and failure restores durable/cached prior history

#### Scenario: Skip variants and exclusions
- **WHEN** wait/rest, self/party sleep or forced continuation commits or replays/refuses
- **THEN** each positive interval observes its end once; zero/replay/refusal/read/teleport does not

### Requirement: Permanent reveal is a bounded read projection
A wilderness cell SHALL reveal from valid lit ownership or a stored visit disc, while hidden location identity requires actual visitation and read queries write nothing.

#### Scenario: Union and lit shortcut
- **WHEN** synthetic discs span chunk/query edges and another district landmark is visited
- **THEN** reveal equals independent disc/ownership results using only expanded intersecting chunks

#### Scenario: Hidden and corrupt history
- **WHEN** a hidden cell reveals or an observation chunk is malformed
- **THEN** terrain may reveal without location identity and corruption retains bytes while using only trusted lit knowledge
