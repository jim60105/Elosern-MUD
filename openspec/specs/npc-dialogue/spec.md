## Purpose

Defines the NPC dialogue layer that runs a guarded generative reply pipeline for `LLMNPC` entities, builds deterministic and bounded prompts that inject the player's `disguised_stats`, extracts whitelisted, shape-validated intents, and applies verified intents through the deterministic core while degrading to authored greetings or silence offline. The layer preserves the single-writer and transport boundaries: it never mutates state, never opens a network connection itself, and consumes the client through an injected protocol.

## Requirements

### Requirement: NPC dialogue runs a guarded generative reply pipeline

`world/ai/npc_dialogue.py` SHALL provide a guarded entry point `generate_npc_reply(...) -> Deferred[NPCDialogueReply | None]` that runs the `npc_dialogue` layer's validation-retry-degrade pipeline (design §7.5): output is validated against the registered `{speech, intent}` jsonschema and the layer's semantic validators, and the call resolves, on success, to a frozen `NPCDialogueReply` carrying `speech: str` and `intent: dict`.

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

#### Scenario: The client arrives only as an injected argument
- **WHEN** any caller uses `generate_npc_reply`
- **THEN** the client is a required injected argument and the dialogue layer never constructs its own transport client

### Requirement: NPC dialogue prompts are deterministic, bounded, and inject disguised stats, affinity context, and persona

`build_npc_dialogue_prompt(...)` SHALL produce a deterministic system/user message pair serialized, with stable JSON serialization, from the NPC's identity (name, description, location in the current turn frame), the speaking player's identity and `disguised_stats`, the NPC's affinity context for the speaking player, optional persona blocks, and a bounded rendered view of durable pair dialogue plus owner-permitted fixed and recalled memories.

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
- **WHEN** a prompt is built without NPC or player persona records
- **THEN** `persona=""` is substituted and no player persona token/block is present; the output equals the persona-free baseline for the current context/rendering version, including the same memory sections

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

#### Scenario: Serialization is hard-bounded
- **WHEN** a prompt is rendered
- **THEN** stable JSON serialization applies hard bounds on memory lines, per-field string length, and total size

#### Scenario: The affinity block is plain read-only data
- **WHEN** an affinity record exists for the speaking player
- **THEN** the block is serialized as `player.affinity = {"value": int, "cap": int, "stage": str}`
- **AND** the affinity context supplied to the builder carries `affinity` as the true numeric value, `affinity_cap`, and `affinity_stage` as the display stage name
- **AND** building a prompt never creates, persists, or mutates an affinity record
- **AND** a player without a record omits the block entirely

#### Scenario: Persona blocks have fixed placements
- **WHEN** persona blocks are included in a prompt
- **THEN** the NPC's own persona appears in the system message and the speaking player's persona appears as `player.persona`

#### Scenario: The prompt library is the sole template source
- **WHEN** the `npc_dialogue` system-message template is located
- **THEN** the prompt library is the sole source of the system-prompt template and the module embeds it as no Python constant

#### Scenario: Only allowlisted placeholders are substituted
- **WHEN** the system template is rendered
- **THEN** only the allowlisted `{name}`, `{desc}`, `{location}`, and `{persona}` placeholders are substituted
- **AND** `persona` is passed on every call — the flattened block when one exists, an empty string when not — so the `{persona}` token is always substituted and the empty-substitution output equals the pre-persona system message

#### Scenario: The system message fixes role, language, and output contract
- **WHEN** the NPC dialogue system message is read
- **THEN** it fixes the NPC's role, the 正體中文 language, and the output contract: reply with a `{speech, intent}` object

#### Scenario: The system message forbids invented outcomes and non-perception
- **WHEN** the system message constrains generation
- **THEN** the model may never invent outcomes and may express only what the NPC could perceive — including reading the player's `disguised_stats` as the truth

#### Scenario: The system message bounds relation deltas and secrets
- **WHEN** the system message governs affinity behaviour
- **THEN** `adjust_relation` deltas are chosen from the supplied affinity context within the bounded 0–10 range
- **AND** the numeric affinity value and cap are treated as secrets never spoken aloud

#### Scenario: The no-leak check installs on disguise-only secrets
- **WHEN** a call has no affinity context but its bound disguise true values make the secret set non-empty
- **THEN** the no-leak check is installed for that call just as for calls with affinity context

#### Scenario: Leak attempts exhaust the retry budget and degrade
- **WHEN** repeated replies leak secret numbers until the `1 + max_retries` budget is exhausted
- **THEN** the call degrades to `None` rather than presenting the leak

#### Scenario: Leak checks bind per call through the request descriptor
- **WHEN** dialogue calls interleave
- **THEN** each call's no-leak check is bound to that call's own secret numbers through the request descriptor, so interleaved calls never cross-contaminate

### Requirement: Intent extraction is whitelisted and shape-validated per kind

The `npc_dialogue` output contract SHALL restrict `intent.kind` to exactly the eight whitelisted kinds `give_item` / `take_item` / `offer_quest` / `request_guild_exam` / `adjust_relation` / `reveal_lore` / `party_invite` / `none`, with a per-kind payload shape validated by a semantic validator: outputs whose kind is outside the whitelist or whose payload violates the per-kind shape are rejected and retried within the budget.

#### Scenario: A whitelisted intent with a valid payload passes
- **WHEN** the model returns an intent such as `{"kind": "give_item", "item_key": "healing_potion", "qty": 1}`, `{"kind": "request_guild_exam", "target_rank": "E"}`, `{"kind": "adjust_relation", "delta": 3}`, `{"kind": "party_invite", "accept": true}`, `{"kind": "offer_quest", "quest_key": "forest_clearing"}`, or `{"kind": "reveal_lore", "category": "race", "key": "ciaran"}`
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

#### Scenario: A malformed offer-quest payload is rejected
- **WHEN** the model returns `offer_quest` with a missing, empty, non-text, or extra-field payload
- **THEN** the output is rejected by the per-kind semantic validator and retried rather than passed to the engine

#### Scenario: A malformed reveal-lore payload is rejected
- **WHEN** the model returns `reveal_lore` with a missing, empty, non-text, or extra-field payload
- **THEN** the output is rejected by the per-kind semantic validator and retried rather than passed
  to the engine

#### Scenario: Item intents carry a key and positive quantity
- **WHEN** the model returns `give_item` or `take_item`
- **THEN** the payload shape requires `item_key` and a positive `qty`

#### Scenario: The exam intent carries exactly a target rank
- **WHEN** the model returns `request_guild_exam`
- **THEN** the payload shape requires exactly one field, `target_rank`

#### Scenario: The relation intent carries a bounded delta
- **WHEN** the model returns `adjust_relation`
- **THEN** the payload shape requires exactly one field, `delta`, a non-negative integer with `0 <= delta <= 10`

#### Scenario: The party-invite intent carries a boolean accept
- **WHEN** the model returns `party_invite`
- **THEN** the payload shape requires exactly one field, `accept`, a boolean

#### Scenario: The offer-quest intent carries a bounded quest key
- **WHEN** the model returns `offer_quest`
- **THEN** the payload shape requires exactly one field, `quest_key`, a non-empty string of at most 64 code points

#### Scenario: The reveal-lore intent carries a bounded category and key
- **WHEN** the model returns `reveal_lore`
- **THEN** the payload shape requires exactly two fields, `category` and `key`, each a non-empty string of at most 64 code points

#### Scenario: A whitelisted kind is not a guarantee of executability
- **WHEN** an intent kind is whitelisted
- **THEN** only its shape is accepted for extraction; executability is decided by the deterministic applier

### Requirement: Intent application is deterministic, verified, and non-escalating

`world/rules/npc_intents.py` SHALL expose `apply_npc_intent(npc, player, intent) -> IntentOutcome` that verifies an extracted intent against the deterministic world before applying it, using existing deterministic APIs only: illegal or unverifiable intent is discarded while the speech is kept, and the world is never changed by an intent the NPC could not perform.

**Removed scenario**: The former "A whitelisted but not-yet-executable intent is rejected without state change" scenario is removed by this change: `reveal_lore` becomes executable here, `offer_quest` became executable in `dialogue-offer-quest`, and no forward-declared intent kinds remain.

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

#### Scenario: An offer-quest intent routes through the dialogue-offer-quest applier
- **WHEN** the extracted intent is `offer_quest` with a valid `quest_key`
- **THEN** `apply_npc_intent` delegates to the dialogue-offer-quest applier, which rechecks the speaker's authored issuing authority and the registered issuance under that issuer kind's eligibility rule and assigns the quest through the quest runtime on success

#### Scenario: An offer-quest gate failure discards only the intent
- **WHEN** the offer-quest verification fails (speaker without an authored issuing authority, no issuance at the speaker's resolved issuer key, an ambiguous dual authority, malformed authority identity data, or a failed guild eligibility check)
- **THEN** the intent is discarded, the speech is preserved, and no quest or affinity state changes

#### Scenario: A reveal-lore intent records the discovery
- **WHEN** the extracted intent is `reveal_lore` with a bounded `category`/`key` that passes the allowlist and registry verification
- **THEN** the applier records the discovery through `record_lore_reveal`, reports applied, and grants no affinity

#### Scenario: A reveal-lore intent the NPC cannot perform is discarded
- **WHEN** the extracted intent is `reveal_lore` with an unknown category or an unresolvable key
- **THEN** the intent is discarded, the speech is preserved, and no codex record changes

#### Scenario: The AI cannot escalate through the exam gate
- **WHEN** `request_guild_exam` is applied
- **THEN** the AI cannot choose examiner stats, waive a gate, promote the player, or start combat directly

#### Scenario: The exam gate performs its own rechecks
- **WHEN** `apply_npc_intent` delegates `request_guild_exam` to change 16's `start_guild_exam(actor=player, examiner=npc, target_rank=..., requested_by="npc_intent")`
- **THEN** that API itself rechecks co-location, the GuildExaminer component and branch, the exact next rank, true cumulative merit, and the absence of active combat/examination

#### Scenario: Item transfers are all-or-nothing across both entities
- **WHEN** a `give_item` or `take_item` transfer is applied after holdings are verified
- **THEN** it transfers through the validated inventory-planning boundary as one all-or-nothing operation whose failure restores both entities' database and in-process state

#### Scenario: Relation deltas route through the affinity-system writer
- **WHEN** `adjust_relation` is applied
- **THEN** the applier verifies the bounded `delta` payload and delegates to `world/rules/affinity.py::apply_affinity_change(npc, player, "ai_dialogue", delta)` from `affinity-system`
- **AND** the AI cannot choose a delta outside 0–10

#### Scenario: The applier reports the actually applied delta amount
- **WHEN** an `adjust_relation` delta is partially budget-applied
- **THEN** the applier reports it as applied with the applied amount in `IntentOutcome.delta_used`
- **AND** a fully blocked or rejected delta (applied amount 0) is discarded as an intent with the speech kept

#### Scenario: Accepted party invites route through party-core
- **WHEN** `party_invite` with `accept: true` is applied
- **THEN** the applier verifies the boolean `accept` payload and delegates to `world/rules/party.py::join_party(npc, player)` from `party-core`, which rechecks co-location, the NPC target, the absence of an existing binding, and the 4-companion bound
- **AND** on `accept: false` the applier reports an applied no-op

#### Scenario: Quest offers recheck authority and issue all-or-nothing
- **WHEN** `offer_quest` is applied
- **THEN** the applier verifies the bounded `quest_key` payload and delegates to the dialogue-offer-quest applier, which rechecks the speaker's authored issuing authority (`GuildStaff` or `QuestIssuer`) and the registered issuance for the speaker's resolved issuer key under that issuer kind's own eligibility rule
- **AND** the quest is assigned through the quest runtime in one all-or-nothing operation with +1 guild affinity

#### Scenario: Lore reveals record append-only with no affinity
- **WHEN** `reveal_lore` is applied
- **THEN** the applier verifies the bounded `category`/`key` payload and delegates to `world/rules/lore_knowledge.py::record_lore_reveal(player, category, key)`, which checks the category allowlist and registry resolvability and records the discovery append-only
- **AND** a repeat reveal is an applied no-op and no affinity is granted

### Requirement: NPC dialogue degrades to greeting or silence offline

When the `npc_dialogue` layer is disabled, unreachable, or retry-exhausted, `generate_npc_reply` SHALL resolve to `None`, and the caller SHALL render that as the NPC's authored greeting when one is available, or as silence when it is not; the game SHALL remain fully playable with the LLM entirely offline, and no dialogue call SHALL change state or open a network connection.

#### Scenario: Offline dialogue falls back to the authored greeting
- **WHEN** the LLM is offline and the NPC has an authored greeting
- **THEN** the player receives the authored greeting with no state change and no network request

#### Scenario: Offline dialogue with no greeting is silence
- **WHEN** the LLM is offline and the NPC has no table greeting, no offline-greeting field text, and no profile greeting
- **THEN** the NPC stays silent and no state changes

#### Scenario: An NPC with an offline-greeting field speaks it offline
- **WHEN** the LLM is offline and a free-form NPC without a scripted table carries a non-empty offline-greeting field
- **THEN** the player receives that field's greeting verbatim, distinct from another such NPC's greeting, with no state change and without resolving any profile

#### Scenario: A profiled host speaks its profile greeting offline
- **WHEN** the LLM is offline, an NPC has no table greeting and an empty offline-greeting field, and its persona provenance names a profile that authors a greeting
- **THEN** the player receives that profile greeting verbatim with no state change

#### Scenario: Greeting resolution follows the fixed order
- **WHEN** an offline NPC's authored greeting is resolved
- **THEN** it resolves in order: the greeting stored in the NPC's own bounded per-instance offline-greeting field, then the NPC's dialogue-table greeting when its table authors one, then the greeting authored by the NPC profile named in its persona provenance

#### Scenario: The instance offline-greeting field overrides every default
- **WHEN** the NPC's per-instance offline-greeting field is set
- **THEN** the field is seeded at build, is author-editable, and overrides every authored default when set

#### Scenario: A runtime card edit does not alter shared defaults
- **WHEN** a card is edited at runtime
- **THEN** the edit changes neither the table nor the profile greeting default, and the instance field speaks exactly its stored text

### Requirement: The LLMNPC entity provides chat memory, thinking state, and a dialogue seam

`typeclasses/npcs.py` SHALL provide an `LLMNPC(NPC)` entity typeclass using narrative-owned append-only durable pair turns and a bounded rendered prompt view, a thinking-state feedback contract, and an `at_talked_to(speech, character, client)` seam that builds the dialogue prompt, runs the guarded reply pipeline, maps the degraded outcome to the authored greeting or silence, and routes a verified intent to `world/rules/npc_intents.apply_npc_intent`.

#### Scenario: A reply is recorded and a verified intent is applied
- **WHEN** the player talks to an `LLMNPC` and the guarded pipeline resolves a valid `NPCDialogueReply`
- **THEN** the NPC's speech is presented to the player, delivered turn records are appended once to the durable pair stream, and a verified intent is applied through the deterministic applier

#### Scenario: The seam injects affinity context without persisting
- **WHEN** the player talks to an `LLMNPC` with an existing affinity record and the prompt is built
- **THEN** the user payload carries the true affinity value, cap, and stage, and the NPC's stored affinity data is unchanged by the talk

#### Scenario: Memory is trimmed to the configured window
- **WHEN** pair history exceeds the configured rendered window
- **THEN** only the rendered memory view is trimmed to the configured window; all original turns remain recoverable under narrative ownership and no durable exchange is dropped

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

#### Scenario: The seam reads affinity context without writing
- **WHEN** the seam builds the dialogue prompt for a speaking player
- **THEN** the prompt includes the NPC's own affinity context for that player, read from the relations handler without creating or mutating any record

#### Scenario: The client is injected and never lazy-built
- **WHEN** the seam is exercised
- **THEN** the client is a required injected argument and is never constructed lazily from a typeclass
- **AND** tests use `FakeLLMClient` only

#### Scenario: Deferred imports protect the guardrail logger
- **WHEN** `typeclasses.npcs` is imported before `evennia._init()`
- **THEN** the seam's imports of `world.ai` and `world.rules.npc_intents` are deferred to the server-ready call path, so the import cannot bind the guardrail's import-time logger to `None`

#### Scenario: The seam consults the schedule before the pipeline
- **WHEN** the seam is about to invoke the guarded pipeline
- **THEN** it consults `world/rules/npc_schedules.py::interaction_reason(npc, "talk")`
- **AND** a non-`None` result presents that stable rejection line and builds no prompt, runs no pipeline, appends no memory, and applies no intent

### Requirement: Async dialogue intents revalidate context at completion

When an async NPC exchange completes, the system SHALL revalidate that the player and the NPC are still co-located and that the NPC is still interactable before applying the reply's intent; a stale completion SHALL display the speech but discard the intent with a clear message.

#### Scenario: Intent is dropped after separation
- **WHEN** an async reply completes after the player or NPC left the room
- **THEN** the speech is shown and no intent (give/take item, adjust relation, reveal lore) is applied

#### Scenario: Intent is dropped when the NPC becomes busy
- **WHEN** an async reply completes after the NPC entered a `busy`/`resting` schedule state
- **THEN** the speech is shown and no intent is applied

#### Scenario: Co-located interactive completion applies the intent
- **WHEN** an async reply completes while both parties remain co-located and the NPC is interactable
- **THEN** the intent applies through its existing per-kind validation

### Requirement: The generative dialogue layer preserves the transport and single-writer boundaries

`world/ai/npc_dialogue.py` SHALL import no state writer, no typeclass, no live transport, and no socket; it SHALL consume the client through the injected protocol and consume the prompt and degrade seams without importing entity or rules packages. No module under `world/ai/` SHALL apply a state change under any circumstance, and the sole transport composition site SHALL remain `world/ai/client.py` plus presentation composition roots that inject the client into the seams.

#### Scenario: The new module complies with the existing contract test
- **WHEN** `tests/test_ai_transport_contract.py` scans the new `world/ai/npc_dialogue.py`
- **THEN** it finds no live-transport import, no state-writer import, and no socket import, and the test passes with no edits

#### Scenario: Only the deterministic applier changes state
- **WHEN** an intent is applied
- **THEN** every state change is performed by `world/rules/npc_intents.py` through existing deterministic APIs, never by a module under `world/ai/`

#### Scenario: The transport-boundary contract test stays green
- **WHEN** the repository-wide transport-boundary contract test runs
- **THEN** it remains green without modification

### Requirement: A persona edit during an asynchronous exchange discards the stale response
Every asynchronous NPC dialogue exchange SHALL capture the NPC's identity and current `persona_version` when it builds the prompt, and at settlement, before any response-side effect, SHALL compare the NPC's current `persona_version` with the captured value. Any inequality SHALL produce a distinct stale-persona terminal outcome, separate from the degraded/offline outcome and from the separated-context outcome.

#### Scenario: A one-leaf edit discards a pending free-form reply
- **WHEN** a browser free-form talk is in flight and the NPC's `habit` is saved through the persona writer before the reply settles
- **THEN** the reply's speech is not shown, no NPC line is appended to memory, no intent applies, the dialogue session line is unchanged, and the action settles with the stale-persona explanation

#### Scenario: Change-and-revert still discards
- **WHEN** a leaf is changed and then changed back by two saves while an exchange is in flight
- **THEN** the exchange settles as stale-persona even though the card text equals the captured card

#### Scenario: A stale invite runs no threshold fallback
- **WHEN** a party invitation exchange degrades offline after the NPC's card was edited mid-flight
- **THEN** no party join, refusal line, or threshold decision occurs, and both the browser action and the text `invite` command report the stale-persona explanation

#### Scenario: A no-op save leaves the exchange valid
- **WHEN** an unchanged card is saved while an exchange is in flight
- **THEN** the exchange settles normally, presents its speech, and applies its verified intent

#### Scenario: Stale-persona settlement clears thinking state without retry
- **WHEN** an exchange settles as stale-persona after its thinking timer started
- **THEN** the timer is cancelled, no second request is made, and the pending state ends

#### Scenario: A stale-persona exchange performs no response-side effect
- **WHEN** an exchange settles as stale-persona
- **THEN** it presents no speech, appends no NPC response to chat memory, applies no intent, records or replaces no dialogue-session line, and runs no degraded party-invite threshold
- **AND** it settles with one safe localized explanation, clears the thinking state, and does not retry

#### Scenario: A pre-edit player line may survive
- **WHEN** an exchange is invalidated by a persona edit
- **THEN** the player's own line recorded before the edit may remain in memory

#### Scenario: No-op saves do not invalidate exchanges
- **WHEN** an unchanged or no-op save occurs during an exchange
- **THEN** the exchange is not invalidated

#### Scenario: The gate covers every exchange consumer
- **WHEN** any consumer of the exchange seam settles — the browser free-form talk action, the browser party-invite action, the text `invite` command, or any other caller of the shared exchange
- **THEN** the stale-persona gate applies through the shared result and memory path, not only a browser control

#### Scenario: Committed work is never undone
- **WHEN** a persona edit invalidates an exchange
- **THEN** already committed speech and effects are not undone

### Requirement: NPC context recalls only permitted committed experience

NPC generation SHALL receive owner-permitted cognition and a durable player/NPC turn view from the narrative context builder. An uninformed NPC SHALL NOT receive another owner private memory or hidden world facts. Speech SHALL NOT establish authoritative outcomes.

#### Scenario: Shared protection reaches the response
- **WHEN** a synthetic observer talks about protection several game days after the encounter
- **THEN** its recorded request includes the selected episode/provenance and a validated fixture reply can refer to it

#### Scenario: Unrelated question does not force recall
- **WHEN** the same owner asks about an unrelated topic
- **THEN** the protection episode is absent from recalled context
