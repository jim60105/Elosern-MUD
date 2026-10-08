## MODIFIED Requirements

### Requirement: start_guild_exam is the sole trigger and validates authority itself
start_guild_exam(actor, examiner, target_rank, requested_by=...) SHALL be the only mutation-capable exam start API. It SHALL validate selected persistent human host qualification/identity for registered branch/next rank, co-location and shared service_available, true cumulative merit and no active battle/exam for either participant. requested_by SHALL be audit metadata only. Existing +1 guild-source affinity SHALL commit atomically with kit/restriction/record/session and grant nothing on rejection.

#### Scenario: Qualified start
- **WHEN** an eligible local candidate requests its qualified persistent host
- **THEN** one attempt/session starts with that same host and affinity +1

#### Scenario: Busy present host
- **WHEN** the host service state is blocked
- **THEN** start rejects before resources or affinity change

#### Scenario: Duplicate or unauthorized
- **WHEN** actor or host is already in battle or wrong qualification
- **THEN** no second attempt or session starts

### Requirement: Examination start is all-or-nothing across opponent, record, and session
The opponent SHALL be the existing persistent qualified host. Preflight SHALL validate profile, usable permitted lineage, equipment and accessory slots before mutation. Start SHALL snapshot normal outfit and exam-owned state, then atomically activate kit/restriction, restore applicable full pools and publish exam/session/affinity. Failure SHALL restore persistent attributes, inventory mirrors, ORM and handler caches and skip-safety registration without deleting the host.

#### Scenario: Fault after kit replacement
- **WHEN** session persistence fails after kit/restriction installation
- **THEN** all storage/caches/resources/affinity equal pre-start snapshots and host dbref survives

#### Scenario: Invalid loadout
- **WHEN** kit or prerequisite validation fails
- **THEN** no outfit, restriction, attempt or session mutation occurs

### Requirement: Exam opponents use validated true-stat rank profiles
Each E-S target SHALL map to a validated kit/restriction policy and a branch-qualified persistent human host, preserving literal normal bases and learned lineage/proficiency. E-B SHALL lower qualified B-or-higher hosts using guild-exam-restrictions; A/S SHALL use their respective references. Profiles SHALL never amplify a weak host or derive values from candidate/disguise. No temporary opponent factory SHALL remain.

#### Scenario: Repeated E-B host
- **WHEN** the same persistent senior hosts repeated E-B exams
- **THEN** normal base/learned records and identity remain unchanged between attempts

#### Scenario: Disguise
- **WHEN** candidate changes displayed traits
- **THEN** selected host and restriction profile stay unchanged

### Requirement: Examination combat is a simulated lethal battle with full restoration around it
Pre-exam description SHALL state simulated battle and full HP/MP/SP restoration before/after. Ordinary ActionResolver/initiative/modifiers/costs/upkeep/HP-zero semantics SHALL apply, with no HP1 floor. Both enter at full applicable pools. Every action/round SHALL carry simulation markers suppressing loot, DEFEAT/protected-entity failure and skill growth. Every terminal outcome SHALL restore both to full normal pools and preserve the persistent host.

#### Scenario: Zero HP
- **WHEN** either participant reaches zero HP
- **THEN** pass/fail settles under normal defeat semantics with no death reward/growth and full normal pools restored

#### Scenario: Wounded entry
- **WHEN** participants begin wounded or spent
- **THEN** full applicable pools precede the first action

#### Scenario: Costs and upkeep
- **WHEN** a permitted skill resolves
- **THEN** ordinary costs/upkeep commit during battle without skill practice

### Requirement: Exam settlement is idempotent and promotes only a passing candidate
Attempt identity SHALL remain <character-id>:<target-rank>:<attempt-number>. PASS SHALL atomically advance one rank and bank paired title (autoequip only empty slot), with merit unchanged. Fail/flee/forfeit/invalid recovery/round cap SHALL not promote. Settlement SHALL close once, remove exam-owned effects/restriction and restore host normal outfit and both full normal pools without deleting the host. Rollback SHALL restore storage/caches for retry. Cold recovery SHALL resume coherent persisted identity/kit/restriction/session or close invalid simulation and restore host; deletion SHALL NOT repair it.

#### Scenario: Replay PASS
- **WHEN** terminal settlement repeats
- **THEN** rank/title/restoration and attempt state settle once

#### Scenario: Fault title or outfit restoration
- **WHEN** terminal persistence fails after staging changes
- **THEN** pre-settlement surfaces/caches are restored and retry settles exactly once

#### Scenario: Corrupt reload
- **WHEN** exam identity/session/restriction mismatch after cold start
- **THEN** invalid simulation closes and host normal state/dbref is retained

#### Scenario: Valid resume
- **WHEN** coherent active simulation reloads
- **THEN** same host, restriction and session continue

### Requirement: Guild exam opponents carry canonical age
Qualified persistent hosts SHALL carry canonical authored age/apparent_age integers in 0..10000 before any exam start. Start SHALL validate existing identity without respawning/reinitializing age or card. Invalid age SHALL reject without attempt/resource/affinity change.

#### Scenario: Existing age
- **WHEN** a qualified host enters a second examination
- **THEN** canonical age pair remains unchanged

#### Scenario: Invalid age
- **WHEN** stored host age is invalid
- **THEN** start rejects without partial mutation

### Requirement: Exam opponents use collision-free unique display keys
Participant names SHALL be collision-safe through existing NPC identity/roster discipline before combat; persistent dbrefs SHALL determine qualification/participant identity. No display-name search, first component match, temporary per-exam renaming or cloning SHALL select a host. Host may not join simultaneous exams.

#### Scenario: Player name collision
- **WHEN** a player shares authored host display name
- **THEN** roster preflight resolves collision through established discipline without selecting a different host or replacing dbref

#### Scenario: Same host contention
- **WHEN** another actor requests a busy host
- **THEN** request/start rejects without concurrent session

### Requirement: Exam opponents receive their rank examiner's card at spawn
Persistent host assembly SHALL initialize each person once from its authored profile with canonical provenance, age and bounded card. Examination start SHALL reuse existing card/persona/identity without creating or resetting it. Rank-owned card spawn contracts and orphaned F/E/D/C examiner profiles SHALL be removed without aliases.

#### Scenario: Edited normal card
- **WHEN** a host has an edited persona and starts/settles two exams
- **THEN** the same edited persona/provenance remains with no reset or copy from rank profile

