# Spec Delta

## MODIFIED Requirements

### Requirement: Combat time settles once at terminal session outcome
Session rounds SHALL accumulate without command-default cast time. On enemy defeat, player defeat,
successful party retreat, nonlethal exam outcome, or bounded terminal condition, the total rounds times six
seconds SHALL settle once through `settle_combat_result()`. Then active session/context state SHALL
be cleared. The settlement SHALL be idempotent: a
terminal outcome SHALL record a durable settled marker so a restart that re-reads the session can
never settle the same rounds a second time.

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
- **THEN** the companion's HP/MP/SP are regenerated for the accumulated combat seconds, and a knocked-out
  companion rises above the nonlethal HP floor when its regen allows

#### Scenario: Settlement scope is the living non-fled roster
- **WHEN** a terminal settlement runs
- **THEN** the settlement entity scope is every living, non-fled member of the session's battlefield
  roster (player, companions, and any non-defeated foe still present), so all participants receive
  gauge regen for the accumulated combat time

## ADDED Requirements

### Requirement: Retreat contests the slowest acting ally against the fastest pursuer
Confirmed retreat SHALL replace all personal commands and attempt before ordinary actions. With pursuers it SHALL use one d100 plus minimum adjusted agility of allies able to act against 51 plus maximum adjusted agility of living present nonfled pursuers, reusing the existing flee constant. Accuracy and Dodge SHALL NOT modify this check.

#### Scenario: Slowest member
- **WHEN** allied adjusted agilities are 10 and 20, pursuer maximum is 15, and d100 is 56
- **THEN** retreat succeeds at 66 >= 66 using the slower ally, independently of accuracy/Dodge

#### Scenario: No pursuers or no acting allies
- **WHEN** no pursuers remain or no allied member can act
- **THEN** no pursuers gives automatic escape without a roll; no acting ally uses ordinary defeat

### Requirement: Successful retreat carries the entire present party and counts one round
A successful retreat SHALL remove the whole present party from combat, carrying knocked-out companions without including them in the agility minimum. Enemies SHALL take no action and exactly one elapsed combat round SHALL be added and settled. The operation SHALL add no healing, revival or invented relocation.

#### Scenario: Carried companion
- **WHEN** an acting ally retreats with a present knocked-out companion
- **THEN** both leave combat, the companion stays knocked out absent existing settlement recovery, no enemy action runs and elapsed time settles once

#### Scenario: Exactly once
- **WHEN** a successful retreat confirmation is duplicated across reconnect or restart
- **THEN** the party outcome and added round/time settle once, never leaving a subset in combat

### Requirement: Failed retreat consumes all allied actions and runs one ordinary enemy upkeep round
A failed retreat SHALL keep the entire party in combat, consume every allied action opportunity, allow eligible enemies their normal initiative actions and run ordinary upkeep once. It SHALL cost no MP/SP, activate no Defend/Dodge/Taunt and execute no old draft command. A nonterminal failure SHALL create a fresh next-round draft.

#### Scenario: No draft or tactical benefit
- **WHEN** a party with pending attacks and tactical declarations confirms a retreat that fails
- **THEN** none of those entries executes or protects anyone; eligible enemy actions and upkeep run once and next-round selections are empty

#### Scenario: Failure rollback
- **WHEN** a technical failure occurs after enemy, upkeep or retreat metadata writes
- **THEN** all round state and caches restore together and the accepted operation remains safe to retry without double time

