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
- **THEN** no network request is made, the world clock tick, affinity records, memories, and party bindings are byte-identical to before the action; only the dialogue session and narrative-owned availability observation may change

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

#### Scenario: talk_open changes only the session and narrative observation
- **WHEN** a successful `explore.talk_open` runs
- **THEN** the adapter makes no LLM or network request, does not advance world time or change affinity, memory, party, quest or inventory, and writes only session state plus deterministic narrative availability observation

#### Scenario: talk_open is allowlisted but never suggestible
- **WHEN** the shared action-code registries are consulted
- **THEN** `explore.talk_open` is a member of the shared `ACTION_CODE_ALLOWLIST` and is emitted only as a target's 交談 affordance, so no exploration entry proposes it as a standalone action

#### Scenario: Rejections reuse talk_scripted's codes and message set
- **WHEN** the adapter rejects a possess, resolution, schedule, or host-class failure
- **THEN** it uses the same stable codes and messages `explore.talk_scripted` uses
- **AND** an `npc_id` must re-resolve to an NPC present in the actor's current location — never a stored, remote, or ambiguous reference — else `no_npc`; a host whose talk schedule gate blocks talk rejects with `schedule_blocked` and the gate's reason; and an NPC that is not a conversable host rejects with `not_dialogue_host`

#### Scenario: The session line comes from the greeting or fallback
- **WHEN** a successful `explore.talk_open` resolves its session line
- **THEN** it takes the session line from the host's resolved offline greeting, else one fixed server-authored fallback line naming the host, delivers the line, and records the session

#### Scenario: A possessed actor cannot open a conversation
- **WHEN** a possessed actor has invalid mirrors, membership or authenticated control
- **THEN** opening rejects before any dialogue or narrative state change

#### Scenario: Opening a conversation touches nothing but the session
- **WHEN** a freeform-only host without scene topics opens with all model profiles disabled
- **THEN** native opening writes only its session and changes no gameplay or authored-reading observation state

#### Scenario: talk_open touches no state beyond the session
- **WHEN** a freeform-only conversation opens without a scene topic definition
- **THEN** no scene observation is written, no model generation runs and only its session changes; static/generated scene hosts use the shared observation path

### Requirement: Exploration affordances are server-authored, never inferred from prose
Existing exploration affordances SHALL remain server-authored. Party invite SHALL use general identity and its separate four-member quota; same-owner temporary-only members SHALL remain normally recruitable. Party leave SHALL address source-aware general removal or selected private escort abandonment through the existing mission drawer, never detach a valid escort reason directly. Other conversation/service/combat/editor gates SHALL remain.

#### Scenario: A scripted host exposes its authored keywords
- **WHEN** a present NPC carries a `ScriptedDialogue` component with two authored keywords and the player opens a conversation with it
- **THEN** its interact descriptor offers exactly one enabled 交談 `explore.talk_open` affordance and no keyword list, and once the conversation opens the `dialogue` panel's choices are exactly those two authored keywords

#### Scenario: A generative NPC offers free-form talk
- **WHEN** a present `LLMNPC` is in the room, with or without a scripted component
- **THEN** its interact descriptor offers exactly one 交談 `explore.talk_open` affordance and no `explore.talk_freeform` affordance, and the conversation that 交談 opens offers free-form speech

#### Scenario: An unbound generative NPC offers an invite
- **WHEN** an eligible present unbound or same-owner temporary-only LLMNPC has no general identity
- **THEN** its invite affordance is enabled below four valid general identities regardless of temporary count, otherwise disabled as full_party

#### Scenario: A bound companion offers leave instead of invite
- **WHEN** a present companion has general identity
- **THEN** its leave affordance offers general removal; a temporary-only eligible actor may also offer ordinary recruitment

#### Scenario: A living hostile monster offers engage
- **WHEN** a present living `Monster` is in the room and the actor has no active session
- **THEN** its interact descriptor offers `explore.engage`; an already-engaged actor receives no engage affordance

#### Scenario: No affordance is fabricated for a plain NPC
- **WHEN** a present NPC carries neither a dialogue component nor an eligible free-form surface nor a party binding
- **THEN** its descriptor retains disabled talk with a server reason and contains no fabricated invite/leave/service; the card retains fixed talk/look slots

#### Scenario: A scripted host without a resolvable table shows a disabled 交談
- **WHEN** a present NPC carries a `ScriptedDialogue` component whose authored table cannot be resolved and is not an `LLMNPC`
- **THEN** its interact descriptor carries one disabled 交談 affordance with the `dialogue_unavailable` reason, and submitting `explore.talk_open` for it rejects with `not_dialogue_host`

#### Scenario: Every NPC target offers the author editor last
- **WHEN** the room holds a scripted host with a valid card, a plain NPC whose card was never initialized, and a living monster
- **THEN** the host's conditional descriptors include an enabled 編輯人物設定 npc_persona navigation before the separate services group, the uninitialized NPC's ends with a disabled one carrying the `npc_persona.unavailable` reason, and the monster carries none

#### Scenario: The editor row survives the descriptor bound
- **WHEN** a target's other affordances already fill the eight-descriptor bound
- **THEN** the descriptor keeps the 編輯人物設定 conditional navigation before the separate services group and drops the lowest-priority other affordance

#### Scenario: A scripted host whose table cannot be resolved carries a disabled 交談
- **WHEN** a present NPC carries a resolved `ScriptedDialogue` component whose authored table cannot be resolved
- **THEN** it carries one disabled 交談 affordance with the stable `dialogue_unavailable` reason

#### Scenario: No in-conversation codes or keyword lists are offered
- **WHEN** the presenter builds target affordances
- **THEN** no target carries an `explore.talk_scripted` or `explore.talk_freeform` affordance or a keyword list: the host's authored keywords and free-form speech are offered by the dialogue surface once the conversation is open

#### Scenario: Party invite eligibility and enablement
- **WHEN** party invite affordances are built
- **THEN** ordinary local free-form eligibility, ownership and general quota apply; already-general/foreign-bound actors are refused while same-owner temporary-only actors are recruitable

#### Scenario: Party leave targets only bound companions
- **WHEN** party leave affordances are built
- **THEN** only effective owned present companions receive them, and active escort reasons identify the affected missions for selected abandonment rather than blind detachment

#### Scenario: Engage targets only living hostile monsters outside combat
- **WHEN** the presenter decides whether to offer `explore.engage`
- **THEN** it is offered only for a present living hostile `Monster` when the actor has no active combat session

#### Scenario: A navigate service affordance needs an unambiguous usable host
- **WHEN** the presenter decides whether to offer a `navigate`-kind service affordance (`surface` `"guild"` or `"shop"`)
- **THEN** old guild/shop navigate descriptors stay removed after P; selected-provider entries use the services field

#### Scenario: No affordance references a remote, absent, or ambiguous target
- **WHEN** the presenter builds any interact affordance
- **THEN** it references no remote, absent, or ambiguous host or target

#### Scenario: Adapters re-verify their descriptor's affordance at commit time
- **WHEN** an exploration adapter runs after the dispatcher's checks
- **THEN** it re-verifies, against the actor's current location and current canonical state, the affordance that produced its descriptor — presence in the actor's location, the exact typeclass/component/eligibility, and the unchanged keyword, party, or host condition
- **AND** a target removed from the room, type-changed, or no longer eligible between render and submit is rejected before the display, dialogue, invite, leave, or engage API is called and before any memory, intent, party, session, or time state changes

#### Scenario: Dual membership preserves one row and independent controls
- **WHEN** a same-owner temporary-only actor is normally recruited and later has its general identity removed
- **THEN** its one effective roster row and escort controls remain until all valid escort reasons end

#### Scenario: Disabled common talk for plain NPC
- **WHEN** a visible NPC has no supported conversation
- **THEN** its server-authored talk descriptor is disabled with an inline not-conversable reason, preserving common slot 1 without granting talk authority

#### Scenario: Selected-provider services replace coarse navigation
- **WHEN** an NPC has supported services
- **THEN** the services field derives all route entries for that selected host; guild/shop navigate affordances remain removed and another same-class bystander does not hide its entries
