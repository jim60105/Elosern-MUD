## MODIFIED Requirements

### Requirement: The NPC's own persona feeds the dialogue system message
The NPC dialogue system message SHALL be rendered from the prompt library's `npc_dialogue.system` key with a `persona` value supplied from `PersonaStore.flatten()` on the speaking NPC called with the compact NPC card's render order — `identity`, `appearance`, `personality`, `speech_style`, `life_story`, `habit`, `social_connection` — so the NPC's own flattened block includes its hidden identity layer and its explicit speech style, with no truncation for a valid card; when a block is present it SHALL be wrapped by the prompt library's `npc_dialogue.persona_frame` text, which states that this is the NPC's current character setting governing subsequent replies and that earlier conversation and confirmed events are history that the current setting does not rewrite: the `{persona}` placeholder SHALL be substituted on every call — the flattened block when present, an empty string when not — and the empty-substitution output SHALL be byte-identical to today's pre-persona system message. The flattened block SHALL be capped by the `PersonaStore` contract before injection, the structural-key content SHALL never override mechanical values, and the module SHALL NOT embed the template or the persona text as a Python constant.

#### Scenario: An NPC with persona speaks in character
- **WHEN** a prompt is built for an NPC whose persona record contains personality, life story, and habits
- **THEN** the system message contains the flattened labeled block (性格：… / 人生經歷：… / 習慣：…) through the `{persona}` placeholder, rendered via the prompt library

#### Scenario: The NPC sees its own hidden identity
- **WHEN** a prompt is built for an NPC whose persona `identity` is a mapping with `public` and `hidden` entries
- **THEN** the system message's persona block contains the 隱秘身分 line alongside the 公開身分 line

#### Scenario: An NPC without persona keeps today's system message
- **WHEN** a prompt is built for an NPC with no persona record
- **THEN** `persona=""` is substituted into `{persona}` and the system message is byte-identical to the pre-persona rendering with no persona token or empty block present

#### Scenario: The NPC's speech style reaches the prompt beside its personality
- **WHEN** a prompt is built for an NPC carrying a valid compact card
- **THEN** the persona block contains every non-empty card section in render order with the 說話風格 section immediately after the 性格 section, no truncation marker, and the current-setting frame from the prompt library
