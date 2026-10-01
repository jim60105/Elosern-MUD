## ADDED Requirements

### Requirement: The NPC persona frame key is registered with exactly the block placeholder
The prompt registry SHALL register `npc_dialogue.persona_frame` in `prompts/npc_dialogue.yaml` with an allowlist of exactly `block`. Its text SHALL present `{block}` as the speaking NPC's current character setting that governs subsequent replies and SHALL state that earlier conversation and already confirmed events remain history the current setting does not rewrite. The NPC dialogue layer SHALL render it only when a persona block exists and SHALL pass the rendered frame as the `persona` value of `npc_dialogue.system`.

#### Scenario: The frame key is registered and consumed
- **WHEN** the prompt registry is queried for `npc_dialogue.persona_frame`
- **THEN** the key exists with its default text, its allowlist is exactly `block`, and a prompt built for an NPC with a card contains the rendered frame around the card block

#### Scenario: No frame without a card
- **WHEN** a prompt is built for an NPC with no persona block
- **THEN** the frame is not rendered and the system message is byte-identical to the pre-persona rendering
