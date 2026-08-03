## ADDED Requirements

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

### Requirement: NPC dialogue prompts are deterministic, bounded, and inject disguised stats

`build_npc_dialogue_prompt(...)` SHALL produce a deterministic system/user message pair serialized from the NPC's identity (name, description, location), the speaking player's identity and `disguised_stats`, and a bounded chat-memory window, using stable JSON serialization with hard bounds on memory lines, per-field string length, and total size. The system message SHALL fix the NPC's role, the 正體中文 language, and the output contract: reply with a `{speech, intent}` object, never invent outcomes, and express only what the NPC could perceive — including reading the player's `disguised_stats` as the truth. Identical input SHALL produce byte-identical prompts with no live entity references.

#### Scenario: A disguised elf reads as weak to the NPC
- **WHEN** a prompt is built for an NPC facing a player whose `disguised_stats` hide their true power
- **THEN** the prompt carries the disguised values so the model describes the player as the NPC perceives them, not the player's true traits

#### Scenario: Identical input yields byte-identical prompts
- **WHEN** the same NPC identity, player data, disguised stats, and memory are serialized twice
- **THEN** both prompts are byte-identical and contain only plain JSON-compatible data with no live entity references

#### Scenario: Oversized memory is bounded deterministically
- **WHEN** the chat memory exceeds the configured window
- **THEN** the prompt truncates to the fixed window with an explicit marker and never produces an unbounded request

### Requirement: Intent extraction is whitelisted and shape-validated per kind

The `npc_dialogue` output contract SHALL restrict `intent.kind` to exactly the seven whitelisted kinds `give_item` / `take_item` / `offer_quest` / `request_guild_exam` / `adjust_relation` / `reveal_lore` / `none`. The `request_guild_exam` intent SHALL carry exactly one payload field, `target_rank`; `give_item` and `take_item` SHALL carry `item_key` and a positive `qty`. Outputs whose kind is outside the whitelist or whose payload violates the per-kind shape SHALL be rejected by a semantic validator and retried within the budget. Whitelisting an intent kind SHALL mean the shape is accepted for extraction; it does not guarantee the intent is executable (executability is decided by the deterministic applier).

#### Scenario: A whitelisted intent with a valid payload passes
- **WHEN** the model returns an intent such as `{"kind": "give_item", "item_key": "healing_potion", "qty": 1}` or `{"kind": "request_guild_exam", "target_rank": "E"}`
- **THEN** the intent passes semantic validation and proceeds to deterministic verification

#### Scenario: An unknown kind is rejected and retried
- **WHEN** the model returns an `intent.kind` outside the seven-kind whitelist
- **THEN** the output is treated as a validation failure, the error is appended, and the pipeline retries within the budget

#### Scenario: A malformed exam payload is rejected
- **WHEN** the model returns `request_guild_exam` with a payload other than exactly one `target_rank` field
- **THEN** the output is rejected by the per-kind semantic validator and retried rather than passed to the engine

### Requirement: Intent application is deterministic, verified, and non-escalating

`world/rules/npc_intents.py` SHALL expose `apply_npc_intent(npc, player, intent) -> IntentOutcome` that verifies an extracted intent against the deterministic world before applying it, using existing deterministic APIs only. `request_guild_exam` SHALL delegate to change 16's `start_guild_exam(actor=player, examiner=npc, target_rank=..., requested_by="npc_intent")`, which rechecks co-location, the GuildExaminer component and branch, the exact next rank, true cumulative merit, and the absence of active combat/examination; the AI SHALL NOT be able to choose examiner stats, waive a gate, promote the player, or start combat directly. `give_item` and `take_item` SHALL verify that the giver actually holds the requested item quantity and SHALL transfer it through the validated inventory-planning boundary as one all-or-nothing operation whose failure restores both entities' database and in-process state. **Illegal or unverifiable intent SHALL be discarded while the speech is kept** — the world is never changed by an intent the NPC could not perform.

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

#### Scenario: A whitelisted but not-yet-executable intent is rejected without state change
- **WHEN** the extracted intent is `offer_quest`, `adjust_relation`, or `reveal_lore` and passes extraction shape validation
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

`typeclasses/npcs.py` SHALL provide an `LLMNPC(NPC)` entity typeclass carrying persistent per-character chat memory, a bounded memory window, a thinking-state feedback contract, and an `at_talked_to(speech, character, client)` seam that builds the dialogue prompt, runs the guarded reply pipeline, maps the degraded outcome to the authored greeting or silence, and routes a verified intent to `world/rules/npc_intents.apply_npc_intent`. The client SHALL be a required injected argument and SHALL NOT be constructed lazily from a typeclass; tests use `FakeLLMClient` only. The seam's imports of `world.ai` and `world.rules.npc_intents` SHALL be deferred to the server-ready call path so that importing `typeclasses.npcs` before `evennia._init()` cannot bind the guardrail's import-time logger to `None`.

#### Scenario: A reply is recorded and a verified intent is applied
- **WHEN** the player talks to an `LLMNPC` and the guarded pipeline resolves a valid `NPCDialogueReply`
- **THEN** the NPC's speech is presented to the player, the exchange is appended to the per-character memory within its bound, and a verified intent is applied through the deterministic applier

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
