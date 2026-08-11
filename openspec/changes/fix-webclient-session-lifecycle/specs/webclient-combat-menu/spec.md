## ADDED Requirements

### Requirement: Terminal combat outcomes refresh all mode-relevant panels

A terminal combat result (victory, defeat, flee, forfeit, exam outcome) SHALL publish a full snapshot (or equivalently refresh every panel the mode change touches: exploration, character, services, local_map, status, context_actions, art), so no panel retains pre-combat or combat-stale state after the mode returns to exploration.

#### Scenario: Exploration panels are fresh after a terminal outcome

- **WHEN** a combat session ends terminally and the mode switches back to exploration
- **THEN** the exploration/character/services/local_map payloads reflect the post-settlement canonical state (defeated monster gone, current HP, settled world time)

#### Scenario: Non-terminal rounds keep partial updates

- **WHEN** an ordinary (non-terminal) combat round completes
- **THEN** the existing status/context_actions/art partial update is unchanged
