## Purpose

Defines the party core: the bounded, persistent, single-writer membership binding between a player and up to four NPC companions (`world/rules/party.py` owns `player.db.party` and `npc.db.party_member`), the AI-judged `invite` / `leave` command surfaces with the fixed offline threshold fallback, the wired auto-leave rule that ends a party when affinity drops below the invite threshold, and the deletion-purge path that never lets a removed NPC consume a companion slot.

## Requirements

### Requirement: Party membership is bounded, persistent, and single-writer

`world/rules/party.py` SHALL be the sole writer of party membership: `player.db.party` holds the list of companion NPC dbids (at most 4) and each companion's `npc.db.party_member` holds the player's dbid. `join_party(npc, player)` SHALL require an NPC target, co-location (same room), no existing binding, and a party below the 4-companion bound; `leave_party(npc, player, reason)` SHALL remove the binding regardless of the reason. Both SHALL commit the player-side and NPC-side writes atomically, SHALL restore both entities' in-process caches on failure, SHALL be idempotent under re-application, and SHALL survive reloads.

#### Scenario: A valid join binds both sides
- **WHEN** a player invites a co-located NPC with 2 companions already
- **THEN** the NPC appears in `player.db.party`, the NPC's `party_member` is the player, and the party size is 3

#### Scenario: The party bound is four companions
- **WHEN** a player with 4 companions invites a fifth NPC
- **THEN** the join is rejected with a full-party outcome and no binding changes

#### Scenario: A remote NPC cannot join
- **WHEN** a player invites an NPC in another room
- **THEN** the join is rejected and no binding changes

#### Scenario: A duplicate join is a no-op
- **WHEN** a join is attempted for an NPC already bound to the player
- **THEN** the join is rejected and no binding changes

#### Scenario: A failed join restores both entities
- **WHEN** the NPC-side write fails after the player-side write applied
- **THEN** both database and in-process values return to their pre-join state and no partial binding is observable

#### Scenario: Membership survives a reload
- **WHEN** a player with companions disconnects and reconnects
- **THEN** `player.db.party` and each companion's `party_member` are unchanged

### Requirement: The invite command proposes a party through the AI-judged dialogue seam

The character cmdset SHALL provide `invite <npc> [訊息]` (aliases 邀請, 組隊) that resolves a local NPC target (absent or ambiguous targets produce Traditional Chinese errors, mirroring `talk`), preflights the deterministic gate (an NPC with an eligible free-form dialogue surface — an `LLMNPC` — not already a companion, party not full), and then sends the player's invitation message through the guarded dialogue seam with the NPC's affinity context; a webclient action SHALL offer the same flow with the injected client. The reply's speech SHALL be shown to the player. A `party_invite {accept: true}` intent SHALL be verified and applied through `join_party` (rechecking co-location, binding, and the 4-companion bound) and the player SHALL be notified of the joined companion; `accept: false` SHALL notify of the refusal and change nothing; any illegal or unverifiable intent SHALL keep the speech and change nothing. When the dialogue layer is disabled, unreachable, or retry-exhausted, the invitation SHALL degrade to a fixed threshold decision (`affinity >= 70`, the 羈絆 stage floor) with deterministic accept/reject lines; the AI, when present, SHALL NOT be bound by that threshold.

#### Scenario: A co-located NPC is invited and joins
- **WHEN** a player invites a co-located NPC and the dialogue reply carries `party_invite` with `accept: true`
- **THEN** the player sees the NPC's speech and a join notification, and the membership binding exists

#### Scenario: The NPC declines through the AI
- **WHEN** a player invites an NPC and the dialogue reply carries `party_invite` with `accept: false`
- **THEN** the player sees the NPC's refusal speech and no binding is created

#### Scenario: An illegal party intent keeps the speech
- **WHEN** the reply's intent is not a valid `party_invite` payload
- **THEN** the speech is shown, the intent is discarded, and no binding is created

#### Scenario: Offline invitations fall back to the fixed threshold
- **WHEN** the dialogue layer is unavailable and the NPC's affinity is 70 or higher
- **THEN** the invitation succeeds with a deterministic acceptance line and the binding is created; below 70 it is refused with a deterministic rejection line

#### Scenario: The AI is not bound by the threshold
- **WHEN** the dialogue layer is available and the NPC's affinity is below 70
- **THEN** the decision is entirely the reply's `party_invite` value — the threshold never overrides it

#### Scenario: An AI decline is never overridden by the threshold
- **WHEN** the dialogue layer is available, the reply's intent is `party_invite` with `accept: false`, and the NPC's affinity is 70 or higher
- **THEN** the refusal stands, the threshold is not consulted, and no binding is created

#### Scenario: Inviting an already-bound companion reports a clear result
- **WHEN** a player invites an NPC that is already a companion
- **THEN** the invite is rejected before any dialogue call with a Traditional Chinese message and no state changes

#### Scenario: A non-dialogue NPC cannot be invited
- **WHEN** a player invites a present NPC without an eligible free-form dialogue surface
- **THEN** the invite is rejected before any dialogue call with a Traditional Chinese message and no state changes

#### Scenario: A party filled after the AI accepted is surfaced to the player
- **WHEN** the AI replies `accept: true` but the party became full before `join_party` ran
- **THEN** the NPC's speech is shown, the join is rejected with the full-party reason, and the player receives the fixed Traditional Chinese full-party message

#### Scenario: A full party blocks the invite before the AI call
- **WHEN** a player with 4 companions invites a fifth NPC
- **THEN** the invite is rejected with a full-party error and no dialogue call is made

#### Scenario: The invite command surface is documented
- **WHEN** the command reference is inspected
- **THEN** `invite` and its aliases and syntax appear in `docs/game/command-reference.md`

### Requirement: The leave command dismisses a companion without affinity change

The character cmdset SHALL provide `leave <npc>` (alias 解散) that resolves a bound companion (absent, ambiguous, or unbounded targets produce Traditional Chinese errors) and dismisses it through `leave_party(npc, player, reason="dismissed")`. Dismissal SHALL NOT change affinity in either direction and SHALL notify the player. A webclient action SHALL offer the same flow.

#### Scenario: Dismissal removes the binding
- **WHEN** a player dismisses a bound companion
- **THEN** `player.db.party` and the NPC's `party_member` are cleared and the player is notified

#### Scenario: Dismissal keeps affinity unchanged
- **WHEN** a player dismisses a companion with a 信賴-stage record
- **THEN** the NPC's affinity value is unchanged

#### Scenario: An unbounded target is rejected
- **WHEN** a player runs `leave` on an NPC that is not a companion
- **THEN** the command reports the Traditional Chinese error and no state changes

#### Scenario: The leave command surface is documented
- **WHEN** the command reference is inspected
- **THEN** `leave` and its alias appear in `docs/game/command-reference.md`

### Requirement: Companions auto-leave when affinity drops below the invite threshold

The auto-leave recheck hook installed by `affinity-system` SHALL be wired: after every negative affinity delta, when the NPC is a bound companion and the NPC's affinity toward the player drops below the invite threshold (70), the hook SHALL call `leave_party(npc, player, reason="affinity_below_threshold")` as part of the affinity write's transaction — a failed leave SHALL roll back the entire negative-delta operation so "affinity below threshold but still bound" is unreachable — and the write API SHALL return the auto-leave notification line, which the caller SHALL send to the player only after its own transaction commits. The writer SHALL never send the notification itself. A negative delta that leaves affinity at or above the threshold SHALL NOT end the party.

#### Scenario: Below-threshold affinity ends the party
- **WHEN** a bound companion's affinity drops from 70 to 69 through a negative delta
- **THEN** the party binding is removed with the auto-leave reason, the write API returns the notification line, and the caller notifies the player only after the write commits

#### Scenario: At-threshold affinity keeps the party
- **WHEN** a bound companion's affinity drops to exactly 70 through a negative delta
- **THEN** the party binding remains

#### Scenario: A failed auto-leave rolls back the affinity write
- **WHEN** the leave write fails after the affinity value was lowered below the threshold
- **THEN** the affinity value and both party attributes return to their pre-delta values, the companion remains bound, and no notification is sent

#### Scenario: Non-companions are unaffected by the hook
- **WHEN** a negative delta applies to an NPC that is not a companion
- **THEN** no party call or notification occurs

### Requirement: Deleting an NPC purges its party bindings

When an NPC is deleted (instance reclamation, scene teardown, or any `delete()`), the typeclass deletion hook SHALL invoke the party module's purge API, which SHALL remove the NPC's dbid from every player's `db.party` and clear the NPC's `party_member` in one transaction. A party API encountering a stale dbid (an NPC that no longer exists) SHALL treat it as an absent companion — never a crash — and a player's companion capacity SHALL never be permanently consumed by a deleted NPC.

#### Scenario: Deleting a companion frees its slot
- **WHEN** a bound companion NPC is deleted
- **THEN** the player's `db.party` no longer contains the NPC's dbid, the party size shrinks, and a fifth invitation becomes possible

#### Scenario: A stale dbid reads as an absent companion
- **WHEN** a party API encounters a party entry whose NPC no longer exists
- **THEN** the API treats it as absent without raising and the player's remaining companions stay intact

### Requirement: Companions follow the player through every exit traversal

The follow function in the party module SHALL move every companion of the traversing player who is present in the source room to the player's destination, and SHALL be invoked from every exit success path: the shared `MovementCostMixin.at_post_traverse` hook (grid, instance, and base exits), the wilderness gate entry branch (`WildernessGateExit.at_traverse`), the wilderness return branch, and the ordinary wilderness step branch (`WildernessReturnExit.at_traverse`). Companion movement SHALL charge no world clock, SHALL emit no announce messages, SHALL leave the party binding unchanged, and SHALL never raise from any traversal hook. Grid and instance destinations SHALL be reached through quiet `move_to`; wilderness entry and wilderness steps SHALL move companions through the wilderness provider's coordinate API (`enter_wilderness` / `script.move_obj`), never through a plain `move_to` into a wilderness room. A companion whose move fails SHALL remain at its current location and the player SHALL receive one fixed Traditional Chinese 「跟丟了」 notification per traversal naming every companion left behind. Follow SHALL trigger only on the exit paths above; teleports, spawns, and other non-exit relocations SHALL NOT pull companions, and a bound companion in a different room SHALL NOT be teleported to the player.

#### Scenario: Companions follow a successful grid traversal
- **WHEN** a player with two companions in the source room traverses an ordinary or grid exit
- **THEN** both companions' locations equal the player's new location, the player's clock advance is unchanged by their movement, and the party binding is unchanged

#### Scenario: Companions follow through the wilderness gate
- **WHEN** a player with companions in the grid room enters the wilderness through the gate exit
- **THEN** each companion arrives at the entry wilderness coordinates through the provider API, and the player's clock advance reflects only the player's `wilderness_move` cost

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

### Requirement: Companions fight as allies in the player's combat session
When the player engages a hostile target, `engage` SHALL include every bound companion that is
co-located, living, and not knocked out in the session's allied team (`player_ids`). The
battlefield's two-team model SHALL treat companions as allies: `relation_to` returns ALLY for
them, freely-targetable (ANY) skills and the `all-allies` shorthand may include them, and the
player SHALL be able to select companions as explicit damage targets — companion hits apply the
friendly-fire penalty contract (affinity-friendly-fire) rather than being rejected; opposing-team
combatants SHALL be able to target
companions. Each companion SHALL receive at most one deterministic policy request per round
through the session's non-player action provider (the same `monster_behaviour_policy` pipeline
monsters use, whose target selection is team-relative), and SHALL NOT consume or delay the
player's queued request.

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

### Requirement: Knocked-out companions are persistent battlefield state and can never die
A companion whose HP crosses from positive to non-positive SHALL be knocked out nonlethally: HP
floors at 1, `target_knocked_out` is emitted, `target_defeated` is not, and no kill credit, XP,
DEFEAT progress, or loot consumer observes a companion death. The knockout SHALL be marked on the
battlefield at damage-commit time, SHALL be persisted in the session record's `knocked_out_ids`,
and SHALL be reconstructed on battlefield rebuild. A knocked-out companion SHALL be excluded from
initiative order, from receiving policy requests, from all target selection (the player's
`all-allies`, opposing-team enemy selection, and AREA shortcuts), from overwhelm classification,
and from the terminal living checks. The knockout marker SHALL clear only when the companion's HP
rises above 1 through the ordinary clock-driven regen; until then the companion SHALL NOT join a
new engagement. The party binding SHALL remain unchanged throughout.

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
A bound companion's contributions SHALL count toward the quest owner's active objectives: a
DEFEAT entry produced by a bound companion's action SHALL advance the owner's matching DEFEAT
stage through the same commit-time planner rules as the owner's own kills (same aggregation,
cap, and one-transition rules), only while the binding is valid in both directions (the actor
appears in the owner's valid party list and the actor's back-reference points to the owner) and
the actor is not knocked out; a knocked-out companion's, unbound NPC's, or mismatched binding's
entries SHALL NOT count, and a credit decision without an active battlefield SHALL fail closed.
A REACH or ESCORT arrival SHALL advance when the player arrives at the destination and at least
one bound companion is present in the destination room — already there or arriving with the
player; ESCORT SHALL keep requiring every protected entity alive and present. The arrival
observation SHALL run again after companions complete their follow moves, so co-presence on the
first arrival is visible, and the one-transition rule SHALL make the repeated observation
idempotent. Unbound entities, other players' companions, and monster kills SHALL grant no credit.
The player's active quest record SHALL be the only record advanced; companions SHALL have no quest
log of their own.

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

### Requirement: Completing a quest rewards each then-in-party companion with affinity
Quest reward settlement SHALL grant +2 affinity (source `quest_completion`, exempt from the daily
cap) to every companion in the player's party at turn-in, through the sole-writer affinity API
(`world/rules/affinity.py`), committed atomically with the reward transaction: wallet, inventory,
merit, ACQUIRE progress, claims, and every affected companion's affinity record SHALL commit
together, and a fault at any write position SHALL restore all surfaces including the affinity
records and their in-process caches. Companions SHALL receive no XP, items, or merit.

#### Scenario: Turn-in rewards the party with affinity
- **WHEN** a player turns in a completed quest with two bound companions in the party
- **THEN** each companion's affinity value rises by 2, alongside the ordinary reward surfaces, in
  one committed operation

#### Scenario: Only then-in-party companions earn the bonus
- **WHEN** a player turns in a quest while one bound companion is in the party and another is not
- **THEN** only the in-party companion's affinity rises by 2

#### Scenario: A quest-completion gain bypasses the daily cap
- **WHEN** a companion's interaction budget is exhausted for the day and a turn-in grants the bonus
- **THEN** the +2 applies and the daily interaction counter is unchanged

#### Scenario: A failed reward write restores every surface
- **WHEN** any reward or affinity write is fault-injected after preceding writes
- **THEN** wallet, inventory, merit, quest log, claims, and every companion's affinity record — and
  their in-process caches — equal their pre-turn-in values

### Requirement: Combat settlement includes companions in the regen scope

The terminal settlement of a combat session SHALL apply the combat-time gauge regen to every living, non-fled roster member, including bound companions, so a knocked-out companion can recover above the nonlethal HP floor and rejoin later engagements.

#### Scenario: Knocked-out companion recovers through combat settlement

- **WHEN** a session with a companion floored at 1 HP reaches a terminal outcome whose accumulated combat seconds exceed what its regen needs to rise above 1
- **THEN** the companion's HP rises above 1 and the companion is eligible for a later engagement
