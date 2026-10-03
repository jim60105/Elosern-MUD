## MODIFIED Requirements

### Requirement: NPC dialogue prompts are deterministic, bounded, and inject disguised stats, affinity context, and persona

`build_npc_dialogue_prompt(...)` SHALL produce a deterministic system/user message pair serialized from the NPC's identity (name, description, location), the speaking player's identity and `disguised_stats`, the NPC's affinity context for the speaking player (`affinity` as the true numeric value, `affinity_cap`, and `affinity_stage` as the display stage name), optional persona blocks (the NPC's own persona in the system message and the speaking player's persona as `player.persona`), and a bounded rendered view of durable pair dialogue plus owner-permitted fixed and recalled memories, using stable JSON serialization with hard bounds on memory lines, per-field string length, and total size. The affinity block SHALL be serialized as `player.affinity = {"value": int, "cap": int, "stage": str}` and SHALL be read-only: building a prompt SHALL never create, persist, or mutate an affinity record, and a player without a record SHALL omit the block. The system message SHALL be rendered from the prompt library's `npc_dialogue.system` key via `render_prompt("npc_dialogue.system", name=…, desc=…, location=…, persona=…)` — the library is the sole source of the system-prompt template, and the module SHALL NOT embed it as a Python constant; only the allowlisted `{name}`, `{desc}`, `{location}`, and `{persona}` placeholders are substituted, and `persona` SHALL be passed on every call (the flattened block when one exists, an empty string when not) so the `{persona}` token is always substituted and the empty-substitution output equals the pre-persona system message. The system message SHALL fix the NPC's role, the 正體中文 language, and the output contract: reply with a `{speech, intent}` object, never invent outcomes, express only what the NPC could perceive — including reading the player's `disguised_stats` as the truth — choose `adjust_relation` deltas from the supplied affinity context within the bounded 0–10 range, and treat the numeric affinity value and cap as secrets never spoken aloud. The no-leak check SHALL be installed for a call whenever its secret set is non-empty — including calls with no affinity context but with disguise true values — and SHALL treat a reply whose speech contains the affinity value, the cap, or any bound disguise true value as a decimal integer substring (fullwidth digit forms folded via NFKC normalization) as a validation failure, retried within the budget, and on budget exhaustion degraded to `None` rather than presented; the check SHALL be bound to the individual call's own secret numbers through the request descriptor so interleaved calls never cross-contaminate, and stage names SHALL remain allowed in speech. Identical input SHALL produce byte-identical prompts with no live entity references.

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
- **THEN** it equals `render_prompt("npc_dialogue.system", name=…, desc=…, location=…, persona=…)` and the prompt-library file is the only place its template text is defined

### Requirement: The LLMNPC entity provides chat memory, thinking state, and a dialogue seam

`typeclasses/npcs.py` SHALL provide an `LLMNPC(NPC)` entity typeclass using narrative-owned append-only durable pair turns and a bounded rendered prompt view, a thinking-state feedback contract, and an `at_talked_to(speech, character, client)` seam that builds the dialogue prompt — including the NPC's own affinity context for the speaking player, read from the relations handler without creating or mutating any record — runs the guarded reply pipeline, maps the degraded outcome to the authored greeting or silence, and routes a verified intent to `world/rules/npc_intents.apply_npc_intent`. The client SHALL be a required injected argument and SHALL NOT be constructed lazily from a typeclass; tests use `FakeLLMClient` only. The seam's imports of `world.ai` and `world.rules.npc_intents` SHALL be deferred to the server-ready call path so that importing `typeclasses.npcs` before `evennia._init()` cannot bind the guardrail's import-time logger to `None`. Before invoking the guarded pipeline, the seam SHALL consult
`world/rules/npc_schedules.py::interaction_reason(npc, "talk")`; a non-`None` result SHALL present
that stable rejection line and SHALL NOT build a prompt, run the pipeline, append memory, or
apply an intent.

#### Scenario: A reply is recorded and a verified intent is applied
- **WHEN** the player talks to an `LLMNPC` and the guarded pipeline resolves a valid `NPCDialogueReply`
- **THEN** the NPC's speech is presented to the player, delivered turn records are appended once to the durable pair stream, and a verified intent is applied through the deterministic applier

#### Scenario: The seam injects affinity context without persisting
- **WHEN** the player talks to an `LLMNPC` with an existing affinity record and the prompt is built
- **THEN** the user payload carries the true affinity value, cap, and stage, and the NPC's stored affinity data is unchanged by the talk

#### Scenario: Prompt selection does not delete durable history
- **WHEN** pair history exceeds the configured rendered window
- **THEN** the prompt is bounded but all original turns remain recoverable under narrative ownership

#### Scenario: Thinking feedback is bounded and cancelled on a terminal result
- **WHEN** the LLM reply takes longer than the configured thinking timeout
- **THEN** exactly one thinking message is sent to the current speaker, and any pending thinking timer is cancelled on the terminal reply or degrade with no leaked deferred or cancellation error

#### Scenario: An explicit None client is rejected by the seam
- **WHEN** `at_talked_to` is called with an explicit `None` client
- **THEN** the seam errbacks with a named client-required error before any prompt construction or transport work

#### Scenario: Importing the typeclass does not break degradation
- **WHEN** `typeclasses.npcs` is imported (its generative and applier imports deferred to the server-ready call path) and the server then runs with the `npc_dialogue` layer disabled
- **THEN** the seam still degrades cleanly to greeting or silence without a logger failure, and no module-scope import chain reaches the guardrail or the applier

#### Scenario: A schedule-blocked seam shows the stable reason and runs nothing
- **WHEN** the player talks to an `LLMNPC` whose schedule state blocks `talk`
- **THEN** the stable rejection line is presented, and no prompt is built, no pipeline runs, no memory is appended, and no intent is applied

## ADDED Requirements

### Requirement: NPC context recalls only permitted committed experience

NPC generation SHALL receive owner-permitted cognition and a durable player/NPC turn view from the narrative context builder. An uninformed NPC SHALL NOT receive another owner private memory or hidden world facts. Speech SHALL NOT establish authoritative outcomes.

#### Scenario: Shared protection reaches the response
- **WHEN** a synthetic observer talks about protection several game days after the encounter
- **THEN** its recorded request includes the selected episode/provenance and a validated fixture reply can refer to it

#### Scenario: Unrelated question does not force recall
- **WHEN** the same owner asks about an unrelated topic
- **THEN** the protection episode is absent from recalled context

