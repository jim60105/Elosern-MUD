# persona-dialogue-injection Specification

## Purpose
Feed the persona blocks produced by `PersonaStore` into the NPC dialogue prompt — the speaking
NPC's own persona in the system message and the speaking player's persona as `player.persona` in
the user payload — and generalize the per-call no-leak validator from affinity-only to a bounded
secret set that also covers true trait values under an active disguise, all read-only and
value-passing across the single-writer boundary.

## Requirements

### Requirement: The NPC's own persona feeds the dialogue system message
The NPC dialogue system message SHALL be rendered from the prompt library's `npc_dialogue.system`
key with a `persona` value supplied from `PersonaStore.flatten()` on the speaking NPC: the
`{persona}` placeholder SHALL be substituted on every call — the flattened block when present, an
empty string when not — and the empty-substitution output SHALL be byte-identical to today's
pre-persona system message. The flattened block SHALL be capped by the `PersonaStore` contract
before injection, and the module SHALL NOT embed the template or the persona text as a Python
constant.

#### Scenario: An NPC with persona speaks in character
- **WHEN** a prompt is built for an NPC whose persona record contains personality, life story, and
  habits
- **THEN** the system message contains the flattened labeled block (性格：… / 人生經歷：… /
  習慣：…) through the `{persona}` placeholder, rendered via the prompt library

#### Scenario: An NPC without persona keeps today's system message
- **WHEN** a prompt is built for an NPC with no persona record
- **THEN** `persona=""` is substituted into `{persona}` and the system message is byte-identical
  to the pre-persona rendering with no persona token or empty block present

### Requirement: The player's persona feeds the user payload as player.persona
`build_npc_dialogue_prompt(...)` SHALL accept an optional `player_persona` block and serialize it
as `player.persona` beside `player.affinity` when present. A player without a flattened block
SHALL produce a payload byte-identical to today's output. Building the prompt SHALL never create,
persist, or mutate a persona record — the block is read-only context.

#### Scenario: A player with persona is recognized by the NPC
- **WHEN** a prompt is built for a speaking player whose persona record flattens to a block
- **THEN** the user payload carries `player.persona` with the flattened block

#### Scenario: A player without persona omits the block
- **WHEN** a prompt is built for a player with no persona record
- **THEN** the user payload contains no `player.persona` key

### Requirement: The no-leak validator binds a per-call bounded secret set including disguise true values
The reply no-leak check SHALL be installed for a call whenever its secret set is non-empty —
independently of whether an affinity context exists — and SHALL validate speech against that
per-call set: the affinity value and cap (when present) plus the true trait values of `atk_phys`,
`agility`, `defense`, `magic_power`, and `hp` when the NPC has an active `disguised_stats` record
whose value for that key differs from the true trait value. All five values SHALL be read from the
traits' current `.value` (for `hp`, the current gauge value, not the maximum). A reply whose
speech contains any bound secret as a decimal integer substring (fullwidth digit forms folded via
NFKC normalization) SHALL be treated as a validation failure, retried within the budget, and on
budget exhaustion degrade to `None` rather than present the leak. The binding SHALL be per call
through the request descriptor so interleaved calls never cross-contaminate; stage names SHALL
remain allowed; and when no disguise is active and no affinity context exists the set SHALL be
empty and no leak check SHALL be installed.

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
