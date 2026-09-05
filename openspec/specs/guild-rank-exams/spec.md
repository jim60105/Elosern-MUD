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
API. It SHALL validate examiner authority through the shared `world/rules/service_gate.py::
service_available` resolver applied to the examiner's `GuildExaminer` component — a `remote`
verdict (actor and examiner not co-located) and an `off_anchor` verdict (place-bound examiner
away from its anchor room) are both refused before any eligibility check, and a
`malformed_binding` verdict fails closed — SHALL require a matching GuildExaminer component,
eligibility, and no active combat or examination. A successfully started examination SHALL additionally grant +1 affinity (`guild`
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

#### Scenario: An off-anchor examiner cannot open examinations
- **WHEN** a place-bound examiner is not in its anchor room and a co-located eligible actor
  requests the next-rank examination
- **THEN** the start is refused with the gate's fixed off-anchor message and no exam record,
  opponent, combat session, merit, affinity, or rank change is created

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
kill rewards: no kill loot, no DEFEAT quest progress, and no protected-entity failure; and no growth of any kind: every examination resolution carries the `simulated` event-context marker, so lineage practice accrual is skipped for every skill used. MP/SP costs and
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
- **THEN** no kill loot, DEFEAT quest progress, or protected-entity failure is granted — the battle is a simulation

#### Scenario: Ordinary combat semantics are reused unmodified
- **WHEN** exam rounds resolve
- **THEN** the same ActionResolver, initiative, modifiers, upkeep, and HP-to-zero defeat logic as ordinary combat apply, with no nonlethal policy

### Requirement: Exam settlement is idempotent and promotes only a passing candidate
Every attempt SHALL use ID `<character-id>:<target-rank>:<attempt-number>`. Opponent knockout SHALL
atomically record PASS and advance rank one step. Candidate knockout, flee, invalid recovery, or round
cap SHALL record FAIL without rank or merit change. Settlement SHALL delete the temporary opponent,
close combat state, and be idempotent by exam ID.
A PASS settlement SHALL additionally grant the new rank's paired fixed title into
`db.title_collection` within the same promotion transaction (auto-equipping the fixed slot only
when empty); a rolled-back promotion revokes the entry with the transaction.

#### Scenario: Passing promotes exactly one rank
- **WHEN** an eligible F candidate knocks out the E examiner
- **THEN** rank becomes E, merit is unchanged, and the exam records PASS once

#### Scenario: Promotion carries its title
- **WHEN** an eligible F candidate's PASS settlement commits
- **THEN** the E-rank fixed title is banked in that same transaction

#### Scenario: A rolled-back promotion revokes its title
- **WHEN** a promotion transaction fails after staging the rank-up title
- **THEN** the title collection is byte-identical to its pre-settlement value

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
`start_guild_exam` SHALL spawn each temporary opponent under the rank's authored examiner name,
falling back to the authored name suffixed with the spawn's primary key (`<authored-name>-<pk>`)
only when another entity (including any player character) already holds that key, so a battlefield
roster or skip-safety registry keyed on the entity key can never see two participants under one
key while the authored name is used whenever it is free.

#### Scenario: A free authored name is used verbatim
- **WHEN** `start_guild_exam` spawns an opponent and no other entity holds the rank's authored
  examiner name
- **THEN** the opponent's key is exactly the authored examiner name

#### Scenario: A taken authored name gains a unique suffix
- **WHEN** a player character is legally named the rank's authored examiner name and requests that
  examination
- **THEN** the spawned opponent key differs (authored name with its `-<pk>` suffix) and the exam
  starts normally

#### Scenario: Concurrent same-rank exams never share a key
- **WHEN** two examinations of one rank spawn opponents while the authored name is occupied
- **THEN** each opponent key includes its own primary-key component and the two keys are never
  identical
