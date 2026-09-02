# persona-dialogue-injection — Delta Spec

## MODIFIED Requirements

### Requirement: The NPC's own persona feeds the dialogue system message
The NPC dialogue system message SHALL be rendered from the prompt library's `npc_dialogue.system` key with a `persona` value supplied from `PersonaStore.flatten()` on the speaking NPC called with the full depth field set — `personality`, `life_story`, `habit`, `identity`, `appearance`, `social_connection` — so the NPC's own flattened block includes its hidden identity layer: the `{persona}` placeholder SHALL be substituted on every call — the flattened block when present, an empty string when not — and the empty-substitution output SHALL be byte-identical to today's pre-persona system message. The flattened block SHALL be capped by the `PersonaStore` contract before injection, the structural-key content SHALL never override mechanical values, and the module SHALL NOT embed the template or the persona text as a Python constant.

#### Scenario: An NPC with persona speaks in character
- **WHEN** a prompt is built for an NPC whose persona record contains personality, life story, and habits
- **THEN** the system message contains the flattened labeled block (性格：… / 人生經歷：… / 習慣：…) through the `{persona}` placeholder, rendered via the prompt library

#### Scenario: The NPC sees its own hidden identity
- **WHEN** a prompt is built for an NPC whose persona `identity` is a mapping with `public` and `hidden` entries
- **THEN** the system message's persona block contains the 隱秘身分 line alongside the 公開身分 line

#### Scenario: An NPC without persona keeps today's system message
- **WHEN** a prompt is built for an NPC with no persona record
- **THEN** `persona=""` is substituted into `{persona}` and the system message is byte-identical to the pre-persona rendering with no persona token or empty block present

### Requirement: The player's persona feeds the user payload as player.persona
`build_npc_dialogue_prompt(...)` SHALL accept an optional `player_persona` block and serialize it as `player.persona` beside `player.affinity` when present. The block SHALL be flattened from a public view of the player's persona record that includes `identity` (public layer only), `appearance`, and `social_connection` alongside the three prose fields: when the record's `identity` is a mapping, its `hidden` entry SHALL be excluded from the block by construction before flattening, never by post-hoc text scrubbing; a plain-string `identity` renders as-is. A player without a flattened block SHALL produce a payload byte-identical to today's output. Building the prompt SHALL never create, persist, or mutate a persona record — the block is read-only context.

#### Scenario: A player with persona is recognized by the NPC
- **WHEN** a prompt is built for a speaking player whose persona record flattens to a block
- **THEN** the user payload carries `player.persona` with the flattened block

#### Scenario: The player's hidden identity never reaches the NPC prompt
- **WHEN** a prompt is built for a player whose persona `identity` is a mapping containing a `hidden` entry
- **THEN** `player.persona` contains the 公開身分 line and no 隱秘身分 line or hidden value

#### Scenario: A player without persona omits the block
- **WHEN** a prompt is built for a player with no persona record
- **THEN** the user payload contains no `player.persona` key
