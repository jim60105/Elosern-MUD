## ADDED Requirements

### Requirement: Async dialogue intents revalidate context at completion

When an async NPC exchange completes, the system SHALL revalidate that the player and the NPC are still co-located and that the NPC is still interactable before applying the reply's intent; a stale completion SHALL display the speech but discard the intent with a clear message.

#### Scenario: Intent is dropped after separation

- **WHEN** an async reply completes after the player or NPC left the room
- **THEN** the speech is shown and no intent (give/take item, adjust relation, reveal lore) is applied

#### Scenario: Intent is dropped when the NPC becomes busy

- **WHEN** an async reply completes after the NPC entered a `busy`/`resting` schedule state
- **THEN** the speech is shown and no intent is applied

#### Scenario: Co-located interactive completion applies the intent

- **WHEN** an async reply completes while both parties remain co-located and the NPC is interactable
- **THEN** the intent applies through its existing per-kind validation
