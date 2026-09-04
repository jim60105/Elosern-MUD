# Delta: scripted-dialogue

## MODIFIED Requirements

### Requirement: Scripted dialogue hosts answer authored talk lines

An NPC carrying a `ScriptedDialogue` component SHALL answer known keywords with
the authored response and unknown keywords with the no-understanding line,
without causing state change except that a known-keyword answer SHALL grant +1 affinity
(`talk` source) with the host through the sole-writer affinity API (`world/rules/affinity.py`),
applied by the deterministic talk writer in the same transaction as the answer; unknown keywords
and no-keyword paths SHALL NOT write any state.
`talk <npc>` without a keyword SHALL present the host's authored greeting when one is configured,
and the no-response line when it is not. An NPC without any dialogue component SHALL keep yielding
the no-response line. The
`guild_staff` host SHALL be the dialogue action exception: the keyword `回報`
SHALL resolve the read-only reportable-quest listing through the deterministic
guild service without granting the talk affinity, and `talk <guild-staff> 回報 <quest_id>` SHALL
turn in exactly that quest through `turn_in_quest` with the same atomic exactly-once
settlement and rejection semantics as `guild turnin`. Every other `guild_staff`
keyword SHALL grant the same +1 affinity as any other known-keyword answer.
Before answering, the scripted-talk entry path SHALL consult
`world/rules/npc_schedules.py::interaction_reason(npc, "talk")`; a non-`None` result SHALL present
that stable rejection line and SHALL write no state — the +1 affinity and
turn-in paths are both bypassed for the blocked interaction.

#### Scenario: Guild staff answers a known keyword
- **WHEN** the player talks to the guild master with a keyword such as 公會 or 任務
- **THEN** the guild master answers with the authored response for that keyword, the host's
  affinity value rises by 1, and no other state changes

#### Scenario: No-keyword talk presents the host's greeting
- **WHEN** the player runs `talk <guild-master>` without a keyword
- **THEN** the guild master presents its authored greeting teaching the guild
  commands, and no state changes (including no affinity change)

#### Scenario: Missing greeting falls back to the no-response line
- **WHEN** the player runs `talk <scripted-host>` without a keyword and the host
  has no configured greeting
- **THEN** the player receives the no-response line and no state changes

#### Scenario: Unknown keyword yields the no-understanding line
- **WHEN** the player talks to a scripted dialogue host with an unrecognized
  keyword
- **THEN** the host gives the no-understanding line and no state changes

#### Scenario: Componentless NPC still yields no response
- **WHEN** the player talks to an NPC that carries neither dialogue component
- **THEN** the player receives the no-response line and no state changes

#### Scenario: Guild staff 回報 keyword lists reportable quests read-only
- **WHEN** a registered player with completed, unclaimed quests talks to the
  guild staff with the keyword `回報` and no quest id
- **THEN** the staff answers with the deterministic reportable-quest listing in
  `(accepted_tick, quest_id)` order and no quest, wallet, inventory, merit, or
  claim state changes

#### Scenario: Guild staff 回報 with a quest id turns the quest in
- **WHEN** the player talks to the guild staff with `回報 <quest_id>` naming a
  reportable quest
- **THEN** the staff turns the quest in through `turn_in_quest`, paying the
  exact reward once and answering with the same success or rejection prose as
  `guild turnin`

#### Scenario: Guild staff 回報 without a reportable quest says so
- **WHEN** a registered player with no completed-and-unclaimed quests talks to
  the guild staff with the keyword `回報`
- **THEN** the staff answers that there is nothing to report and no state
  changes

#### Scenario: Unregistered player asking 回報 gets guidance, no state change
- **WHEN** a player without a guild registration talks to the guild staff with
  the keyword `回報`
- **THEN** the staff answers with the authored register-first guidance and no
  quest, wallet, inventory, merit, or claim state changes

#### Scenario: 回報 on a non-guild host stays a plain unknown keyword
- **WHEN** the player talks to any dialogue host other than the `guild_staff`
  host with the keyword `回報`
- **THEN** the host gives the no-understanding line and no state changes

#### Scenario: A schedule-blocked host does not answer and writes nothing
- **WHEN** the player talks to a scripted dialogue host whose schedule state blocks `talk`
- **THEN** the player receives the stable schedule rejection line, and no affinity
  or turn-in state changes
