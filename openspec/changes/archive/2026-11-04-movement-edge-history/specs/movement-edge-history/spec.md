# Spec Delta

## Purpose

Retain stable completed physical edges and expose their real legality and execution pricing independently of pooled room identities.

## ADDED Requirements

### Requirement: Completed physical edges retain stable player history
Player movement SHALL atomically retain its last completed physical edge by stable location identity, with legal execution-price queries and passage visibility independent of early room relocation.

#### Scenario: Recycled wilderness source
- **WHEN** a paid edge completes, its pooled source room recycles and the body reloads
- **THEN** history still names the original map/cell and actual destination; querying it creates no room or state

#### Scenario: Failure and teleport
- **WHEN** an attempted traversal rolls back or the controlled body teleports
- **THEN** rollback preserves prior history and teleport invalidates it, without retaining an unrelated reverse route

#### Scenario: Possessed party
- **WHEN** a controlled companion completes a physical gate edge with present and remote party members
- **THEN** actual transported bodies retain the edge and remote bodies remain unchanged; a later reverse quote checks current locks

#### Scenario: Shared quote and passage
- **WHEN** an actual edge has terrain/fatigue, corner/access restrictions or exact arrival depletion
- **THEN** quote and execution agree under the canonical price; the party is exposed at neither idle endpoint during passage and no routing fallback authorizes it

