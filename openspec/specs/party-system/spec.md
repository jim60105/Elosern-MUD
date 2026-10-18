## Purpose

Defines the party core: the bounded, persistent, single-writer membership binding between a player and up to four NPC companions (`world/rules/party.py` owns `player.db.party` and `npc.db.party_member`), the AI-judged `invite` / `leave` command surfaces with the fixed offline threshold fallback, the wired auto-leave rule that ends a party when affinity drops below the invite threshold, and the deletion-purge path that never lets a removed NPC consume a companion slot.

## Requirements

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

### Requirement: Deleting an NPC purges its party bindings

When an NPC is deleted (instance reclamation, scene teardown, or any `delete()`), the typeclass deletion hook SHALL invoke the party module's purge API, which SHALL remove the NPC's dbid from every player's `db.party` and clear the NPC's `party_member` in one transaction. A party API encountering a stale dbid (an NPC that no longer exists) SHALL treat it as an absent companion — never a crash — and a player's companion capacity SHALL never be permanently consumed by a deleted NPC.

#### Scenario: Deleting a companion frees its slot
- **WHEN** a bound companion NPC is deleted
- **THEN** the player's `db.party` no longer contains the NPC's dbid, the party size shrinks, and a fifth invitation becomes possible

#### Scenario: A stale dbid reads as an absent companion
- **WHEN** a party API encounters a party entry whose NPC no longer exists
- **THEN** the API treats it as absent without raising and the player's remaining companions stay intact

### Requirement: Companions follow the player through every exit traversal

The follow function SHALL resolve the commander from the traverser (the player character, or the owner of a possessed companion puppeted by that account), SHALL move every other party member present in the source room — the commander's body and every effective companion other than the traverser — to the destination on every exit success path, SHALL charge no world clock, SHALL emit no announce messages, SHALL leave the party binding unchanged, and SHALL never raise from a traversal hook.

#### Scenario: Companions follow a successful grid traversal
- **WHEN** a player with two companions in the source room traverses an ordinary or grid exit
- **THEN** both companions' locations equal the player's new location, the player's clock advance is unchanged by their movement, and the party binding is unchanged

#### Scenario: Companions follow through the wilderness gate
- **WHEN** a player with companions in the grid room enters the wilderness through a gate exit
- **THEN** each companion arrives at that gate's `approach_cell` through the provider API (the same cell the player landed on — never a footprint cell), and the player's clock advance reflects only the player's `wilderness_move` cost

#### Scenario: Companions follow an ordinary wilderness step
- **WHEN** a player with companions in the same wilderness room steps to a neighboring coordinate
- **THEN** each companion moves to the player's new coordinates through the provider API with no additional clock charge

#### Scenario: Companions follow the wilderness return to the grid
- **WHEN** a player with companions in the wilderness returns through the registered gate
- **THEN** each companion arrives in the grid room with the player and no additional clock charge occurs

#### Scenario: A companion move failure leaves the companion behind
- **WHEN** a destination rejects one companion's move
- **THEN** that companion stays at its current location, the player receives the 跟丟了 notification naming it, the other companions still follow, and no state other than the notification changes

#### Scenario: Follow never charges the clock
- **WHEN** a player with companions traverses any exit
- **THEN** the world clock advances by exactly the player's movement cost, with no additional advance attributable to the companions

#### Scenario: An empty party traverses with no side effects
- **WHEN** a player with no companions traverses an exit
- **THEN** the traversal behaves exactly as before this change and no notification is emitted

#### Scenario: A bound companion in another room is not pulled
- **WHEN** a player whose companion is in a different room traverses an exit
- **THEN** the companion's location is unchanged and no notification is emitted

#### Scenario: Non-exit relocation does not pull companions
- **WHEN** a player is relocated by a teleport, spawn, or other non-exit move
- **THEN** the companions' locations are unchanged

#### Scenario: A stale party entry never blocks follow
- **WHEN** the player's party list contains the dbid of a deleted NPC
- **THEN** the follow skips the stale entry, the remaining companions still follow, and no exception is raised

#### Scenario: A left-behind companion rejoins on a later traversal
- **WHEN** a companion failed to follow and the player later traverses an exit from the companion's current room
- **THEN** the companion follows on that traversal and the player receives no repeated notification

#### Scenario: Every exit success path invokes follow
- **WHEN** an exit traversal succeeds
- **THEN** follow is invoked from the shared `MovementCostMixin.at_post_traverse` hook (grid, instance, and base exits), the wilderness gate entry branch (`WildernessGateExit.at_traverse`), the wilderness return branch, and the ordinary wilderness step branch (`WildernessReturnExit.at_traverse`)

#### Scenario: Companion moves use the traversal-appropriate move API
- **WHEN** companions follow through any exit type
- **THEN** grid and instance destinations are reached through quiet `move_to`, and wilderness entry and wilderness steps move companions through the wilderness provider's coordinate API (`enter_wilderness` / `script.move_obj`), never through a plain `move_to` into a wilderness room

#### Scenario: One fixed left-behind notification names every companion per traversal
- **WHEN** one or more companions' follow moves fail in a traversal
- **THEN** each failed companion remains at its current location and the player receives one fixed Traditional Chinese 「跟丟了」 notification per traversal naming every companion left behind

#### Scenario: Follow triggers only on exit paths
- **WHEN** the player is relocated by a teleport, spawn, or other non-exit move, or a bound companion waits in a different room
- **THEN** follow does not trigger: companions are not pulled, and a bound companion in a different room is not teleported to the player

#### Scenario: The whole party follows a possessed traversal
- **WHEN** the player possesses 艾拉 and walks her through an exit while the player's own body and companion 卡恩 share her source room
- **THEN** the player's body and 卡恩 arrive in 艾拉's destination through the same follow moves, with no additional clock charge and the party and possession bindings unchanged

#### Scenario: The owner body follows quietly and stays entranced
- **WHEN** the player's own body follows a possessed traversal
- **THEN** the destination's `at_pre_object_receive` gate is run for the body first, the body then moves with `move_to(..., quiet=True, move_hooks=False)` (or the wilderness provider API), so no `PlayerCharacter.at_post_move` side effect (action options, arrival lore, encounter activation) is attributed to it, the commander's map knowledge records the destination once, the body keeps its entranced presentation and possession mirror, and it is never puppeted by the move

#### Scenario: A destination that refuses the body leaves it behind
- **WHEN** the destination's receive gate refuses the player's body during a possessed traversal
- **THEN** the body stays in the source room, the other members still follow, and the acting session receives the one 跟丟了 notification naming the body

#### Scenario: A body left in a recycled wilderness room is still found
- **WHEN** a failed wilderness follow leaves the unpuppeted body registered at the source coordinates after the contrib recycled its room
- **THEN** a later possessed traversal from those coordinates still treats the body as co-located through the wilderness registration predicate and it follows

#### Scenario: Party members stay together under possession
- **WHEN** the player, while possessing a companion, traverses several exits in a row with every follow succeeding
- **THEN** after each traversal the commander's body and every effective companion share the traverser's room

### Requirement: Companions fight as allies in the player's combat session
When the player engages a hostile target, `engage` SHALL include every bound companion that is co-located, living, and not knocked out in the session's allied team (`player_ids`). Each companion SHALL receive at most one deterministic policy request per round through the session's non-player action provider, and SHALL NOT consume or delay the player's queued request.

#### Scenario: Co-located living companions join the engagement
- **WHEN** a player with two co-located living bound companions engages a monster
- **THEN** both companions are in the session's allied team, the battlefield roster contains them,
  and the party binding is unchanged

#### Scenario: Distant, dead, or knocked-out companions do not join
- **WHEN** a player's bound companion is in another room, has HP 0, or is marked knocked out
- **THEN** that companion is absent from the session's allied team

#### Scenario: Companions act once per round through the policy provider
- **WHEN** one round runs with a player, two companions, and two monsters
- **THEN** the player's request is supplied exactly once, each companion receives at most one
  deterministic policy request targeting the opposing team, and each monster receives at most one

#### Scenario: A damage skill may select a companion as its explicit target
- **WHEN** the player resolves a freely-targetable (ANY) damage skill with a companion as the
  explicit target
- **THEN** the companion appears among the selectable targets and the hit applies the
  friendly-fire penalty contract instead of being rejected at the faction check

#### Scenario: A companion's fallback policy attacks the opposing team without fleeing
- **WHEN** a companion (which has no monster threat tier) acts through the policy provider
- **THEN** its request targets an opposing-team combatant and is never a flee request

#### Scenario: The two-team model treats companions as allies
- **WHEN** the battlefield relates to a companion
- **THEN** `relation_to` returns ALLY for it, freely-targetable (ANY) skills and the `all-allies` shorthand may include it, and opposing-team combatants are able to target companions

#### Scenario: Companion hits obey the friendly-fire penalty contract
- **WHEN** the player selects a companion as an explicit damage target
- **THEN** the hit applies the friendly-fire penalty contract (affinity-friendly-fire) rather than being rejected

#### Scenario: Companions share the monsters' policy pipeline
- **WHEN** a companion's per-round policy request is produced
- **THEN** it runs through the same `monster_behaviour_policy` pipeline monsters use, whose target selection is team-relative

### Requirement: Knocked-out companions are persistent battlefield state and can never die
A companion whose HP crosses from positive to non-positive SHALL be knocked out nonlethally: HP floors at 1, `target_knocked_out` is emitted, `target_defeated` is not, and no kill credit, XP, DEFEAT progress, or loot consumer observes a companion death. The party binding SHALL remain unchanged throughout.

#### Scenario: A companion's lethal crossing becomes a knockout
- **WHEN** a monster's damage would cross a companion's HP from positive to non-positive
- **THEN** the companion's HP floors at 1, `target_knocked_out` is emitted, no `target_defeated`
  entry exists, and the battlefield marks the companion knocked out within the same commit

#### Scenario: Hostile kills stay lethal
- **WHEN** identical damage would cross a monster's HP from positive to non-positive
- **THEN** the ordinary lethal crossing and `target_defeated` behavior apply unchanged

#### Scenario: A knocked-out companion stops acting and cannot be targeted
- **WHEN** a companion is knocked out and the next round runs
- **THEN** the companion receives no policy request, is excluded from the player's `all-allies`
  expansion and from opposing-team target selection, and every remaining participant still acts

#### Scenario: Knockout state survives a rebuild
- **WHEN** a session with a knocked-out companion is reconstructed (e.g. after a reload)
- **THEN** the companion is still excluded from action, targeting, and terminal checks

#### Scenario: A knocked-out companion cannot re-engage before recovery
- **WHEN** a session ends with a companion knocked out and the player engages again before the
  companion's HP rose above 1
- **THEN** the companion does not join the new session's allied team

#### Scenario: Recovery clears the knockout marker
- **WHEN** a knocked-out companion's HP rises above 1 through clock-driven regen
- **THEN** the companion may join a later engagement as a living participant

#### Scenario: The knockout is marked, persisted, and reconstructed
- **WHEN** a companion knockout commits
- **THEN** it is marked on the battlefield at damage-commit time, persisted in the session record's `knocked_out_ids`, and reconstructed on battlefield rebuild

#### Scenario: A knocked-out companion is excluded from every battlefield role
- **WHEN** a companion is knocked out
- **THEN** it is excluded from initiative order, from receiving policy requests, from all target selection (the player's `all-allies`, opposing-team enemy selection, and AREA shortcuts), from overwhelm classification, and from the terminal living checks

#### Scenario: The knockout marker clears only through clock-driven regen
- **WHEN** a companion carries the knockout marker
- **THEN** the marker clears only when the companion's HP rises above 1 through the ordinary clock-driven regen, and until then the companion does not join a new engagement

### Requirement: Combat terminal rules are player-centric
The session SHALL end in defeat when the player (the session owner) is defeated — HP at or below
zero or marked knocked out — even when companions remain standing; it SHALL end in victory when
every opposing-team combatant is defeated or fled; flee, forfeit, and the round cap SHALL behave
unchanged. A knocked-out companion SHALL NOT end the session. Settlement, flee, forfeit,
skip-safety registration, and the party binding SHALL be unchanged by companion participation.

#### Scenario: Player defeat ends the session with companions alive
- **WHEN** the player's HP crosses to zero or the player is knocked out while companions still stand
- **THEN** the session settles its elapsed rounds and clears combat state as an ordinary defeat

#### Scenario: Victory requires only the foes team to be gone
- **WHEN** every foe is defeated or fled while the player and companions remain
- **THEN** the session settles as victory

#### Scenario: A knocked-out companion does not end the session
- **WHEN** a companion is knocked out while the player and foes remain active
- **THEN** the session persists and the player's next action continues the round loop

#### Scenario: Knocked-out companions recover after combat
- **WHEN** a session ends with a companion knocked out at 1 HP
- **THEN** the binding remains and the companion's HP regenerates through the ordinary clock-driven
  regen over subsequent world-time advances, clearing the knockout marker above 1 HP

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

### Requirement: Completing a quest rewards each then-in-party companion with affinity
Quest reward settlement SHALL grant the declared quest-completion affinity (source `quest_completion`, exempt from the daily cap) to every companion in the player's party at turn-in, through the sole-writer affinity API (`world/rules/affinity.py`), committed atomically with the reward transaction. Companions SHALL receive no XP, items, or merit.

#### Scenario: Turn-in rewards the party with affinity
- **WHEN** a player turns in a completed quest with two bound companions in the party
- **THEN** each companion's affinity value rises by the declared quest-completion gain, alongside the ordinary reward surfaces, in
  one committed operation

#### Scenario: Only then-in-party companions earn the bonus
- **WHEN** a player turns in a quest while one bound companion is in the party and another is not
- **THEN** only the in-party companion's affinity rises by the declared quest-completion gain

#### Scenario: A quest-completion gain bypasses the daily cap
- **WHEN** a companion's interaction budget is exhausted for the day and a turn-in grants the bonus
- **THEN** the the declared quest-completion applies and the daily interaction counter is unchanged

#### Scenario: A failed reward write restores every surface
- **WHEN** any reward or affinity write is fault-injected after preceding writes
- **THEN** wallet, inventory, merit, quest log, claims, and every companion's affinity record ;  and
  their in-process caches ;  equal their pre-turn-in values

#### Scenario: Every reward surface commits in one transaction
- **WHEN** a quest turn-in commits
- **THEN** wallet, inventory, merit, ACQUIRE progress, claims, and every affected companion's affinity record commit together in the one atomic reward transaction

#### Scenario: Independently known cap-order fixture
- **WHEN** a synthetic quest rule grants 2 to value 99 and raises cap to 150
- **THEN** the committed value is 101, whereas a failed reward commit restores both value 99 and cap 99; this does not pin the production quest gain

### Requirement: Combat settlement includes companions in the regen scope

The terminal settlement of a combat session SHALL apply the combat-time gauge regen to every living, non-fled roster member, including bound companions, so a knocked-out companion can recover above the nonlethal HP floor and rejoin later engagements.

#### Scenario: Knocked-out companion recovers through combat settlement

- **WHEN** a session with a companion floored at 1 HP reaches a terminal outcome whose accumulated combat seconds exceed what its regen needs to rise above 1
- **THEN** the companion's HP rises above 1 and the companion is eligible for a later engagement

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
