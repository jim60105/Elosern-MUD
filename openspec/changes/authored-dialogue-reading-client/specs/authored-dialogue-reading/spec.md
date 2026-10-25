# Spec Delta

## ADDED Requirements

### Requirement: Frontend completion retries remain memory-only
After explicit formal-scene finish, the client SHALL retry a failed completion acknowledgement in memory without requiring immediate rereading. It SHALL distinguish pending from saved and discard pending state on fresh reload, character exit or context retirement. No durable browser completion queue SHALL exist.

#### Scenario: Retry without rereading
- **WHEN** completion transport fails after the final explicit activation, then same-context transport recovers
- **THEN** the exact acknowledgement retries without another selection/effect and only saved response clears pending status

#### Scenario: Reload discards pending
- **WHEN** the app reloads before a failed acknowledgement saves
- **THEN** server unread/predecessor state wins and latest valid delivery restarts at line one

### Requirement: Optimistic public reading cannot unlock qualified topics
Local pending completion SHALL reveal only already delivered public-chain successors. Qualified topics SHALL wait for server-saved predecessors and current server eligibility. Unrelated reading updates SHALL not restart or auto-advance current playback.

#### Scenario: Pending public successor
- **WHEN** a root is locally finished but its acknowledgement is pending
- **THEN** its pre-delivered public successor can play and queues completion after predecessor, while protected descendant remains absent

#### Scenario: Other connection saves
- **WHEN** another current connection completes a topic while this connection reads another scene
- **THEN** markers synchronize without stealing focus or changing the current line

