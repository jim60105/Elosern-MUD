# Spec Delta

## MODIFIED Requirements

### Requirement: Successful retreat carries the entire present party and counts one round
Successful confirmed retreat SHALL atomically depart the whole present party, carry existing knocked-out companions, settle one attempt round and complete a real legal affordable traversal with normal travel time and physiology once, preserving old-encounter regeneration exclusions.

#### Scenario: Carried companion
- **WHEN** an acting ally retreats with a present knocked-out companion
- **THEN** both leave combat, the companion stays knocked out absent existing settlement recovery, no enemy action runs and elapsed time settles once

#### Scenario: Exactly once
- **WHEN** a successful retreat confirmation is duplicated across reconnect or restart
- **THEN** the party outcome and added round/time settle once, never leaving a subset in combat

#### Scenario: Post-round reserve and real travel
- **WHEN** the preferred previous reverse edge is legal and affordable using the reserve projected after the complete unpaid combat prefix and attempt
- **THEN** the party arrives there after one attempt round plus normal terrain/fatigue traversal; old-session exit and arrival history commit once, and actual travel retains ordinary physiology without an exit heal

#### Scenario: Exact arrival depletion
- **WHEN** the canonical movement plan reaches exactly zero reserve at arrival
- **THEN** the edge succeeds and applies real forced posture plus any immediate destination contact, without a grace flag

#### Scenario: Carry and remote members
- **WHEN** a present knocked-out companion and a remote companion accompany actual self-moving retreat actors
- **THEN** only present bodies arrive, carried bodies retain condition/applicable physiology without walking costs, and only actual self-moving members determine full-route speed/admission

#### Scenario: Examination edge
- **WHEN** a guild examination retreat succeeds
- **THEN** existing FAIL/opponent cleanup and confirmation authority remain, and the party travels a real legal edge from the actual exam room

#### Scenario: Late failure and fresh encounter replay
- **WHEN** movement, physiology, arrival admission or receipt writing fails, or a committed old receipt is retried after arrival opened a new session
- **THEN** failure restores the complete old session/source party and live caches, while committed replay neither repeats travel/payment nor mutates the new session

### Requirement: Retreat contests the slowest acting ally against the fastest pursuer
Confirmed retreat SHALL first require a legal adjacent route affordable after its attempt round, then retain the existing one-roll slowest-acting-ally versus fastest-pursuer agility contest; no pursuer SHALL skip only the roll and no acting ally SHALL retain ordinary defeat policy.

#### Scenario: Slowest member
- **WHEN** allied adjusted agilities are 10 and 20, pursuer maximum is 15, and d100 is 56
- **THEN** retreat succeeds at 66 >= 66 using the slower ally, independently of accuracy/Dodge

#### Scenario: No pursuers or no acting allies
- **WHEN** no pursuers remain or no allied member can act
- **THEN** no pursuers skips the roll only when a legal affordable route exists; no acting ally uses ordinary defeat

#### Scenario: Previous edge and lawful fallback
- **WHEN** the actual completed previous reverse edge is blocked/unaffordable or no valid history exists
- **THEN** choose reproducibly among other legal affordable neighbors without preferring monster-free/safe cells, consulting birth exclusions or blacklisting opponents

### Requirement: Failed retreat consumes all allied actions and runs one ordinary enemy upkeep round
A failed retreat SHALL keep the entire party in combat, consume every allied action opportunity, allow eligible enemies their normal initiative actions and run ordinary upkeep once. It SHALL cost no MP/SP, activate no Defend/Dodge/Taunt and execute no old draft command. A nonterminal failure SHALL create a fresh next-round draft.

#### Scenario: No draft or tactical benefit
- **WHEN** a party with pending attacks and tactical declarations confirms a retreat that fails
- **THEN** none of those entries executes or protects anyone; eligible enemy actions and upkeep run once and next-round selections are empty

#### Scenario: Failure rollback
- **WHEN** a technical failure occurs after enemy, upkeep or retreat metadata writes
- **THEN** all round state and caches restore together and the accepted operation remains safe to retry without double time

#### Scenario: No route or insufficient post-attempt energy
- **WHEN** every legal adjacent edge would deplete reserve before arrival, or none exists, even without pursuers
- **THEN** one ordinary failed attempt/enemy round occurs at the source, with no traversal time, movement charge or partial party move; malformed state instead refuses by name

### Requirement: Party exit requires a commander session round and operation bound confirmation
Retreat and surrender SHALL be session-level operations available independently of selected member. Both SHALL require explicit confirmation bound to commander, current session, round revision and operation. Cancel SHALL preserve the entire draft and advance no time. Stale, forged, replayed and competing confirmations SHALL NOT affect another session or round.

#### Scenario: Cancel and stale prompt
- **WHEN** a player cancels or later confirms a prompt after its session/round changed
- **THEN** cancel retains every draft entry; stale confirmation rejects without mutation or time

#### Scenario: Public bypass forbidden
- **WHEN** an allied personal flee skill or text alias requests exit
- **THEN** it reaches the same party confirmation boundary and cannot perform individual allied escape

#### Scenario: Captured route is scoped and revalidated
- **WHEN** retreat confirmation captures the actual previous edge and its gate/access or affordability changes before execution
- **THEN** the operation-bound server capture is revalidated and lawful fallback is evaluated; no client route, recycled room or invalidated teleport history can redirect the exit

### Requirement: Combat time settles once at terminal session outcome
Interactive rounds SHALL defer combat time until terminal settlement except for paid incapacitated-hostile continuation; a durable settled-round cursor SHALL charge each six-second round and its actual mental intervals once, preserve recorded occurrence times and clear terminal session state idempotently.

#### Scenario: Three-round victory advances eighteen seconds once
- **WHEN** a hostile session ends after three completed rounds
- **THEN** the world clock advances exactly 18 seconds with the combat source and not an additional cast
  cost per command

#### Scenario: Flee closes the same session
- **WHEN** the confirmed party retreat succeeds
- **THEN** the session settles one added retreat round plus prior elapsed rounds, clears the whole party combat state, and leaves no allied personal disengagement bypass

#### Scenario: A restarted terminal session is not settled twice
- **WHEN** a hostile session reached a terminal outcome and the process terminates before session clearing completes
- **THEN** after restart the session's accumulated time is settled exactly once, not again by session restoration

#### Scenario: Companion gauges regenerate from combat settlement
- **WHEN** a session with a wounded or knocked-out companion reaches a terminal outcome
- **THEN** the companion's HP/MP/SP are regenerated for only the remaining unpaid combat seconds, and a knocked-out
  companion rises above the nonlethal HP floor when its regen allows

#### Scenario: Settlement scope is the living non-fled roster
- **WHEN** a terminal settlement runs
- **THEN** the settlement entity scope is every living, non-fled member of the session's battlefield
  roster (player, companions, and any non-defeated foe still present), so all participants receive
  gauge regen for only the remaining unpaid combat interval; any previously paid prefix is excluded

#### Scenario: Population loss carries actual round offset
- **WHEN** a mapped session records a defeat in a later round before terminal-only clock settlement
- **THEN** the persisted start tick and completed-round offset identify its occurrence for delayed population settlement, without advancing the live clock early or double-settling rounds

#### Scenario: Paid automatic prefix
- **WHEN** enemy-only continuation pays prior unpaid rounds and its next real round, then ordinary play later terminates
- **THEN** the clock, gauges and physiology pay that prefix once and terminal settlement pays only remaining rounds; restart replay cannot pay it again

#### Scenario: Retreat has two distinct paid intervals
- **WHEN** a confirmed party retreat succeeds after prior paid or unpaid rounds
- **THEN** old combat pays only the unpaid prefix plus its attempt once, and the subsequent normal physical traversal is charged once; arrival contact never duplicates terminal billing
