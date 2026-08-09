## Purpose

Defines the NPC dialogue layer that runs a guarded generative reply pipeline for `LLMNPC` entities, builds deterministic and bounded prompts that inject the player's `disguised_stats`, extracts whitelisted, shape-validated intents, and applies verified intents through the deterministic core while degrading to authored greetings or silence offline. The layer preserves the single-writer and transport boundaries: it never mutates state, never opens a network connection itself, and consumes the client through an injected protocol.

## Requirements

### Requirement: NPC dialogue runs a guarded generative reply pipeline

`world/ai/npc_dialogue.py` SHALL provide a guarded entry point `generate_npc_reply(...) -> Deferred[NPCDialogueReply | None]` that runs the `npc_dialogue` layer's validation-retry-degrade pipeline (design §7.5) and resolves, on success, to a frozen `NPCDialogueReply` carrying `speech: str` and `intent: dict`; on disabled profile, transport failure, or exhausted retries it SHALL resolve to `None` (the degraded outcome). The client SHALL be a required injected argument, and a call with an explicit `None` client SHALL errback with a named error before any prompt construction or transport work. The output SHALL be validated against the registered `{speech, intent}` jsonschema and the layer's semantic validators, and retried within the `1 + max_retries` budget with the validation errors appended.

#### Scenario: A schema-valid reply resolves with no retry
- **WHEN** the endpoint returns a `{speech, intent}` object satisfying the output schema and every semantic validator on the first attempt
- **THEN** `generate_npc_reply` resolves with an `NPCDialogueReply` and performs no retry

#### Scenario: Invalid output is retried with errors appended
- **WHEN** the endpoint returns output that fails the output schema or a semantic validator
- **THEN** the pipeline retries up to the `1 + max_retries` budget with that round's full validation error list appended to the prompt

#### Scenario: Disabled, failed, or exhausted dialogue degrades to None
- **WHEN** the `npc_dialogue` profile is disabled, the endpoint fails, or the retry budget is exhausted
- **THEN** the call resolves to `None` with no state change, and the deterministic game continues unaffected

#### Scenario: An explicit None client is rejected before any transport work
- **WHEN** `generate_npc_reply` is called with an explicit `None` client
- **THEN** the call errbacks with a named client-required error before any prompt construction or transport interaction

### Requirement: NPC dialogue prompts are deterministic, bounded, and inject disguised stats, affinity context, and persona

`build_npc_dialogue_prompt(...)` SHALL produce a deterministic system/user message pair serialized from the NPC's identity (name, description, location), the speaking player's identity and `disguised_stats`, the NPC's affinity context for the speaking player (`affinity` as the true numeric value, `affinity_cap`, and `affinity_stage` as the display stage name), optional persona blocks (the NPC's own persona in the system message and the speaking player's persona as `player.persona`), and a bounded chat-memory window, using stable JSON serialization with hard bounds on memory lines, per-field string length, and total size. The affinity block SHALL be serialized as `player.affinity = {"value": int, "cap": int, "stage": str}` and SHALL be read-only: building a prompt SHALL never create, persist, or mutate an affinity record, and a player without a record SHALL omit the block. The system message SHALL be rendered from the prompt library's `npc_dialogue.system` key via `render_prompt("npc_dialogue.system", name=…, desc=…, location=…, persona=…)` — the library is the sole source of the system-prompt template, and the module SHALL NOT embed it as a Python constant; only the allowlisted `{name}`, `{desc}`, `{location}`, and `{persona}` placeholders are substituted, and `persona` SHALL be passed on every call (the flattened block when one exists, an empty string when not) so the `{persona}` token is always substituted and the empty-substitution output equals the pre-persona system message. The system message SHALL fix the NPC's role, the 正體中文 language, and the output contract: reply with a `{speech, intent}` object, never invent outcomes, express only what the NPC could perceive — including reading the player's `disguised_stats` as the truth — choose `adjust_relation` deltas from the supplied affinity context within the bounded 0–10 range, and treat the numeric affinity value and cap as secrets never spoken aloud. The no-leak check SHALL be installed for a call whenever its secret set is non-empty — including calls with no affinity context but with disguise true values — and SHALL treat a reply whose speech contains the affinity value, the cap, or any bound disguise true value as a decimal integer substring (fullwidth digit forms folded via NFKC normalization) as a validation failure, retried within the budget, and on budget exhaustion degraded to `None` rather than presented; the check SHALL be bound to the individual call's own secret numbers through the request descriptor so interleaved calls never cross-contaminate, and stage names SHALL remain allowed in speech. Identical input SHALL produce byte-identical prompts with no live entity references.

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

#### Scenario: Absent persona keeps the byte-identical baseline
- **WHEN** a prompt is built for an NPC and player with no persona records
- **THEN** `persona=""` is substituted into `{persona}`, and the system message and user payload
  are byte-identical to the pre-persona output with no persona token or block present

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
- **THEN** the prompt truncates to the fixed window with an explicit marker and never produces an unbounded request

#### Scenario: The system message is rendered from the prompt library
- **WHEN** the NPC dialogue system message is inspected
- **THEN** it equals `render_prompt("npc_dialogue.system", name=…, desc=…, location=…, persona=…)` and the prompt-library file is the only place its template text is defined
### Requirement: Intent extraction is whitelisted and shape-validated per kind

The `npc_dialogue` output contract SHALL restrict `intent.kind` to exactly the eight whitelisted kinds `give_item` / `take_item` / `offer_quest` / `request_guild_exam` / `adjust_relation` / `reveal_lore` / `party_invite` / `none`. The `request_guild_exam` intent SHALL carry exactly one payload field, `target_rank`; `give_item` and `take_item` SHALL carry `item_key` and a positive `qty`; `adjust_relation` SHALL carry exactly one payload field, `delta`, a non-negative integer with `0 <= delta <= 10`; `party_invite` SHALL carry exactly one payload field, `accept`, a boolean. Outputs whose kind is outside the whitelist or whose payload violates the per-kind shape SHALL be rejected by a semantic validator and retried within the budget. Whitelisting an intent kind SHALL mean the shape is accepted for extraction; it does not guarantee the intent is executable (executability is decided by the deterministic applier).

#### Scenario: A whitelisted intent with a valid payload passes
- **WHEN** the model returns an intent such as `{"kind": "give_item", "item_key": "healing_potion", "qty": 1}`, `{"kind": "request_guild_exam", "target_rank": "E"}`, `{"kind": "adjust_relation", "delta": 3}`, or `{"kind": "party_invite", "accept": true}`
- **THEN** the intent passes semantic validation and proceeds to deterministic verification

#### Scenario: An unknown kind is rejected and retried
- **WHEN** the model returns an `intent.kind` outside the eight-kind whitelist
- **THEN** the output is treated as a validation failure, the error is appended, and the pipeline retries within the budget

#### Scenario: A malformed exam payload is rejected
- **WHEN** the model returns `request_guild_exam` with a payload other than exactly one `target_rank` field
- **THEN** the output is rejected by the per-kind semantic validator and retried rather than passed to the engine

#### Scenario: An out-of-range delta payload is rejected
- **WHEN** the model returns `adjust_relation` with `delta` below 0, above 10, fractional, or with any extra payload field
- **THEN** the output is rejected by the per-kind semantic validator and retried rather than passed to the engine

#### Scenario: A malformed party-invite payload is rejected
- **WHEN** the model returns `party_invite` with a non-boolean `accept`, a missing `accept`, or any extra payload field
- **THEN** the output is rejected by the per-kind semantic validator and retried rather than passed to the engine

### Requirement: Intent application is deterministic, verified, and non-escalating

`world/rules/npc_intents.py` SHALL expose `apply_npc_intent(npc, player, intent) -> IntentOutcome` that verifies an extracted intent against the deterministic world before applying it, using existing deterministic APIs only. `request_guild_exam` SHALL delegate to change 16's `start_guild_exam(actor=player, examiner=npc, target_rank=..., requested_by="npc_intent")`, which rechecks co-location, the GuildExaminer component and branch, the exact next rank, true cumulative merit, and the absence of active combat/examination; the AI SHALL NOT be able to choose examiner stats, waive a gate, promote the player, or start combat directly. `give_item` and `take_item` SHALL verify that the giver actually holds the requested item quantity and SHALL transfer it through the validated inventory-planning boundary as one all-or-nothing operation whose failure restores both entities' database and in-process state. `adjust_relation` SHALL verify the bounded `delta` payload and delegate to `world/rules/affinity.py::apply_affinity_change(npc, player, "ai_dialogue", delta)` from `affinity-system`; the AI SHALL NOT choose a delta outside 0–10, and the applier SHALL report the actually applied amount (`IntentOutcome.delta_used`): a partially budget-applied delta SHALL be reported as applied with its applied amount, while a fully blocked or rejected delta (applied amount 0) SHALL be discarded as an intent with the speech kept. `party_invite` SHALL verify the boolean `accept` payload and, on `accept: true`, delegate to `world/rules/party.py::join_party(npc, player)` from `party-core`, which rechecks co-location, the NPC target, the absence of an existing binding, and the 4-companion bound; on `accept: false` it SHALL report an applied no-op. **Illegal or unverifiable intent SHALL be discarded while the speech is kept** — the world is never changed by an intent the NPC could not perform.

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
- **THEN** `apply_affinity_change(npc, player, "ai_dialogue", delta)` applies the delta and the applier reports `applied=True` with the applied amount

#### Scenario: A partially budgeted delta applies what the budget allows
- **WHEN** the extracted intent is `adjust_relation` with `delta` 4 and only 2 budget remains
- **THEN** exactly 2 is applied and the applier reports `applied=True` with `delta_used=2`

#### Scenario: A fully budget-capped delta discards only the intent
- **WHEN** the extracted intent is `adjust_relation` with an in-range delta and no budget remains
- **THEN** the intent is discarded with a capped outcome (`applied=False`), the speech is preserved, and no affinity state changes

#### Scenario: A zero delta creates no affinity record
- **WHEN** the extracted intent is `adjust_relation` with `delta` 0, including for a recordless player on a later world day
- **THEN** the intent is discarded (`applied=False`), the writer is not invoked, and no affinity record is created or modified

#### Scenario: An accepted party invite routes through join_party
- **WHEN** the extracted intent is `party_invite` with `accept: true`
- **THEN** `apply_npc_intent` delegates to `join_party(npc, player)`, which applies its own co-location, target, binding, and party-bound checks and creates the binding on success

#### Scenario: A declined party invite is an applied no-op
- **WHEN** the extracted intent is `party_invite` with `accept: false`
- **THEN** the outcome reports applied without any membership change

#### Scenario: A join gate failure discards only the intent
- **WHEN** `join_party` rejects the request (remote NPC, full party, or duplicate binding)
- **THEN** the intent is discarded, the speech is preserved, and no binding changes

#### Scenario: A whitelisted but not-yet-executable intent is rejected without state change
- **WHEN** the extracted intent is `offer_quest` or `reveal_lore` and passes extraction shape validation
- **THEN** the deterministic applier returns `applied=False` with a documented reason, the speech is preserved, and no state changes

### Requirement: NPC dialogue degrades to greeting or silence offline

When the `npc_dialogue` layer is disabled, unreachable, or retry-exhausted, `generate_npc_reply` SHALL resolve to `None`, and the caller SHALL render that as the NPC's authored greeting when one is available, or as silence when it is not; the game SHALL remain fully playable with the LLM entirely offline, and no dialogue call SHALL change state or open a network connection.

#### Scenario: Offline dialogue falls back to the authored greeting
- **WHEN** the LLM is offline and the NPC has an authored greeting
- **THEN** the player receives the authored greeting with no state change and no network request

#### Scenario: Offline dialogue with no greeting is silence
- **WHEN** the LLM is offline and the NPC has no authored greeting
- **THEN** the NPC stays silent and no state changes

### Requirement: The LLMNPC entity provides chat memory, thinking state, and a dialogue seam

`typeclasses/npcs.py` SHALL provide an `LLMNPC(NPC)` entity typeclass carrying persistent per-character chat memory, a bounded memory window, a thinking-state feedback contract, and an `at_talked_to(speech, character, client)` seam that builds the dialogue prompt — including the NPC's own affinity context for the speaking player, read from the relations handler without creating or mutating any record — runs the guarded reply pipeline, maps the degraded outcome to the authored greeting or silence, and routes a verified intent to `world/rules/npc_intents.apply_npc_intent`. The client SHALL be a required injected argument and SHALL NOT be constructed lazily from a typeclass; tests use `FakeLLMClient` only. The seam's imports of `world.ai` and `world.rules.npc_intents` SHALL be deferred to the server-ready call path so that importing `typeclasses.npcs` before `evennia._init()` cannot bind the guardrail's import-time logger to `None`.

#### Scenario: A reply is recorded and a verified intent is applied
- **WHEN** the player talks to an `LLMNPC` and the guarded pipeline resolves a valid `NPCDialogueReply`
- **THEN** the NPC's speech is presented to the player, the exchange is appended to the per-character memory within its bound, and a verified intent is applied through the deterministic applier

#### Scenario: The seam injects affinity context without persisting
- **WHEN** the player talks to an `LLMNPC` with an existing affinity record and the prompt is built
- **THEN** the user payload carries the true affinity value, cap, and stage, and the NPC's stored affinity data is unchanged by the talk

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

### Requirement: The generative dialogue layer preserves the transport and single-writer boundaries

`world/ai/npc_dialogue.py` SHALL import no state writer, no typeclass, no live transport, and no socket; it SHALL consume the client through the injected protocol and consume the prompt and degrade seams without importing entity or rules packages. No module under `world/ai/` SHALL apply a state change under any circumstance, and the sole transport composition site SHALL remain `world/ai/client.py` plus presentation composition roots that inject the client into the seams. The repository-wide transport-boundary contract test SHALL remain green without modification.

#### Scenario: The new module complies with the existing contract test
- **WHEN** `tests/test_ai_transport_contract.py` scans the new `world/ai/npc_dialogue.py`
- **THEN** it finds no live-transport import, no state-writer import, and no socket import, and the test passes with no edits

#### Scenario: Only the deterministic applier changes state
- **WHEN** an intent is applied
- **THEN** every state change is performed by `world/rules/npc_intents.py` through existing deterministic APIs, never by a module under `world/ai/`
