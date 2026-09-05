# Delta spec: webclient-exploration-menu (webclient-align-07-dialogue-session-state)

## MODIFIED Requirements

### Requirement: explore.talk_scripted invokes the deterministic dialogue API with keyword buttons
The production action registry SHALL register `explore.talk_scripted`. Its payload SHALL accept exactly `npc_id` (a positive integer) and `keyword_id` (a 1..64-character non-empty string). The adapter SHALL obtain the actor from the authenticated session, re-resolve the NPC from the actor's current location's present contents — never a stored, remote, or ambiguous reference — and re-verify presence, a resolved dialogue component, and the keyword's presence in the host's dialogue table, and then call the read-only `world.rules.dialogue` response API — the same deterministic seam the `talk` command uses — so a `ScriptedDialogue` host answers through the authored tables with the same state effects as the command path. On its success path the adapter SHALL record the exchange through the deterministic dialogue-session seam (the character-held session helper owned by `world.rules.dialogue`); it SHALL NOT invent a response, and SHALL NOT assign dialogue or component state directly. A missing NPC, a no-longer-present NPC, a non-host, an unregistered keyword, or a present-but-unreachable NPC SHALL reject with a stable code and message and SHALL NOT write state.

#### Scenario: Scripted keyword buttons match authored behavior
- **WHEN** an actor submits `explore.talk_scripted` for a present dialogue host with a registered keyword
- **THEN** the player receives the authored response exactly as `talk` would produce it

#### Scenario: An unregistered keyword rejects without writing
- **WHEN** an actor submits a `keyword_id` absent from the host's dialogue table
- **THEN** the adapter rejects with a stable reason, no response is fabricated, and no state is written

#### Scenario: A no-longer-present NPC rejects before any dialogue API
- **WHEN** an actor submits `explore.talk_scripted` for an NPC that was present at render but has since left the room
- **THEN** the adapter re-resolves the NPC from the actor's current location, rejects with a stable reason before calling the dialogue API, and no memory or component state changes

#### Scenario: A scripted reply opens the dialogue session
- **WHEN** an actor submits a valid `explore.talk_scripted` for a present host
- **THEN** the character's dialogue session names that NPC with the authored response line,
  recorded before the adapter's response is delivered

### Requirement: explore.talk_freeform runs the guarded dialogue seam through an injected client
The production action registry SHALL register `explore.talk_freeform`. Its payload SHALL accept exactly `npc_id` (a positive integer) and `speech` (a non-empty string of at most 512 code points). The adapter SHALL obtain the actor from the authenticated session, re-resolve the NPC from the actor's current location's present contents — never a stored, remote, or ambiguous reference — and re-verify presence and free-form eligibility (an `LLMNPC`), obtain the `npc_dialogue` profile client from the exploration composition root (a live `OpenAICompatClient` when the profile is enabled, or a non-`None` offline stub when disabled — the stub is never called because the guardrail degrades before any transport work), and run `npc.at_talked_to(speech, actor, client)`. The seam SHALL present the reply or the degraded authored greeting/silence through the escaped text path, record chat memory, and route any verified intent through the deterministic applier; an illegal or unverifiable AI intent SHALL be discarded while the speech is kept. On the settled success path (reply or authored degrade line) the adapter SHALL record the exchange through the deterministic dialogue-session seam BEFORE publishing, so the published snapshot carries the `dialogue` mode and panel atomically with the reply: the adapter supplies the settled-line observer to `at_talked_to` (the seam's resolution value stays unchanged), and the seam invokes the observer only after the reply or the authored degrade line was actually presented and the completion gate still passes — a mid-flight-stale settlement and a silent degrade invoke it never. The adapter SHALL return a Deferred that resolves to a safe success result after the seam settles, SHALL publish a full snapshot at one newer revision so any applied intent (including a `request_guild_exam` mode change) refreshes atomically, and SHALL NOT assign memory, intent, guild, quest, inventory, or combat state directly. A missing, no-longer-present, or non-eligible NPC SHALL reject synchronously with a stable code before any client or transport work. With the LLM entirely offline the action SHALL still complete through the authored greeting or silence with no network request and no state change beyond the permitted degrade path.

#### Scenario: Free-form dialogue retains its server-held target
- **WHEN** an actor submits `explore.talk_freeform` for a present `LLMNPC` with bounded speech
- **THEN** the seam runs `at_talked_to` with the injected client, the reply (or degraded greeting/silence) is presented, memory is recorded, and a verified intent is applied through the deterministic applier

#### Scenario: Offline free-form dialogue degrades to greeting or silence
- **WHEN** the `npc_dialogue` profile is disabled or unreachable and the actor submits `explore.talk_freeform`
- **THEN** the player receives the authored greeting or silence, no network request is made, and no unintended state changes

#### Scenario: An illegal AI intent is discarded while the speech is kept
- **WHEN** the guarded pipeline resolves a reply whose intent the deterministic applier cannot verify
- **THEN** the speech is presented, the intent is discarded, and no guild, quest, inventory, or combat state changes

#### Scenario: A tampered NPC ID is rejected before any client work
- **WHEN** an actor submits `explore.talk_freeform` with an `npc_id` that is not a present eligible `LLMNPC`
- **THEN** the adapter rejects with a stable reason and the injected client is never invoked

#### Scenario: A settled freeform reply opens the session before the snapshot
- **WHEN** a freeform talk settles with a reply (or the authored degrade line) for a present
  `LLMNPC`
- **THEN** the session records the NPC and the settled line BEFORE the existing newer-revision
  snapshot publish for that settlement

#### Scenario: A discarded stale completion records nothing
- **WHEN** the deferred reply settles after the player moved away and the rechecks fail
- **THEN** the dialogue session is not written (or already cleared by the movement seam) by the
  stale completion
