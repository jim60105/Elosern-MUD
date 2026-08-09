# NPC Dialogue

## MODIFIED Requirements

### Requirement: The LLMNPC entity provides chat memory, thinking state, and a dialogue seam

`typeclasses/npcs.py` SHALL provide an `LLMNPC(NPC)` entity typeclass carrying persistent per-character chat memory, a bounded memory window, a thinking-state feedback contract, and an `at_talked_to(speech, character, client)` seam that builds the dialogue prompt — including the NPC's own affinity context for the speaking player, read from the relations handler without creating or mutating any record — runs the guarded reply pipeline, maps the degraded outcome to the authored greeting or silence, and routes a verified intent to `world/rules/npc_intents.apply_npc_intent`. The client SHALL be a required injected argument and SHALL NOT be constructed lazily from a typeclass; tests use `FakeLLMClient` only. The seam's imports of `world.ai` and `world.rules.npc_intents` SHALL be deferred to the server-ready call path so that importing `typeclasses.npcs` before `evennia._init()` cannot bind the guardrail's import-time logger to `None`. Before invoking the guarded pipeline, the seam SHALL consult
`world/rules/npc_schedules.py::interaction_reason(npc, "talk")`; a non-`None` result SHALL present
that stable rejection line and SHALL NOT build a prompt, run the pipeline, append memory, or
apply an intent.

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

#### Scenario: A schedule-blocked seam shows the stable reason and runs nothing
- **WHEN** the player talks to an `LLMNPC` whose schedule state blocks `talk`
- **THEN** the stable rejection line is presented, and no prompt is built, no pipeline runs, no memory is appended, and no intent is applied
