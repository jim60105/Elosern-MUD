## MODIFIED Requirements

### Requirement: Scripted dialogue hosts answer authored talk lines
An NPC carrying a `ScriptedDialogue` component SHALL answer known keywords with the
authored response and unknown keywords with the no-understanding line,
without causing state change except that a known-keyword answer SHALL grant +1 affinity
(`talk` source) with the host through the sole-writer affinity API (`world/rules/affinity.py`),
applied by the deterministic talk writer in the same transaction as the answer; unknown keywords
and no-keyword paths SHALL NOT write any state.
`talk <npc>` without a keyword SHALL present the host's authored greeting when one is configured,
and the no-response line when it is not. An NPC without any dialogue component SHALL keep yielding
the no-response line. An `OnboardingGuide` host (the South Gate guard) SHALL answer through the
same authored tables, is explicitly exempt from the no-state guarantee (a known guard keyword
updates `guide_progress` exactly as the existing onboarding rules define), and SHALL grant the
same +1 affinity as any other known-keyword answer — with `guide_progress` and the affinity gain
committed in one transaction — while an unknown keyword SHALL NOT write.

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

#### Scenario: Guard keyword tracking and affinity commit together
- **WHEN** the player talks to the South Gate guard with a known guard keyword
- **THEN** the guard answers from the authored table, records the keyword on
  `guide_progress`, and the guard's affinity value rises by 1 in one transaction; an unknown
  guard keyword records nothing and grants no affinity

#### Scenario: A failed guard talk write restores both surfaces
- **WHEN** persistence is fault-injected after `guide_progress` is written and before the
  affinity gain commits
- **THEN** `guide_progress` and the affinity record — and their in-process caches — equal their
  pre-talk values
