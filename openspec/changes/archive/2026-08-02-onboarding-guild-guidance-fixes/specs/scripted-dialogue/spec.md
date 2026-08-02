## ADDED Requirements

### Requirement: Scripted dialogue hosts answer authored talk lines
An NPC carrying a `ScriptedDialogue` component SHALL answer known keywords with
the authored response and unknown keywords with the no-understanding line,
without causing state change. `talk <npc>` without a keyword SHALL present the
host's authored greeting when one is configured, and the no-response line when
it is not. An NPC without any dialogue component SHALL keep yielding the
no-response line. An `OnboardingGuide` host (the South Gate guard) SHALL answer
through the same authored tables but is explicitly exempt from the no-state
guarantee: a known guard keyword updates `guide_progress` exactly as the
existing onboarding rules define, while an unknown keyword SHALL NOT write.

#### Scenario: Guild staff answers a known keyword
- **WHEN** the player talks to the guild master with a keyword such as 公會 or 任務
- **THEN** the guild master answers with the authored response for that keyword
  and no state changes

#### Scenario: No-keyword talk presents the host's greeting
- **WHEN** the player runs `talk <guild-master>` without a keyword
- **THEN** the guild master presents its authored greeting teaching the guild
  commands, and no state changes

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

#### Scenario: Guard keyword tracking stays an onboarding exception
- **WHEN** the player talks to the South Gate guard with a known guard keyword
- **THEN** the guard answers from the authored table and records the keyword on
  `guide_progress`; an unknown guard keyword records nothing

### Requirement: Dialogue tables are immutable, keyed, and registry-backed
The dialogue-table registry SHALL be keyed by `dialogue_key` and SHALL hold only
frozen `DialogueDefinition` values composed of an optional `greeting` and a
tuple of frozen `KeywordResponse` values. The registry SHALL be read-only at
runtime. A `dialogue_key` with no registered table SHALL resolve to the
no-understanding line for keywords and to no greeting. The `guild_staff`
definition SHALL teach the documented guild commands (`guild register`,
`guild list`, `guild accept`, `guild log`, `guild show`, `guild turnin`,
`guild abandon`, `guild merit`) in its greeting or keyword responses.

#### Scenario: guild_staff definition registers and answers command guidance
- **WHEN** the `guild_staff` dialogue definition is registered and queried
- **THEN** its greeting and keyword responses name the guild commands a player
  can use at the guild hall

#### Scenario: A missing table yields the no-understanding line
- **WHEN** a dialogue lookup references a `dialogue_key` absent from the registry
- **THEN** the no-understanding line is returned for keywords and no greeting is
  resolved, and nothing is written
