# persona-dialogue-injection Specification

## Purpose
Feed the persona blocks produced by `PersonaStore` into the NPC dialogue prompt — the speaking
NPC's own persona in the system message and the speaking player's persona as `player.persona` in
the user payload — and generalize the per-call no-leak validator from affinity-only to a bounded
secret set that also covers true trait values under an active disguise, all read-only and
value-passing across the single-writer boundary.

## Requirements

### Requirement: The NPC's own persona feeds the dialogue system message
The NPC dialogue system message SHALL be rendered from the prompt library's `npc_dialogue.system` key with a `persona` value supplied from `PersonaStore.flatten()` on the speaking NPC called with the compact NPC card's render order — `identity`, `appearance`, `personality`, `speech_style`, `life_story`, `habit`, `social_connection` — so the NPC's own flattened block includes its hidden identity layer and its explicit speech style, with no truncation for a valid card.

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

#### Scenario: The persona frame wraps a present block
- **WHEN** a flattened persona block is present for the speaking NPC
- **THEN** it is wrapped by the prompt library's `npc_dialogue.persona_frame` text, which states that this is the NPC's current character setting governing subsequent replies and that earlier conversation and confirmed events are history that the current setting does not rewrite

#### Scenario: The persona placeholder is substituted on every call
- **WHEN** a dialogue system message is rendered, with or without a persona block
- **THEN** the `{persona}` placeholder is substituted on every call — the flattened block when present, an empty string when not — and the empty-substitution output is byte-identical to today's pre-persona system message

#### Scenario: The injected block arrives already capped
- **WHEN** a persona record would flatten past the `PersonaStore` contract's cap
- **THEN** the flattened block is capped by that contract before injection

#### Scenario: Persona content never overrides mechanical values
- **WHEN** an injected persona block carries structural-key content
- **THEN** that content never overrides mechanical values

#### Scenario: No prompt template or persona constant lives in the module
- **WHEN** the dialogue prompt-building module's source is inspected
- **THEN** it embeds neither the template nor the persona text as a Python constant

### Requirement: The player's persona feeds the user payload as player.persona
`build_npc_dialogue_prompt(...)` SHALL accept an optional `player_persona` block and serialize it as `player.persona` beside `player.affinity` when present. The block SHALL be flattened from a public view of the player's persona record with the field set limited to exactly `identity` (public layer only), `appearance`, and `social_connection`.

#### Scenario: A player with persona is recognized by the NPC
- **WHEN** a prompt is built for a speaking player whose persona record flattens to a block
- **THEN** the user payload carries `player.persona` with the flattened block

#### Scenario: The player's hidden identity never reaches the NPC prompt
- **WHEN** a prompt is built for a player whose persona `identity` is a mapping containing a `hidden` entry
- **THEN** `player.persona` contains the 公開身分 line and no 隱秘身分 line or hidden value

#### Scenario: Player prose never reaches the NPC prompt
- **WHEN** a prompt is built for a player whose persona record carries all of `personality`, `life_story`, `habit`, and `background`
- **THEN** `player.persona` contains none of the 性格／人生經歷／習慣／背景 labeled sections or their values, while the 公開身分, 外觀, and 人脈 sections are present when set

#### Scenario: A player without persona omits the block
- **WHEN** a prompt is built for a player with no persona record
- **THEN** the user payload contains no `player.persona` key

#### Scenario: Hidden identity is excluded by construction
- **WHEN** the record's `identity` is a mapping
- **THEN** its `hidden` entry is excluded from the block by construction before flattening, never by post-hoc text scrubbing

#### Scenario: A plain-string identity renders as-is
- **WHEN** the record's `identity` is a plain string rather than a mapping
- **THEN** it renders as-is in the block

#### Scenario: The field set reflects how the NPC reads the player
- **WHEN** the player field set is applied
- **THEN** the prose fields `personality`, `life_story`, and `habit` and the `background` key are not part of it — the NPC reads the player only through appearance, public identity, and the NPC's own social-connection notes

#### Scenario: No block keeps the payload byte-identical
- **WHEN** a player has no flattened block
- **THEN** the produced payload is byte-identical to today's output

#### Scenario: Prompt building never writes persona state
- **WHEN** a prompt is built with a player persona block
- **THEN** building the prompt never creates, persists, or mutates a persona record — the block is read-only context

### Requirement: The no-leak validator binds a per-call bounded secret set including disguise true values
The reply no-leak check SHALL be installed for a call whenever its secret set is non-empty —
independently of whether an affinity context exists — and SHALL validate speech against that
per-call set: the affinity value and cap (when present) plus the true trait values of `atk_phys`,
`agility`, `defense`, `magic_power`, and `hp` when the NPC has an active `disguised_stats` record
whose value for that key differs from the true trait value.

#### Scenario: Secret values are read from the current trait values
- **WHEN** the five disguise-comparable traits are bound as secrets
- **THEN** all five values are read from the traits' current `.value` (for `hp`, the current gauge value, not the maximum)

#### Scenario: A leaked secret fails, retries, and degrades to None
- **WHEN** a reply's speech contains any bound secret as a decimal integer substring, with fullwidth digit forms folded via NFKC normalization
- **THEN** the reply is treated as a validation failure and retried within the budget, and on budget exhaustion the call degrades to `None` rather than present the leak

#### Scenario: Binding rides the per-call request descriptor
- **WHEN** calls interleave
- **THEN** each secret set is bound per call through the request descriptor so interleaved calls never cross-contaminate

#### Scenario: Stage names stay allowed
- **WHEN** a reply mentions stage names
- **THEN** stage names remain allowed by the no-leak validator

#### Scenario: No secrets means no installed check
- **WHEN** no disguise is active and no affinity context exists
- **THEN** the secret set is empty and no leak check is installed

#### Scenario: A reply echoing a disguised true value is retried
- **WHEN** an NPC with an active disguise (true `atk_phys` 88 disguised as 60) receives a reply
  whose speech contains "88"
- **THEN** the output is rejected by the no-leak validator and retried within the budget, while a
  speech containing "60" passes

#### Scenario: The leak check fires without any affinity record
- **WHEN** an NPC with an active disguise faces a player with no affinity record
- **THEN** the call still installs the no-leak validator over the disguise true values, and a
  reply echoing one of them is rejected and retried, while a player-facing conversation that
  never echoes them proceeds normally

#### Scenario: hp is protected at its current gauge value
- **WHEN** an NPC has a disguise whose `hp` differs from the true current `hp.value` (and
  `hp.value != hp.max`)
- **THEN** the current `hp.value` is bound as a secret and a reply echoing it is rejected, while
  the maximum is not treated as the protected value

#### Scenario: No disguise adds no extra bindings
- **WHEN** the NPC has no `disguised_stats` record or every disguise value equals the true value
- **THEN** the secret set is exactly the affinity value and cap (or empty when no affinity
  context exists), and existing affinity-only leak behavior is unchanged

#### Scenario: The secret set is per-call isolated
- **WHEN** two calls with different disguise/affinity contexts run concurrently
- **THEN** each reply is validated only against its own call's secrets, never the other call's
  numbers

### Requirement: Persona wiring is read-only and value-passing
The persona blocks and the extended secret set SHALL be computed in `typeclasses/npcs.py`
(read-only via `PersonaStore` and trait reads) and passed as plain values through the existing
dialogue context; `world/ai/npc_dialogue.py` SHALL NOT import entities, typeclasses, or any
state-mutating module, and SHALL NOT write persona, affinity, trait, or dialogue state.

#### Scenario: world/ai receives values, never entities
- **WHEN** the dialogue prompt-building module's imports and call signatures are inspected
- **THEN** it receives persona blocks and secrets as plain values and contains no typeclass or
  writer import

#### Scenario: Building a prompt never mutates persona state
- **WHEN** a prompt is built for an NPC and player with persona records
- **THEN** both `entity.db.persona` records remain byte-identical before and after
