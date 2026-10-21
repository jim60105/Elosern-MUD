# Spec Delta

## ADDED Requirements

### Requirement: Fatigue-aware movement restores all owning surfaces
Accepted movement SHALL atomically commit location, all intended followers, clock, mental/fractional state, forced sleep, map knowledge and owning effects. Failed settlement SHALL restore durable and cached state through existing owners without a second physiology or clock writer.

#### Scenario: Late fault rollback
- **WHEN** a fault follows follower relocation and mental/forced-sleep writes or occurs at outer commit
- **THEN** all travellers including the possessed owner body, locations/contents, wilderness bookkeeping, mental remainder, sleep, quest/knowledge surfaces and tick equal pre-move state in durable rows and live caches.

#### Scenario: Long accepted edge
- **WHEN** an authored edge exceeds the clock’s 86400-second call bound
- **THEN** bounded internal advances remain inside one movement transaction and snapshot the full window; the traversal rounds once and is never clipped to a daily cap.

