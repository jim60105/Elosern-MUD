# guild-rank-exams Specification

## Purpose

Define deterministic guild-rank examinations and simulated-battle promotion combat.

## Requirements

### Requirement: Rank promotion requires cumulative merit and exactly the next examination
`guild_economy.yaml` SHALL define strictly increasing non-negative merit thresholds for E through S.
An actor SHALL be eligible only when registered, currently at the immediately preceding rank, and true
`guild_merit` meets the requested target's threshold. Merit SHALL not be spent on an attempt or
promotion. Skipping ranks and examining from S SHALL be rejected.

#### Scenario: Threshold alone does not promote
- **WHEN** an F member reaches the E threshold
- **THEN** rank remains F until an E examination is passed

#### Scenario: Below-threshold request is rejected
- **WHEN** an F member below the E threshold requests the E examination
- **THEN** no exam record, opponent, combat session, merit, or rank change is created

#### Scenario: Rank skipping is rejected
- **WHEN** an F member requests a D examination even with enough merit for D
- **THEN** the request is rejected because E is the only valid target

### Requirement: start_guild_exam is the sole trigger and validates authority itself
`start_guild_exam(actor, examiner, target_rank, requested_by=...)` SHALL be the only examination-start
API. It SHALL require co-location, a matching GuildExaminer component, eligibility, and no active combat
or examination. A successfully started examination SHALL additionally grant +1 affinity (`guild`
source) with the examiner through the sole-writer affinity API (`world/rules/affinity.py`), applied
inside the same atomic block that creates the exam record and combat session (the temporary
opponent is pre-spawned before any mutation); the examiner's affinity record SHALL join the
existing exam snapshot/restore surfaces so any failure restores it; a rejected start SHALL grant
nothing. `requested_by` SHALL be audit metadata and SHALL NOT bypass validation.

#### Scenario: Command trigger starts an eligible exam
- **WHEN** local GuildExaminer invokes the API for an eligible next rank with `requested_by="command"`
- **THEN** one deterministic exam record, temporary opponent, and guild-exam combat session are
  created, and the examiner's affinity value rises by 1

#### Scenario: Future intent has no extra authority
- **WHEN** the same request uses `requested_by="npc_intent"` but the actor lacks merit
- **THEN** it is rejected identically to the command request and no affinity is granted

#### Scenario: Duplicate active exam is rejected
- **WHEN** an actor with an active exam requests another
- **THEN** no second opponent, record, or session is created and no affinity is granted

### Requirement: Examination start is all-or-nothing across opponent, record, and session
The exam trigger SHALL preflight all eligibility/profile/spawn inputs, then create the temporary opponent,
exam record, and combat session as one logical operation. If any creation or persistence step fails, it
SHALL restore all caches and delete any opponent already created. No exception path SHALL leave only a
record, opponent, or session.

#### Scenario: Spawn succeeds but session persistence fails
- **WHEN** combat-session persistence is fault-injected after the opponent and exam record are created
- **THEN** the record and session are absent and the temporary opponent is deleted

#### Scenario: Exam-record creation fails before spawn
- **WHEN** exam-record preflight or persistence fails before opponent creation
- **THEN** no opponent or combat session is created

### Requirement: Exam opponents use validated true-stat rank profiles
Each target rank E through S SHALL map to one YAML exam profile with exact true traits and known combat
skills. E/D profiles SHALL fit `human_adventurer`, C/B `human_elite`, A `human_veteran`, and S
`human_swordmaster`. The spawned opponent SHALL be an adult temporary NPC and SHALL never derive stats
from the candidate's displayed or true values.

#### Scenario: Every rank profile stays inside its lore band
- **WHEN** all six target-rank profiles are validated
- **THEN** their physical stats lie inside the required StaticTier bands and all skill keys exist

#### Scenario: Disguised candidate receives the same opponent
- **WHEN** one candidate changes `disguised_stats` between two otherwise identical exam starts
- **THEN** the selected target-rank profile is unchanged

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

### Requirement: Exam settlement is idempotent and promotes only a passing candidate
Every attempt SHALL use ID `<character-id>:<target-rank>:<attempt-number>`. Opponent knockout SHALL
atomically record PASS and advance rank one step. Candidate knockout, flee, invalid recovery, or round
cap SHALL record FAIL without rank or merit change. Settlement SHALL delete the temporary opponent,
close combat state, and be idempotent by exam ID.

#### Scenario: Passing promotes exactly one rank
- **WHEN** an eligible F candidate knocks out the E examiner
- **THEN** rank becomes E, merit is unchanged, and the exam records PASS once

#### Scenario: Failed attempt can be retried
- **WHEN** a failed exam has settled and the candidate remains eligible
- **THEN** a new attempt receives the next deterministic attempt number

#### Scenario: Replayed settlement cannot promote twice
- **WHEN** PASS settlement is invoked again for an already settled exam ID
- **THEN** rank and every exam surface remain unchanged

### Requirement: Guild exam opponents carry adult identity

The system SHALL persist adult `age`/`apparent_age` on every temporary exam
opponent spawned by `start_guild_exam`.

#### Scenario: Exam opponent has adult age
- **WHEN** `guild exam <rank>` spawns `guild-examiner-<rank>`
- **THEN** the opponent has integer `age` and `apparent_age` of at least 18

### Requirement: Exam opponents use collision-free unique display keys
`start_guild_exam` SHALL spawn each temporary opponent with a display key unique to that spawn (e.g.
`guild-examiner-<rank>-<pk>`), so a participant whose display name equals the bare
`guild-examiner-<rank>` pattern can never collide with the opponent in a battlefield roster.

#### Scenario: Same-named player can take the exam
- **WHEN** a player character is legally named `guild-examiner-E` and requests the E examination
- **THEN** the spawned opponent key differs from the player's key and the exam starts normally

#### Scenario: Opponent keys stay deterministic per rank
- **WHEN** two E examinations spawn opponents
- **THEN** each opponent key includes its own unique component (never identical to the other's)
