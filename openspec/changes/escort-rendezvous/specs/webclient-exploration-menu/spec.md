# Spec Delta

## MODIFIED Requirements

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
- **THEN** its interact descriptor contains no 交談, invite, leave, or service affordance, and the browser renders only the descriptors the server sent

#### Scenario: A scripted host without a resolvable table shows a disabled 交談
- **WHEN** a present NPC carries a `ScriptedDialogue` component whose authored table cannot be resolved and is not an `LLMNPC`
- **THEN** its interact descriptor carries one disabled 交談 affordance with the `dialogue_unavailable` reason, and submitting `explore.talk_open` for it rejects with `not_dialogue_host`

#### Scenario: Every NPC target offers the author editor last
- **WHEN** the room holds a scripted host with a valid card, a plain NPC whose card was never initialized, and a living monster
- **THEN** the host's descriptor ends with an enabled 編輯人物設定 `npc_persona` navigation, the uninitialized NPC's ends with a disabled one carrying the `npc_persona.unavailable` reason, and the monster carries none

#### Scenario: The editor row survives the descriptor bound
- **WHEN** a target's other affordances already fill the eight-descriptor bound
- **THEN** the descriptor keeps the 編輯人物設定 navigation as its last entry and drops the lowest-priority other affordance

#### Scenario: A scripted host whose table cannot be resolved carries a disabled 交談
- **WHEN** a present NPC carries a resolved `ScriptedDialogue` component whose authored table cannot be resolved
- **THEN** it carries one disabled 交談 affordance with the stable `dialogue_unavailable` reason

#### Scenario: No in-conversation codes or keyword lists are offered
- **WHEN** the presenter builds target affordances
- **THEN** no target carries an `explore.talk_scripted` or `explore.talk_freeform` affordance or a keyword list: the host's authored keywords and free-form speech are offered by the dialogue surface once the conversation is open, and the shared vocabulary's per-keyword and free-form entries remain the source of suggestion cards

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
- **THEN** it is offered only when the current room has exactly one unambiguous `GuildStaff` or `Merchant` host for a service the actor can use, and it opens the corresponding service drawer rather than inventing a mutation

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

### Requirement: explore.party_invite proposes a party through the guarded dialogue seam
The existing explore.party_invite SHALL retain exactly npc_id and bounded message, injected dialogue and output semantics. Both preflight and commit SHALL use ordinary recruitment eligibility, co-location, ownership, no existing general identity and fewer than four valid general identities. Same-owner temporary-only actors MAY acquire general identity without source loss, duplicate rows or an affinity bypass.

#### Scenario: An invited generative NPC joins through the webclient
- **WHEN** an actor submits `explore.party_invite` for a present unbound `LLMNPC` and the dialogue reply carries `party_invite` with `accept: true`
- **THEN** the NPC's speech is shown, `join_party` binds the companion, and the actor receives the join notification

#### Scenario: Offline webclient invites fall back to the fixed threshold
- **WHEN** the `npc_dialogue` profile is disabled or unreachable and the actor submits `explore.party_invite`
- **THEN** the invitation accepts on `affinity >= 70` with a deterministic acceptance line and rejects below it, with no network request

#### Scenario: A full party blocks the webclient invite before the AI call
- **WHEN** a holder of four valid general identities submits a further ordinary invite
- **THEN** preflight refuses before dialogue; temporary escort rows do not themselves fill this quota

#### Scenario: Target resolution never trusts stale or remote references
- **WHEN** the `explore.party_invite` adapter re-resolves the NPC
- **THEN** it resolves only from the actor's current location's present contents — never a stored, remote, or ambiguous reference
- **AND** the adapter obtains the actor from the authenticated session, and obtains the profile client from the exploration composition root

#### Scenario: The composition root supplies a live client or a never-called stub
- **WHEN** the adapter obtains the `npc_dialogue` profile client from the exploration composition root
- **THEN** it is a live `OpenAICompatClient` when the profile is enabled, or a non-`None` offline stub when disabled — the stub is never called because the guardrail degrades before any transport work

#### Scenario: The degraded terminal decides on the fixed affinity threshold
- **WHEN** the exchange reaches the degraded terminal
- **THEN** the adapter applies the fixed threshold decision (`affinity >= 70`) with deterministic accept/reject lines

#### Scenario: The online terminal follows the AI decision
- **WHEN** the dialogue reply settles online
- **THEN** the adapter presents the reply's speech and routes the reply's intent through `apply_npc_intent`, rendering the join, refusal, full-party, duplicate, and remote notifications with the same fixed Traditional Chinese messages the `invite` command uses, and never overrides an AI decision with the threshold

#### Scenario: The Deferred publishes one newer snapshot without direct assignment
- **WHEN** the exchange seam settles
- **THEN** the adapter returns a Deferred that resolves to a safe success result after the seam settles, publishes a full snapshot at one newer revision so the applied membership binding refreshes atomically, and does not assign memory, intent, party, or affinity state directly

#### Scenario: An invalid invite rejects synchronously before client work
- **WHEN** the actor is absent, ambiguous, non-eligible, already-general, foreign-owned or the valid general quota is full
- **THEN** preflight rejects synchronously with no client/transport work or source changes

#### Scenario: Temporary identity does not bypass invitation judgment
- **WHEN** a temporary-only actor receives an ordinary invitation below the offline affinity threshold
- **THEN** ordinary offline refusal applies and its valid escort reasons remain; successful online acceptance adds only general identity

### Requirement: explore.party_leave dismisses a bound companion without affinity change
The existing explore.party_leave SHALL retain exactly npc_id and authenticated/local target checks. General-only dismissal SHALL use the party owner with existing possession/affinity gates. An active escort reason SHALL require selected commission abandonment in the existing mission drawer with two-step confirmation; the action SHALL never directly remove that reason. Multiple sources SHALL identify affected owned records and preserve non-selected/general sources.

#### Scenario: Webclient dismissal removes the binding
- **WHEN** an actor dismisses a present general-only companion under ordinary gates
- **THEN** party-owned removal and notification commit without affinity change; an escort-backed actor instead routes to its selected mission abandonment flow

#### Scenario: A webclient leave on an unbounded target rejects
- **WHEN** an actor submits `explore.party_leave` for a present NPC that is not a companion
- **THEN** the adapter rejects with a stable reason and no party or affinity state changes

#### Scenario: Target resolution never trusts stale or remote references
- **WHEN** the `explore.party_leave` adapter re-resolves the NPC
- **THEN** it resolves only from the actor's current location's present contents — never a stored, remote, or ambiguous reference

#### Scenario: Dismissal notifies, publishes, and assigns nothing directly
- **WHEN** a dismissal succeeds through `leave_party`
- **THEN** affinity is unchanged in either direction, the actor is notified with the fixed Traditional Chinese dismissal message shared with the `leave` command, a full snapshot is published at one newer revision, and the adapter does not assign party or affinity state directly

#### Scenario: An invalid leave rejects synchronously with no state change
- **WHEN** the NPC is missing, no-longer-present, or unbounded
- **THEN** the adapter rejects synchronously with a stable code and no state change

#### Scenario: Escort dismissal cannot silently detach
- **WHEN** explore.party_leave names a present actor with active escort reasons
- **THEN** those sources are not removed, existing mission choices name the affected owned records and confirm the selected quest_log abandon descriptor; cancellation preserves quest, possession and party state
