## ADDED Requirements

### Requirement: Guild branch master and rank examiners carry individual authored profiles and rewritten dialogue
Each guild host owned by the `altoria_guild` inventory slice SHALL name, through its place record, an authored NPC profile whose key equals the host's service identity, whose card satisfies the compact card contract, and which authors a misunderstanding reply in that host's voice and no profile greeting. Every guild rank SHALL name an examiner profile key that resolves to a profile with a complete card and no voice lines, and a missing or unresolved key SHALL fail load naming the rank. Each corresponding dialogue table SHALL keep its keyword identifiers and its greeting, and every greeting and keyword response SHALL be newly authored against the host's card. Every greeting, response and voice line SHALL be spoken in character and SHALL NOT name a command, a game mechanic, or an interface element. Rewritten dialogue SHALL keep every service semantic its settlement and dialogue specifications require and SHALL NOT state fixed prices, stock counts, or availability that live service data owns. Tests SHALL NOT pin the authored prose: rewording a line SHALL NOT break any test; prose quality, voice distinctness and completeness of the rewrite are established by the change's recorded editorial review.

#### Scenario: Every owned host references its own valid profile
- **WHEN** the shipped place registry is validated against the profile registry
- **THEN** each owned host's profile key resolves to a registered profile whose card validates

#### Scenario: Every rank names a resolvable examiner profile
- **WHEN** the guild rank registry is validated, including a synthetic rank naming an unregistered examiner profile key
- **THEN** every shipped rank's key resolves to a profile with no voice lines, and the synthetic rank fails load naming the rank and the field

#### Scenario: Service semantics are preserved
- **WHEN** the existing settlement, guild, and scripted-dialogue behavior tests run against the rewritten table
- **THEN** they pass without weakening any behavior assertion

#### Scenario: Rewording breaks no test
- **WHEN** any owned greeting, keyword response, or voice line is reworded while staying in character
- **THEN** no test fails, because no test pins the authored prose
