# Spec Delta

## ADDED Requirements

### Requirement: Every settled sleeper completes its own accepted wake plan
Every applicable deterministic party advance SHALL reconcile each living sleeper's own declared wake target, independent of the controlled body. Voluntary recovery SHALL include HP/MP/SP and mental targets; duration SHALL wait until its deadline. Wake SHALL change that body's posture/projection once without changing possession or reviving defeat/death. Live-combat natural wake SHALL retain terminal-only policy.

#### Scenario: Owner wakes while companion waits
- **WHEN** an awake possessed companion waits across its sleeping owner's recovery boundary
- **THEN** the owner becomes awake and its receipt completes once while session control remains on the companion

#### Scenario: Owner wakes while another companion sleeps
- **WHEN** continuation of a controlled companion's sleep reaches the owner's earlier voluntary target
- **THEN** owner posture reconciles awake despite the owner not being the explicitly continued member

#### Scenario: Reserve saturates before duration
- **WHEN** a duration sleeper reaches full reserve before its deadline during another body's local action
- **THEN** it remains asleep until the deadline while reserve clamps, and a later applicable advance wakes it

#### Scenario: Independent practice and resources
- **WHEN** a booked sleeping member reaches its target partway through an applicable interval and another member remains awake
- **THEN** sleeping time earns no practice and preserves the booking; any eligible later awake interval uses ordinary practice/resource rules without granting sleep recovery twice

### Requirement: Sleep receipts join complete party advance compensation
Sleep targets, per-body progress, wake state and completion notifications SHALL commit with the owning clock advance. Failure SHALL restore every touched persisted and cached resource, reserve, posture, projection, booking, receipt and clock surface. Technical failures SHALL report no completed wake; replay SHALL reuse the committed result.

#### Scenario: Late failure
- **WHEN** a fault occurs after clock/resource settlement and one body's wake write
- **THEN** all touched bodies and receipt/projection caches restore with the original tick and no wake-success notification
