## MODIFIED Requirements

### Requirement: NPC dialogue prompts are deterministic, bounded, and inject disguised stats, affinity context, and persona

`build_npc_dialogue_prompt(...)` SHALL produce a deterministic system/user message pair serialized from the NPC's identity (name, description, location in the current turn frame), the speaking player's identity and `disguised_stats`, the NPC's affinity context for the speaking player (`affinity` as the true numeric value, `affinity_cap`, and `affinity_stage` as the display stage name), optional persona blocks (the NPC's own persona in the system message and the speaking player's persona as `player.persona`), and a bounded rendered view of durable pair dialogue plus owner-permitted fixed and recalled memories, using stable JSON serialization with hard bounds on memory lines, per-field string length, and total size. The affinity block SHALL be serialized as `player.affinity = {"value": int, "cap": int, "stage": str}` and SHALL be read-only: building a prompt SHALL never create, persist, or mutate an affinity record, and a player without a record SHALL omit the block. The system message SHALL be rendered from the prompt library's `npc_dialogue.system` key via `render_prompt("npc_dialogue.system", name=…, desc=…, location="", persona=…)` as the capability/character sections of the versioned stable prefix — the library is the sole source of the system-prompt template, and the module SHALL NOT embed it as a Python constant; only the allowlisted `{name}`, `{desc}`, `{location}`, and `{persona}` placeholders are substituted, and `persona` SHALL be passed on every call (the flattened block when one exists, an empty string when not) so the `{persona}` token is always substituted and the empty-substitution output equals the pre-persona system message. The system message SHALL fix the NPC's role, the 正體中文 language, and the output contract: reply with a `{speech, intent}` object, never invent outcomes, express only what the NPC could perceive — including reading the player's `disguised_stats` as the truth — choose `adjust_relation` deltas from the supplied affinity context within the bounded 0–10 range, and treat the numeric affinity value and cap as secrets never spoken aloud. The no-leak check SHALL be installed for a call whenever its secret set is non-empty — including calls with no affinity context but with disguise true values — and SHALL treat a reply whose speech contains the affinity value, the cap, or any bound disguise true value as a decimal integer substring (fullwidth digit forms folded via NFKC normalization) as a validation failure, retried within the budget, and on budget exhaustion degraded to `None` rather than presented; the check SHALL be bound to the individual call's own secret numbers through the request descriptor so interleaved calls never cross-contaminate, and stage names SHALL remain allowed in speech. Identical input SHALL produce byte-identical prompts with no live entity references.

#### Scenario: A disguised elf reads as weak to the NPC
- **WHEN** a prompt is built for an NPC facing a player whose `disguised_stats` hide their true power
- **THEN** the prompt carries the disguised values so the model describes the player as the NPC perceives them, not the player's true traits

#### Scenario: The affinity context reaches the model as plain data
- **WHEN** a prompt is built for an NPC holding an affinity record of value 55 with cap 99 toward the player
- **THEN** the user payload carries `player.affinity` with `value: 55`, `cap: 99`, and the 信賴 stage name, and building the prompt persists no affinity state

#### Scenario: A player without a record gets no affinity block
- **WHEN** a prompt is built for an NPC and a player with no stored affinity record
- **THEN** the user payload contains no `player.affinity` block

#### Scenario: NPC and player persona blocks reach the model
- **WHEN** a prompt is built for an NPC with a persona record and a speaking player with a persona record
- **THEN** the system message contains the NPC's flattened persona block through `{persona}` and the user payload carries `player.persona` with the player's block, both capped

#### Scenario: Absent persona omits persona within the current rendering version
- **WHEN** a prompt is built without NPC or player persona records
- **THEN** `persona=""` is substituted, the player persona block is absent, and unrelated memory/context sections remain valid

#### Scenario: A reply that echoes the secret value is retried
- **WHEN** a reply's speech contains the affinity value, the cap, or a bound disguise true value as a decimal integer substring
- **THEN** the output is rejected by the no-leak semantic validator, the error is appended, and the pipeline retries within the budget instead of presenting the leak

#### Scenario: A fullwidth digit echo is folded and retried
- **WHEN** a reply's speech echoes the affinity value in fullwidth digits such as ５５
- **THEN** NFKC normalization folds the digits and the output is rejected and retried like any decimal-substring leak

#### Scenario: Interleaved calls keep their own leak numbers
- **WHEN** two dialogue calls with different affinity and disguise contexts run concurrently
- **THEN** each reply is validated only against its own call's secret numbers, never the other call's numbers

#### Scenario: A stage name in speech is allowed
- **WHEN** a reply's speech mentions the stage name 信賴 but no affinity number
- **THEN** the output passes the no-leak validator and proceeds normally

#### Scenario: Identical input yields byte-identical prompts
- **WHEN** the same NPC identity, player data, disguised stats, persona blocks, affinity context, and memory are serialized twice
- **THEN** both prompts are byte-identical and contain only plain JSON-compatible data with no live entity references

#### Scenario: Oversized memory is bounded deterministically
- **WHEN** the chat memory exceeds the configured window
- **THEN** the rendered view is reduced deterministically with explicit accounting, durable turns remain intact, and no unbounded request is produced

#### Scenario: The system message is rendered from the prompt library
- **WHEN** the NPC dialogue system message is inspected
- **THEN** its capability/character sections come from `render_prompt("npc_dialogue.system", name=…, desc=…, location="", persona=…)`, changing location is in the new turn frame, and all template text remains in the prompt library

The rendered order SHALL be global rules, world digest, capability contract, character anchor, epoch summary, then append-only turn frames. Changing location, relationships, recall and affordances SHALL occur only in the current turn frame. Persona/prompt/rendering version changes SHALL invalidate the affected prefix and epoch; original historical frames SHALL retain their original tick data.

