# guild-rank-exams Specification

## Purpose

Define deterministic guild-rank examinations and nonlethal promotion combat.

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

### Requirement: Examination combat is nonlethal and grants no ordinary defeat rewards
Guild-exam combat SHALL use the normal ActionResolver, initiative, modifiers, and round scheduler with an
explicit nonlethal policy. A lethal crossing SHALL floor HP at 1, record knockout, and SHALL NOT emit
ordinary `target_defeated`, grant kill XP/loot, advance DEFEAT quests, or trigger protected-entity
failure. The policy SHALL be applied during projected damage before EventLog construction and event-effect
planners. MP/SP costs and ordinary upkeep SHALL remain committed.

#### Scenario: Examiner knockout is not a quest kill
- **WHEN** the candidate deals examination damage that would reduce the opponent below zero
- **THEN** the opponent remains at 1 HP, is marked knocked out, and no kill-credit consumer fires

#### Scenario: Candidate knockout is nonfatal but loses
- **WHEN** the examiner would reduce the candidate below zero
- **THEN** the candidate remains at 1 HP, is marked knocked out, and the exam settles as failed

#### Scenario: Ordinary lethal combat remains unchanged
- **WHEN** the same damage resolves in a hostile context without the nonlethal policy
- **THEN** HP may reach zero and ordinary defeat, XP, and quest planners retain their existing behavior

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
