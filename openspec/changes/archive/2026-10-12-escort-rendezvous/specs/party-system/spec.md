# Spec Delta

## MODIFIED Requirements

### Requirement: Party membership is bounded, persistent, and single-writer
The party owner SHALL keep one ordered persistent ID roster and one NPC owner back-reference; metadata SHALL carry general membership and a unique set of temporary `(quest identity, protected role)` reasons. Ordinary join SHALL declare general membership, and the four-companion quota SHALL count valid general members alone. Temporary escort joining SHALL use the party owner API on an exact live owned protected binding, never stealing another owner's actor or duplicating a row.

#### Scenario: Full general party accepts an escort
- **WHEN** a player with four valid general companions accepts an available escort through the quest owner
- **THEN** the exact protected NPC becomes a fifth temporary-only row, general usage remains four, no member is evicted, and reload preserves the metadata and back-reference

#### Scenario: Dual membership and several reasons have one row
- **WHEN** a general member receives two valid escort reasons and one reason is released
- **THEN** it retains one row, general membership and quota usage, and the other reason; repeating the release changes nothing

#### Scenario: General recruitment remains bounded
- **WHEN** a temporary-only NPC is ordinarily recruited while the general quota is full or ordinary eligibility fails
- **THEN** recruitment refuses without changing the escort reason or granting general identity

#### Scenario: Normal join still validates ownership and presence
- **WHEN** general joining targets a remote, non-NPC, already-general, or another owner's bound actor
- **THEN** the ordinary named refusal changes neither roster nor metadata

#### Scenario: Paired write failure restores membership
- **WHEN** persistence fails after the roster write and before metadata or back-reference completion
- **THEN** live reads and committed reload equal the pre-operation state

#### Scenario: A valid join binds both sides
- **WHEN** a player ordinarily invites an eligible co-located NPC with two valid general companions
- **THEN** general membership, the ordered roster and owner back-reference commit together and general usage becomes three

#### Scenario: The party bound is four companions
- **WHEN** a player with four valid general companions attempts to recruit another general companion, including a temporary-only member
- **THEN** ordinary quota refusal changes no source or binding

#### Scenario: A remote NPC cannot join
- **WHEN** a player invites an NPC in another room
- **THEN** the join is rejected and no binding changes

#### Scenario: A duplicate join is a no-op
- **WHEN** general joining is attempted for an already-general member
- **THEN** the existing refusal/idempotence policy changes no stored source or binding

#### Scenario: A failed join restores both entities
- **WHEN** the NPC-side write fails after the player-side write applied
- **THEN** both database and in-process values return to their pre-join state and no partial binding is observable

#### Scenario: Membership survives a reload
- **WHEN** a player with companions disconnects and reconnects
- **THEN** `player.db.party` and each companion's `party_member` are unchanged

#### Scenario: An activation-bound companion behaves like an invited one
- **WHEN** a starting companion bound at activation is exercised through follow, combat, quest assist, and dismissal
- **THEN** every operation behaves exactly as it does for an invited companion, with no origin-dependent branch

#### Scenario: Both APIs commit their paired writes atomically
- **WHEN** `join_party` or `leave_party` commits
- **THEN** the player-side and NPC-side writes commit atomically, in one operation

#### Scenario: Both APIs are idempotent under re-application
- **WHEN** an already-committed join or leave is re-applied
- **THEN** the operation is idempotent and both entities' stored values are unchanged

#### Scenario: Both APIs restore caches on failure and survive reloads
- **WHEN** a party write fails, or the server reloads with committed membership
- **THEN** both entities' in-process caches are restored on failure, and committed membership survives reloads unchanged

#### Scenario: join_party has exactly two production callers
- **WHEN** `join_party`'s production callers are counted
- **THEN** there are exactly two — the player-initiated invite path and preset activation binding a declared starting companion — and neither caller assigns `player.db.party` or `npc.db.party_member` itself

#### Scenario: An activation-bound companion is indistinguishable to the auto-leave recheck
- **WHEN** the auto-leave recheck evaluates a companion bound at activation
- **THEN** it behaves exactly as it does for an invited companion, with no origin-dependent branch

#### Scenario: Membership writes commit paired state atomically
- **WHEN** a membership join, promotion or release commits
- **THEN** Persistent membership writes SHALL commit paired state atomically with cache restoration.

### Requirement: The invite command proposes a party through the AI-judged dialogue seam
The existing invite command SHALL use ordinary eligibility, dialogue judgment and offline affinity fallback to add general identity. Its preflight and commit checks SHALL reject already-general and foreign-owned actors, count only valid general identities toward four, and admit same-owner temporary-only actors without bypassing ordinary recruitment. Successful promotion SHALL preserve every escort reason and the deduplicated roster.

#### Scenario: A co-located NPC is invited and joins
- **WHEN** a player invites an eligible co-located NPC and the dialogue accepts
- **THEN** join_party adds general identity and notifies without duplicating its roster entry

#### Scenario: The NPC declines through the AI
- **WHEN** an eligible NPC declines through party_invite accept false
- **THEN** refusal speech appears and no general identity is added

#### Scenario: An illegal party intent keeps the speech
- **WHEN** the reply intent is invalid
- **THEN** speech is shown and no identity or escort reason changes

#### Scenario: Offline invitations fall back to the fixed threshold
- **WHEN** dialogue is unavailable for an otherwise eligible invite
- **THEN** the existing affinity threshold 70 determines general recruitment and preserves escort reasons

#### Scenario: The AI is not bound by the threshold
- **WHEN** online dialogue judges an eligible invite below affinity 70
- **THEN** the verified party_invite decision stands without a threshold override

#### Scenario: An AI decline is never overridden by the threshold
- **WHEN** online dialogue declines at affinity 70 or above
- **THEN** the refusal stands and no general identity is added

#### Scenario: Inviting an already-bound companion reports a clear result
- **WHEN** an invite targets an already-general actor or a foreign-owned actor
- **THEN** preflight rejects with the existing clear message before dialogue; same-owner temporary-only actors remain eligible under ordinary gates

#### Scenario: A non-dialogue NPC cannot be invited
- **WHEN** the present actor has no eligible free-form dialogue surface
- **THEN** preflight refuses before dialogue without source changes

#### Scenario: A party filled after the AI accepted is surfaced to the player
- **WHEN** dialogue accepts but valid general identities reach four before commit
- **THEN** speech remains and the full-party refusal adds no general identity or source

#### Scenario: A full party blocks the invite before the AI call
- **WHEN** a holder of four valid general identities proposes another general recruit
- **THEN** preflight rejects before dialogue regardless of temporary escort count

#### Scenario: The invite command surface is documented
- **WHEN** the command reference is inspected
- **THEN** invite aliases, syntax and general-identity recruitment rules are documented

#### Scenario: Target resolution mirrors talk's error contract
- **WHEN** a target is absent or ambiguous
- **THEN** existing localized talk-compatible errors appear without changes

#### Scenario: The deterministic preflight gate admits only eligible invitees
- **WHEN** invite preflight evaluates local actors
- **THEN** it requires ordinary eligible free-form dialogue, no existing general identity, same-owner or unbound ownership and available general quota; same-owner temporary membership is not a duplicate rejection

#### Scenario: The reply's speech reaches the player
- **WHEN** invitation dialogue settles
- **THEN** speech appears through the existing output path

#### Scenario: An accepted intent is rechecked and applied through join_party
- **WHEN** a verified accept true intent applies
- **THEN** join_party rechecks ordinary eligibility, co-location, ownership and general quota, adds general identity and preserves all escort sources

#### Scenario: An unavailable dialogue layer degrades to the fixed threshold
- **WHEN** the existing dialogue layer is disabled or unavailable
- **THEN** the existing fixed affinity threshold and deterministic lines apply with no new retry subsystem

#### Scenario: The webclient offers the same invite flow
- **WHEN** the webclient offers a normal invitation to a temporary-only actor
- **THEN** the same injected-client preflight and general recruitment flow apply

### Requirement: The leave command dismisses a companion without affinity change
The existing leave command and browser flow SHALL remove general membership without changing affinity. Effective escort reasons SHALL require abandonment of selected commissions through the quest owner; dismissal SHALL never silently detach them while their quests stay active, and several reasons SHALL expose the affected commissions and release only the selected ones.

#### Scenario: General dismissal preserves an escort
- **WHEN** a dual member's general membership is dismissed
- **THEN** its valid temporary reasons and row remain, general quota usage decreases, and affinity is unchanged

#### Scenario: Several commissions require a selection
- **WHEN** dismissal targets a temporary member bound to two active escorts
- **THEN** both commissions are identified; abandoning the selected commission terminates that record and releases its reason while preserving the other

#### Scenario: Ordinary possessed dismissal keeps the existing refusal
- **WHEN** manual dismissal targets a possessed general-only member
- **THEN** the existing handback-first refusal leaves control and membership unchanged

#### Scenario: Dismissal removes the binding
- **WHEN** a general-only companion is dismissed through the existing leave path
- **THEN** its general source, row and owner back-reference clear and the player is notified after commit

#### Scenario: Dismissal keeps affinity unchanged
- **WHEN** a player dismisses a companion with a 信賴-stage record
- **THEN** the NPC's affinity value is unchanged

#### Scenario: An unbounded target is rejected
- **WHEN** a player runs `leave` on an NPC that is not a companion
- **THEN** the command reports the Traditional Chinese error and no state changes

#### Scenario: The leave command surface is documented
- **WHEN** the command reference is inspected
- **THEN** `leave` and its alias appear in `docs/game/command-reference.md`

#### Scenario: A possessed companion refuses dismissal
- **WHEN** ordinary manual dismissal targets a possessed general-only companion
- **THEN** the existing handback-first refusal leaves membership and possession unchanged

#### Scenario: Possession refusal is enforced at both layers
- **WHEN** ordinary manual dismissal targets a possessed general-only member
- **THEN** command and party API both enforce the existing handback-first refusal

#### Scenario: Possessed dismissal and escort abandonment keep their refusals
- **WHEN** the dismissed member is possessed or carries several escort reasons
- **THEN** A possessed member's ordinary manual dismissal SHALL retain its handback-first refusal; escort abandonment SHALL use the compensated terminal release contract.

### Requirement: Companions auto-leave when affinity drops below the invite threshold
Negative affinity changes SHALL retain existing relationship writes. Automatic departure below the ordinary threshold SHALL be suppressed while any validated active escort reason remains. General-only members SHALL retain ordinary departure behavior and its handback/failure rules. Corrupt or expired temporary reasons SHALL grant no immunity.

#### Scenario: Valid escort survives a negative affinity delta
- **WHEN** a temporary member's affinity crosses below the invite threshold while its exact owned escort binding remains active
- **THEN** affinity changes but the NPC stays; a general-only control leaves under the existing rule

#### Scenario: Corrupt temporary source provides no immunity
- **WHEN** the reason references an unknown, terminal, invalidated, foreign-owned, or differently bound record
- **THEN** safe membership evaluation rejects that reason and automatic departure receives no escort exemption

#### Scenario: Below-threshold affinity ends the party
- **WHEN** a general-only member crosses below the ordinary invite threshold through a negative delta
- **THEN** the existing departure reason applies with ordinary transactional notification behavior

#### Scenario: At-threshold affinity keeps the party
- **WHEN** a general-only member reaches exactly the ordinary threshold
- **THEN** membership remains

#### Scenario: A failed auto-leave rolls back or aborts the affinity write
- **WHEN** the leave write fails after the affinity value was lowered below the threshold, or the
  possession release of a possessed companion fails
- **THEN** in the first case the affinity value and both party attributes return to their
  pre-delta values and in the second no delta is written at all; either way the companion remains
  bound (and possessed, if it was), and no notification is sent

#### Scenario: Non-companions are unaffected by the hook
- **WHEN** a negative delta applies to an NPC that is not a companion
- **THEN** no party call or notification occurs

#### Scenario: Auto-leaving a possessed companion releases first
- **WHEN** a possessed general-only companion has no valid escort reason and its affinity crosses below the threshold, requiring actual ordinary departure
- **THEN** the possession release commits before the affinity/party atomic opens, and a release
  failure leaves affinity, party binding, and possession all untouched

#### Scenario: A failed leave makes the bound-but-below-threshold state unreachable
- **WHEN** a general-only member departure fails within the negative-affinity operation
- **THEN** the entire ordinary affinity/party operation rolls back; valid escort immunity remains governed by its explicit source contract

### Requirement: Companions assist the player's quest objectives
Both membership kinds SHALL use the same safe owner attribution for DEFEAT contributions, with existing living, knockout, battlefield and one-transition rules. REACH SHALL retain its existing owner-arrival and companion co-presence gates. ESCORT SHALL use exact protected-role destination/rendezvous predicates without an unrelated-companion or original-body gate. Possessed NPCs SHALL remain physical actors and the player SHALL remain quest owner.

#### Scenario: Temporary actor contribution belongs to its owner
- **WHEN** a valid temporary companion produces a counting defeat in combat
- **THEN** the owner's matching record progresses once and the NPC receives no separate quest log

#### Scenario: Possessed protected actor can complete escort alone
- **WHEN** the exact possessed protected actor moves to its validated destination or live meeting role while the original player body and unrelated companions remain elsewhere
- **THEN** the owner's escort evaluates from the physical actor's result without moving the body or rewriting ownership

#### Scenario: A companion's kill advances the owner's DEFEAT objective
- **WHEN** a bound companion's action lethally defeats a monster matching the owner's active DEFEAT stage, with a valid bidirectional binding and an active battlefield
- **THEN** the owner's quest progress advances in the same action, capped and transitioned exactly once

#### Scenario: A knocked-out companion's kill grants no credit
- **WHEN** a knocked-out companion's action defeats a matching monster
- **THEN** the owner's quest progress is unchanged

#### Scenario: An unbound NPC's kill grants no credit
- **WHEN** an NPC that is not a bound companion defeats a matching monster
- **THEN** the owner's quest progress is unchanged

#### Scenario: A mismatched binding grants no credit
- **WHEN** an NPC whose back-reference points to the owner but who is absent from the owner's party list defeats a matching monster
- **THEN** the owner's quest progress is unchanged

#### Scenario: Companion co-presence satisfies an arrival objective
- **WHEN** the player arrives at the destination and at least one bound companion is present there, and the follow moves have completed
- **THEN** a matching REACH or ESCORT arrival advances exactly once

#### Scenario: Escort still requires every protected entity alive and present
- **WHEN** a companion is present at an ESCORT destination but a protected entity is absent or dead
- **THEN** the stage remains unchanged

#### Scenario: Companion kills run under the owner's own planner rules
- **WHEN** a valid companion kill advances the owner's DEFEAT stage
- **THEN** it advances through the same commit-time planner rules as the owner's own kills (same aggregation, cap, and one-transition rules)

#### Scenario: Non-counting entries and a missing battlefield fail closed
- **WHEN** the entry comes from a knocked-out companion, an unbound NPC, or a mismatched binding, or the credit decision has no active battlefield
- **THEN** no credit is granted — the entries do not count and the battlefield-less decision fails closed

#### Scenario: Nothing else grants credit and only the owner's record advances
- **WHEN** an unbound entity, another player's companion, or a monster produces the contribution
- **THEN** no credit is granted, and only the player's active quest record is ever advanced

#### Scenario: A REACH or ESCORT arrival advances on co-presence
- **WHEN** the player arrives at the destination and at least one bound companion is present in the destination room — already there or arriving with the player
- **THEN** the matching REACH or ESCORT arrival advances; ESCORT keeps requiring every protected entity alive and present

#### Scenario: The arrival observation reruns after follow and stays idempotent
- **WHEN** the arrival observation runs again after companions complete their follow moves
- **THEN** co-presence on the first arrival is visible, and the one-transition rule makes the repeated observation idempotent

## ADDED Requirements

### Requirement: Canonical effective membership drives every party consumer
Every party consumer SHALL use the same ordered bidirectionally validated effective member set. General identity or active exact owned escort reasons SHALL grant membership; stale/deleted/corrupt references SHALL not. Temporary membership SHALL retain ordinary lawful targeting, damage and knockout behavior.

#### Scenario: Real traversal and combat use the exact roster
- **WHEN** a temporary NPC follows an exit and a wilderness step, engages combat and receives damage
- **THEN** the same identity follows at most once, adds no clock charge, participates under ordinary combat/targeting policy, and received damage changes its real traits

#### Scenario: Safe readers reject broken membership
- **WHEN** stale roster IDs, mismatched back-references and corrupt temporary sources are read by each affected consumer
- **THEN** none yields owner attribution, possession permission, combat membership or affinity immunity

#### Scenario: Knockout retains existing engagement policy
- **WHEN** a temporary companion is knocked out and later recovers through existing lawful rules
- **THEN** the escort does not fabricate death and the existing knocked-out engagement behavior remains unchanged

#### Scenario: Complete canonical effective membership drives every party consumer contract
- **WHEN** the operation is exercised through its deterministic owner with valid and rejecting inputs
- **THEN** Safe readers SHALL accept general members or valid temporary reasons through the same bidirectionally validated ordered member set. Deleted, stale and corrupt references SHALL grant no membership. Owner lookup, following, combat collection, incoming targeting, affiliation, quest attribution, possession, affinity rechecks and presentation SHALL consume this set. Temporary membership SHALL preserve ordinary living/presence/knockout gates and lawful combat/damage behavior. Existing companion knockout rules SHALL remain applicable; actual committed death from lawful sources SHALL reach escort failure planning. No temporary-only invulnerability SHALL be introduced.
