## MODIFIED Requirements

### Requirement: Examination combat is a simulated lethal battle with full restoration around it
The pre-exam description SHALL state that the examination is a 「模擬戰」 (simulated battle) and that
both sides are restored to full HP/MP/SP before and after. Guild-exam combat SHALL use the normal
ActionResolver, initiative, modifiers, and round scheduler with ordinary lethal semantics: the examiner
follows the normal combat flow until one side's HP reaches 0. No session-wide nonlethal floor SHALL be
applied. Before the exam starts and after it settles, the candidate's and the examiner's HP, MP, and SP
SHALL be restored to full, regardless of outcome. As a simulation, the fight SHALL NOT emit ordinary
kill rewards: no kill XP/loot, no DEFEAT quest progress, and no protected-entity failure. MP/SP costs and
ordinary upkeep SHALL remain committed during the battle.

#### Scenario: Examiner defeat passes the exam

- **WHEN** the candidate reduces the examiner's HP to 0
- **THEN** the exam settles as PASS, the opponent is deleted, and both the candidate and examiner are restored to full HP/MP/SP

#### Scenario: Candidate defeat fails the exam but causes no real injury

- **WHEN** the examiner reduces the candidate's HP to 0
- **THEN** the exam settles as FAIL with no rank change, and the candidate is restored to full HP/MP/SP

#### Scenario: Both sides start the exam at full HP/MP/SP

- **WHEN** a guild examination begins while either participant is wounded or spent MP/SP
- **THEN** both the candidate and the examiner are at full HP, full MP, and full SP before the first round

#### Scenario: Exam combat grants no kill rewards

- **WHEN** a lethal exam round defeats the examiner
- **THEN** no kill XP/loot, DEFEAT quest progress, or protected-entity failure is granted — the battle is a simulation

#### Scenario: Ordinary combat semantics are reused unmodified

- **WHEN** exam rounds resolve
- **THEN** the same ActionResolver, initiative, modifiers, upkeep, and HP-to-zero defeat logic as ordinary combat apply, with no nonlethal policy
