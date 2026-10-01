## MODIFIED Requirements

### Requirement: explore.talk_open opens a conversation with the host's greeting
The production action registry SHALL register `explore.talk_open`. Its payload SHALL accept exactly `npc_id` (a positive integer). The adapter SHALL obtain the actor from the authenticated session and SHALL reject, before writing anything and with the same stable codes and messages `explore.talk_scripted` uses: a possessed actor with the possession-refusal code; an `npc_id` that does not re-resolve to an NPC present in the actor's current location — never a stored, remote, or ambiguous reference — with `no_npc`; a host whose talk schedule gate blocks talk with `schedule_blocked` and the gate's reason; and an NPC that is not a conversable host with `not_dialogue_host`. A conversable host SHALL be an `LLMNPC`, or an NPC carrying a resolved `ScriptedDialogue` component whose authored dialogue table resolves. On success the adapter SHALL take the session line from the host's resolved offline greeting (`world.rules.dialogue.offline_greeting_for`: the host's own `db.npc_offline_greeting` field when non-empty, else the dialogue-table greeting, else the provenance profile greeting) and, when it resolves to nothing, from one fixed server-authored fallback line naming the host (`{name}看向你，等你開口。`) owned by `world/rules/player_messages.py`; it SHALL record the session through the deterministic dialogue-session seam, deliver the line to the actor's narrative (a greeting prefixed by the host's name and `說：`, the fallback verbatim), and return a deterministic success result that publishes a full snapshot at one newer revision, so the committed mode `dialogue` and the available `dialogue` panel — carrying that line and the host's authored choices — arrive atomically. The adapter SHALL make no LLM or network request, SHALL NOT advance the world clock, SHALL NOT change affinity, memory, party, quest, inventory, or any other state beyond the session, and SHALL NOT schedule an action-options generation. `explore.talk_open` SHALL be a member of the shared `ACTION_CODE_ALLOWLIST` and SHALL NOT be a suggestible action code, so no suggestion card or AI proposal names it.

#### Scenario: A scripted host opens with its greeting
- **WHEN** an actor submits `explore.talk_open` for a present scripted host whose authored table carries a greeting and two keywords
- **THEN** the action succeeds once, the character's session names that host with the greeting as its line, and the next committed presentation carries mode `dialogue` with the `dialogue` panel showing that line and exactly the two keyword choices

#### Scenario: An edited offline greeting opens the conversation
- **WHEN** an actor submits `explore.talk_open` for a present host whose `db.npc_offline_greeting` field is non-empty and whose table also carries a greeting
- **THEN** the session line and the dialogue panel's first line are the field's text and not the table greeting

#### Scenario: A host without a greeting opens with the fixed fallback line
- **WHEN** an actor submits `explore.talk_open` for a present `LLMNPC` that carries no scripted component, or a scripted host whose table has no greeting and whose offline-greeting field is empty
- **THEN** the session line is exactly the fixed fallback line naming the host, and the dialogue panel is available with that line

#### Scenario: A departed or non-host NPC rejects without writing
- **WHEN** an actor submits `explore.talk_open` for an NPC that left the room after render, for an identity that is not an NPC, or for a present NPC that is neither an `LLMNPC` nor a scripted host with a resolvable table
- **THEN** the adapter rejects with `no_npc` or `not_dialogue_host` respectively, and `db.dialogue_session` and the committed mode are unchanged

#### Scenario: A schedule-blocked host rejects with the gate's reason
- **WHEN** an actor submits `explore.talk_open` for a present host inside its talk-blocked schedule window
- **THEN** the adapter rejects with `schedule_blocked` and the schedule gate's message, and no session is written

#### Scenario: A possessed actor cannot open a conversation
- **WHEN** the puppeted actor is a possessed NPC and submits `explore.talk_open`
- **THEN** the adapter rejects with the possession-refusal code before resolving the host

#### Scenario: Opening a conversation touches nothing but the session
- **WHEN** a successful `explore.talk_open` settles with every LLM profile disabled
- **THEN** no network request is made, the world clock tick, affinity records, memories, and party bindings are byte-identical to before the action, and only `db.dialogue_session` changed

#### Scenario: A payload with extra or wrong fields is malformed
- **WHEN** a client submits `explore.talk_open` with `keyword_id`, `speech`, a missing `npc_id`, or a non-positive `npc_id`
- **THEN** the dispatcher rejects it as `malformed_payload` without invoking the adapter
