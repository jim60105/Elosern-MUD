# Spec Delta

## MODIFIED Requirements

### Requirement: explore.talk_open opens a conversation with the host's greeting
The production action registry SHALL register `explore.talk_open`, whose payload SHALL accept exactly `npc_id` (a positive integer). The adapter SHALL obtain the actor from the authenticated session and SHALL reject, before writing anything: an unlawful possessed actor, an unresolvable `npc_id`, a schedule-blocked host, and a non-conversable host. On success it SHALL record the session through the deterministic dialogue-session seam and publish a full snapshot at one newer revision.

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

#### Scenario: A lawful possessed actor can open authored conversation
- **WHEN** the puppeted actor is a possessed NPC and submits `explore.talk_open`
- **THEN** the adapter validates actor/owner/host context and opens authored dialogue using the companion body, without enabling generated commissions or freeform talk

#### Scenario: Opening a conversation changes only dialogue and narrative observation
- **WHEN** a successful `explore.talk_open` settles with every LLM profile disabled
- **THEN** no network request is made, the world clock tick, affinity records, memories, and party bindings are byte-identical to before the action, and only `db.dialogue_session` changed

#### Scenario: A payload with extra or wrong fields is malformed
- **WHEN** a client submits `explore.talk_open` with `keyword_id`, `speech`, a missing `npc_id`, or a non-positive `npc_id`
- **THEN** the dispatcher rejects it as `malformed_payload` without invoking the adapter

#### Scenario: Conversable host is an LLMNPC or a resolving scripted host
- **WHEN** the adapter classifies whether a present NPC is a conversable host
- **THEN** a conversable host is an `LLMNPC`, or an NPC carrying a resolved `ScriptedDialogue` component whose authored dialogue table resolves

#### Scenario: The offline greeting resolves through the fixed precedence chain
- **WHEN** the adapter takes the session line from the host's resolved offline greeting via `world.rules.dialogue.offline_greeting_for`
- **THEN** the chain is the host's own `db.npc_offline_greeting` field when non-empty, else the dialogue-table greeting, else the provenance profile greeting
- **AND** when it resolves to nothing, the line is one fixed server-authored fallback line naming the host (`{name}看向你，等你開口。`) owned by `world/rules/player_messages.py`

#### Scenario: The session line reaches the narrative in its delivered form
- **WHEN** a successful `explore.talk_open` delivers the resolved session line to the actor's narrative
- **THEN** a greeting is prefixed by the host's name and `說：`, and the fallback line is delivered verbatim
- **AND** the deterministic success result publishes a full snapshot at one newer revision, so the committed mode `dialogue` and the available `dialogue` panel — carrying that line and the host's authored choices — arrive atomically

#### Scenario: talk_open touches no state beyond the session
- **WHEN** a successful `explore.talk_open` runs
- **THEN** the adapter makes no LLM or network request, does not advance the world clock, does not change affinity, memory, party, quest, inventory, or any other state beyond the session, and does not schedule an action-options generation

#### Scenario: talk_open is allowlisted but never suggestible
- **WHEN** the shared action-code registries are consulted
- **THEN** `explore.talk_open` is a member of the shared `ACTION_CODE_ALLOWLIST` and is not a suggestible action code, so no suggestion card or AI proposal names it

#### Scenario: Rejections reuse talk_scripted's codes and message set
- **WHEN** the adapter rejects a possess, resolution, schedule, or host-class failure
- **THEN** it uses the same stable codes and messages `explore.talk_scripted` uses
- **AND** an `npc_id` must re-resolve to an NPC present in the actor's current location — never a stored, remote, or ambiguous reference — else `no_npc`; a host whose talk schedule gate blocks talk rejects with `schedule_blocked` and the gate's reason; and an NPC that is not a conversable host rejects with `not_dialogue_host`

#### Scenario: The session line comes from the greeting or fallback
- **WHEN** a successful `explore.talk_open` resolves its session line
- **THEN** it takes the session line from the host's resolved offline greeting, else one fixed server-authored fallback line naming the host, delivers the line, and records the session
