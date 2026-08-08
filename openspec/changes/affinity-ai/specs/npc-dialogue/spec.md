## RENAMED Requirements

- FROM: `### Requirement: NPC dialogue prompts are deterministic, bounded, and inject disguised stats`
- TO: `### Requirement: NPC dialogue prompts are deterministic, bounded, and inject disguised stats and affinity context`

## MODIFIED Requirements

### Requirement: NPC dialogue prompts are deterministic, bounded, and inject disguised stats and affinity context
`build_npc_dialogue_prompt(...)` SHALL produce a deterministic system/user message pair serialized
from the NPC's identity (name, description, location), the speaking player's identity and
`disguised_stats`, the NPC's affinity context for the speaking player (`affinity` as the true
numeric value, `affinity_cap`, and `affinity_stage` as the display stage name), and a bounded
chat-memory window, using stable JSON serialization with hard bounds on memory lines, per-field
string length, and total size. The affinity block SHALL be serialized as
`player.affinity = {"value": int, "cap": int, "stage": str}` and SHALL be read-only: building a
prompt SHALL never create, persist, or mutate an affinity record, and a player without a record
SHALL omit the block. The system message SHALL be rendered from the
prompt library's `npc_dialogue.system` key via `render_prompt("npc_dialogue.system", name=…,
desc=…, location=…)` — the library is the sole source of the system-prompt template, and the
module SHALL NOT embed it as a Python constant; only the allowlisted `{name}`, `{desc}`, and
`{location}` placeholders are substituted. The system message SHALL fix the NPC's role, the
正體中文 language, and the output contract: reply with a `{speech, intent}` object, never invent
outcomes, express only what the NPC could perceive — including reading the player's
`disguised_stats` as the truth — choose `adjust_relation` deltas from the supplied affinity
context within the bounded 0–10 range, and treat the numeric affinity value and cap as secrets
never spoken aloud. A reply whose speech contains the affinity value or the cap as a decimal
integer substring SHALL be treated as a validation failure, retried within the budget, and on
budget exhaustion degrade to `None` rather than present the leak; stage names SHALL remain
allowed in speech. Identical input SHALL produce byte-identical prompts with
no live entity references.

#### Scenario: A disguised elf reads as weak to the NPC
- **WHEN** a prompt is built for an NPC facing a player whose `disguised_stats` hide their true power
- **THEN** the prompt carries the disguised values so the model describes the player as the NPC perceives them, not the player's true traits

#### Scenario: The affinity context reaches the model as plain data
- **WHEN** a prompt is built for an NPC holding an affinity record of value 42 with cap 99 toward the player
- **THEN** the user payload carries `player.affinity` with `value: 42`, `cap: 99`, and the 信賴
  stage name, and building the prompt persists no affinity state

#### Scenario: A player without a record gets no affinity block
- **WHEN** a prompt is built for an NPC and a player with no stored affinity record
- **THEN** the user payload contains no `player.affinity` block

#### Scenario: A reply that echoes the secret value is retried
- **WHEN** a reply's speech contains the affinity value or cap as a decimal integer substring
- **THEN** the output is rejected by the no-leak semantic validator, the error is appended, and
  the pipeline retries within the budget instead of presenting the leak

#### Scenario: A stage name in speech is allowed
- **WHEN** a reply's speech mentions the stage name 信賴 but no affinity number
- **THEN** the output passes the no-leak validator and proceeds normally

#### Scenario: Identical input yields byte-identical prompts
- **WHEN** the same NPC identity, player data, disguised stats, affinity context, and memory are serialized twice
- **THEN** both prompts are byte-identical and contain only plain JSON-compatible data with no live entity references

#### Scenario: Oversized memory is bounded deterministically
- **WHEN** the chat memory exceeds the configured window
- **THEN** the prompt truncates to the fixed window with an explicit marker and never produces an unbounded request

#### Scenario: The system message is rendered from the prompt library
- **WHEN** the NPC dialogue system message is inspected
- **THEN** it equals `render_prompt("npc_dialogue.system", name=…, desc=…, location=…)` and the prompt-library file is the only place its template text is defined

### Requirement: Intent extraction is whitelisted and shape-validated per kind
The `npc_dialogue` output contract SHALL restrict `intent.kind` to exactly the seven whitelisted
kinds `give_item` / `take_item` / `offer_quest` / `request_guild_exam` / `adjust_relation` /
`reveal_lore` / `none`. The `request_guild_exam` intent SHALL carry exactly one payload field,
`target_rank`; `give_item` and `take_item` SHALL carry `item_key` and a positive `qty`;
`adjust_relation` SHALL carry exactly one payload field, `delta`, a non-negative integer with
`0 <= delta <= 10`. Outputs whose kind is outside the whitelist or whose payload violates the
per-kind shape SHALL be rejected by a semantic validator and retried within the budget.
Whitelisting an intent kind SHALL mean the shape is accepted for extraction; it does not guarantee
the intent is executable (executability is decided by the deterministic applier).

#### Scenario: A whitelisted intent with a valid payload passes
- **WHEN** the model returns an intent such as `{"kind": "give_item", "item_key": "healing_potion", "qty": 1}`, `{"kind": "request_guild_exam", "target_rank": "E"}`, or `{"kind": "adjust_relation", "delta": 3}`
- **THEN** the intent passes semantic validation and proceeds to deterministic verification

#### Scenario: An unknown kind is rejected and retried
- **WHEN** the model returns an `intent.kind` outside the seven-kind whitelist
- **THEN** the output is treated as a validation failure, the error is appended, and the pipeline retries within the budget

#### Scenario: A malformed exam payload is rejected
- **WHEN** the model returns `request_guild_exam` with a payload other than exactly one `target_rank` field
- **THEN** the output is rejected by the per-kind semantic validator and retried rather than passed to the engine

#### Scenario: An out-of-range delta payload is rejected
- **WHEN** the model returns `adjust_relation` with `delta` below 0, above 10, fractional, or with any extra payload field
- **THEN** the output is rejected by the per-kind semantic validator and retried rather than passed to the engine

### Requirement: Intent application is deterministic, verified, and non-escalating
`world/rules/npc_intents.py` SHALL expose `apply_npc_intent(npc, player, intent) -> IntentOutcome`
that verifies an extracted intent against the deterministic world before applying it, using
existing deterministic APIs only. `request_guild_exam` SHALL delegate to change 16's
`start_guild_exam(actor=player, examiner=npc, target_rank=..., requested_by="npc_intent")`, which
rechecks co-location, the GuildExaminer component and branch, the exact next rank, true cumulative
merit, and the absence of active combat/examination; the AI SHALL NOT be able to choose examiner
stats, waive a gate, promote the player, or start combat directly. `give_item` and `take_item`
SHALL verify that the giver actually holds the requested item quantity and SHALL transfer it
through the validated inventory-planning boundary as one all-or-nothing operation whose failure
restores both entities' database and in-process state. `adjust_relation` SHALL verify the bounded
`delta` payload and delegate to `world/rules/affinity.py::apply_affinity_change(npc, player,
"ai_dialogue", delta)` from `affinity-system`; the AI SHALL NOT choose a delta outside 0–10, and
the applier SHALL report the actually applied amount (`IntentOutcome.delta_used`): a partially
budget-applied delta SHALL be reported as applied with its applied amount, while a fully blocked
or rejected delta (applied amount 0) SHALL be discarded as an intent with the speech kept.
**Illegal
or unverifiable intent SHALL be discarded while the speech is kept** — the world is never changed
by an intent the NPC could not perform.

#### Scenario: A guild exam intent is routed through the deterministic gate
- **WHEN** the extracted intent is `request_guild_exam` with a `target_rank`
- **THEN** `apply_npc_intent` calls `start_guild_exam(actor=player, examiner=npc, target_rank=..., requested_by="npc_intent")`, which applies its own checks and records the exam outcome

#### Scenario: A failed exam gate discards only the intent
- **WHEN** `start_guild_exam` rejects the request (remote examiner, wrong branch, wrong next rank, below merit threshold, or active combat/exam)
- **THEN** the intent is discarded, the speech is preserved, and no exam, rank, or combat state changes

#### Scenario: An item intent verifies holdings before transfer
- **WHEN** the extracted intent is `give_item` or `take_item` and the giver holds the requested item quantity
- **THEN** the items transfer through the inventory-planning boundary and the result is reported deterministically

#### Scenario: An item intent the giver cannot perform is discarded
- **WHEN** the extracted intent asks for an item the giver does not hold or a quantity it cannot provide
- **THEN** the intent is discarded, the speech is kept, and no inventory changes

#### Scenario: A failed transfer rolls back both entities atomically
- **WHEN** the second side of a two-entity item transfer fails after the first side applied
- **THEN** both entities' database inventory and in-process attributes return to their pre-transfer state, and no partial transfer is observable

#### Scenario: An adjust_relation delta applies through the sole-writer API
- **WHEN** the extracted intent is `adjust_relation` with `delta` 0–10 and the daily budget permits the full amount
- **THEN** `apply_affinity_change(npc, player, "ai_dialogue", delta)` applies the delta and the
  applier reports `applied=True` with the applied amount

#### Scenario: A partially budgeted delta applies what the budget allows
- **WHEN** the extracted intent is `adjust_relation` with `delta` 4 and only 2 budget remains
- **THEN** exactly 2 is applied and the applier reports `applied=True` with `delta_used=2`

#### Scenario: A fully budget-capped delta discards only the intent
- **WHEN** the extracted intent is `adjust_relation` with an in-range delta and no budget remains
- **THEN** the intent is discarded with a capped outcome (`applied=False`), the speech is preserved, and no affinity state changes

#### Scenario: A whitelisted but not-yet-executable intent is rejected without state change
- **WHEN** the extracted intent is `offer_quest` or `reveal_lore` and passes extraction shape validation
- **THEN** the deterministic applier returns `applied=False` with a documented reason, the speech is preserved, and no state changes

### Requirement: The LLMNPC entity provides chat memory, thinking state, and a dialogue seam
`typeclasses/npcs.py` SHALL provide an `LLMNPC(NPC)` entity typeclass carrying persistent
per-character chat memory, a bounded memory window, a thinking-state feedback contract, and an
`at_talked_to(speech, character, client)` seam that builds the dialogue prompt — including the
NPC's own affinity context for the speaking player, read from the relations handler without
creating or mutating any record — runs the guarded reply pipeline, maps the degraded outcome to
the authored greeting or silence, and routes a verified intent to
`world/rules/npc_intents.apply_npc_intent`. The client SHALL be a required injected argument and
SHALL NOT be constructed lazily from a typeclass; tests use `FakeLLMClient` only. The seam's
imports of `world.ai` and `world.rules.npc_intents` SHALL be deferred to the server-ready call
path so that importing `typeclasses.npcs` before `evennia._init()` cannot bind the guardrail's
import-time logger to `None`.

#### Scenario: A reply is recorded and a verified intent is applied
- **WHEN** the player talks to an `LLMNPC` and the guarded pipeline resolves a valid `NPCDialogueReply`
- **THEN** the NPC's speech is presented to the player, the exchange is appended to the per-character memory within its bound, and a verified intent is applied through the deterministic applier

#### Scenario: The seam injects affinity context without persisting
- **WHEN** the player talks to an `LLMNPC` with an existing affinity record and the prompt is built
- **THEN** the user payload carries the true affinity value, cap, and stage, and the NPC's stored
  affinity data is unchanged by the talk

#### Scenario: Memory is trimmed to the configured window
- **WHEN** the per-character chat memory exceeds its configured maximum
- **THEN** the oldest exchanges are dropped so the memory stays within the bound

#### Scenario: Thinking feedback is bounded and cancelled on a terminal result
- **WHEN** the LLM reply takes longer than the configured thinking timeout
- **THEN** exactly one thinking message is sent to the current speaker, and any pending thinking timer is cancelled on the terminal reply or degrade with no leaked deferred or cancellation error

#### Scenario: An explicit None client is rejected by the seam
- **WHEN** `at_talked_to` is called with an explicit `None` client
- **THEN** the seam errbacks with a named client-required error before any prompt construction or transport work

#### Scenario: Importing the typeclass does not break degradation
- **WHEN** `typeclasses.npcs` is imported (its generative and applier imports deferred to the server-ready call path) and the server then runs with the `npc_dialogue` layer disabled
- **THEN** the seam still degrades cleanly to greeting or silence without a logger failure, and no module-scope import chain reaches the guardrail or the applier
