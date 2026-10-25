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
