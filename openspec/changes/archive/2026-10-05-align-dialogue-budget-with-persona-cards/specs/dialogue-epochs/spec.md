# dialogue-epochs Delta

## ADDED Requirements

### Requirement: Dialogue budgets admit the mandatory persona-card floor

The `npc_dialogue` rendered profile budget SHALL admit the mandatory dialogue
content of a fully-authored pair: an NPC persona block at the compact card's
full bound (2000 rendered code points, no truncation) rendered into the
character anchor, plus the speaking player's public persona block inside the
current frame, with zero optional material (no history, recall, or summary)
SHALL fit the profile's maximum input budget. Optional dialogue sections SHALL
be sized so content the aggregate input bound admits is never rejected later by
a section hard bound: after the deterministic reduction order (oldest replay
frames, then chat-memory lines, then recall cognition, then epoch summary) has
converged inside the aggregate bound, the final prompt SHALL be accepted rather
than degraded. Rejection of mandatory overflow SHALL remain the only budget
failure path, and mandatory content SHALL never be silently removed.

#### Scenario: A full-card pair converses without degradation

- **WHEN** a dialogue context is built for an NPC whose persona card is at the
  full compact-card bound and a speaking player whose public persona record
  flattens to a block
- **THEN** context building succeeds with the full NPC card and the player's
  persona present in the prompt, the captured accounting reports total rendered
  tokens at or below its max input budget, and the exchange is not degraded to
  the authored greeting by a budget failure

#### Scenario: Oversized optional history reduces before rejection

- **WHEN** replayed epoch frames and chat-memory lines push the assembled pair
  prompt beyond the profile's maximum input budget
- **THEN** frames and memory drop oldest-first, then cognition and epoch
  summary, until the prompt fits, and only a still-overflowing mandatory
  current frame rejects
