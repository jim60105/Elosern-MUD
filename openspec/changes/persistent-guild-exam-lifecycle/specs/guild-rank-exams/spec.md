## MODIFIED Requirements

### Requirement: start_guild_exam is the sole trigger and validates authority itself
start_guild_exam(actor, examiner, target_rank, requested_by=...) SHALL be the only mutation-capable exam start API. It SHALL validate selected persistent human host qualification/identity for registered branch/next rank, co-location and shared service_available, true cumulative merit and no active battle/exam for either participant. requested_by SHALL be audit metadata only. Existing +1 guild-source affinity SHALL commit atomically with kit/restriction/record/session and grant nothing on rejection.

#### Scenario: Command trigger starts an eligible exam
- **WHEN** an eligible local candidate requests its qualified persistent host
- **THEN** one attempt/session starts with that same host and affinity +1

#### Scenario: Busy present host
- **WHEN** the host service state is blocked
- **THEN** start rejects before resources or affinity change

#### Scenario: Duplicate active exam is rejected
- **WHEN** actor or host is already in battle or wrong qualification
- **THEN** no second attempt or session starts

#### Scenario: Future intent has no extra authority
- **WHEN** an npc_intent request reaches start with insufficient merit
- **THEN** start rejects identically with no affinity or exam mutation

#### Scenario: An off-anchor examiner cannot open examinations
- **WHEN** a qualified place-bound examiner is away from its service anchor
- **THEN** service_available refuses the start before resources, affinity or records change

### Requirement: Examination start is all-or-nothing across opponent, record, and session
The opponent SHALL be the existing persistent qualified host. Preflight SHALL validate profile, usable permitted lineage, equipment and accessory slots before mutation. Start SHALL snapshot normal outfit and exam-owned state, then atomically activate kit/restriction, restore applicable full pools and publish exam/session/affinity. Failure SHALL restore persistent attributes, inventory mirrors, ORM and handler caches and skip-safety registration without deleting the host.
Start SHALL activate the predecessor schedule hold in the same transaction. Every terminal/recovery closure SHALL restore normal host state before invoking recoverable held-occurrence release; valid resume SHALL retain hold. No schedule departure/state change SHALL interrupt an active exam and no release SHALL advance world time a second time.

#### Scenario: Spawn succeeds but session persistence fails
- **WHEN** session persistence fails after kit/restriction installation
- **THEN** all storage/caches/resources/affinity equal pre-start snapshots and host dbref survives

#### Scenario: Exam-record creation fails before spawn
- **WHEN** kit or prerequisite validation fails
- **THEN** no outfit, restriction, attempt or session mutation occurs

### Requirement: Exam opponents use validated true-stat rank profiles
Each E-S target SHALL map to a validated kit/restriction policy and a branch-qualified persistent human host, preserving literal normal bases and learned lineage/proficiency. E-B SHALL lower qualified B-or-higher hosts using guild-exam-restrictions; A/S SHALL use their respective references. Profiles SHALL never amplify a weak host or derive values from candidate/disguise. No temporary opponent factory SHALL remain.

#### Scenario: Repeated E-B host
- **WHEN** the same persistent senior hosts repeated E-B exams
- **THEN** normal base/learned records and identity remain unchanged between attempts

#### Scenario: Disguised candidate receives the same opponent
- **WHEN** candidate changes displayed traits
- **THEN** selected host and restriction profile stay unchanged

#### Scenario: Every rank profile stays inside its lore band
- **WHEN** all target policies and normal qualified hosts validate
- **THEN** normal human bases retain unchanged racial/static bounds and target restrictions satisfy the approved effective references without requiring those effective values to fit a bare-human tier band

### Requirement: Examination combat is a simulated lethal battle with full restoration around it
Pre-exam description SHALL state simulated battle and full HP/MP/SP restoration before/after. Ordinary ActionResolver/initiative/modifiers/costs/upkeep/HP-zero semantics SHALL apply, with no HP1 floor. Both enter at full applicable pools. Every action/round SHALL carry simulation markers suppressing loot, DEFEAT/protected-entity failure and skill growth. Every terminal outcome SHALL restore both to full normal pools and preserve the persistent host.

#### Scenario: Zero HP
- **WHEN** either participant reaches zero HP
- **THEN** pass/fail settles under normal defeat semantics with no death reward/growth and full normal pools restored

#### Scenario: Both sides start the exam at full HP/MP/SP
- **WHEN** participants begin wounded or spent
- **THEN** full applicable pools precede the first action

#### Scenario: Costs and upkeep
- **WHEN** a permitted skill resolves
- **THEN** ordinary costs/upkeep commit during battle without skill practice

#### Scenario: Examiner defeat passes the exam
- **WHEN** the persistent examiner reaches zero HP
- **THEN** PASS settles and both full normal pools/outfit/capabilities are restored without deleting the host

#### Scenario: Candidate defeat fails the exam but causes no real injury
- **WHEN** the candidate reaches zero HP
- **THEN** FAIL leaves rank/merit unchanged and restores both participants to full normal pools

#### Scenario: Exam combat grants no kill rewards
- **WHEN** an exam participant is defeated under simulation markers
- **THEN** no loot, DEFEAT quest progress, protected-entity failure or skill growth occurs

#### Scenario: Ordinary combat semantics are reused unmodified
- **WHEN** examination rounds resolve
- **THEN** ordinary initiative/modifiers/costs/upkeep and HP-to-zero logic apply without an HP1 floor

### Requirement: Exam settlement is idempotent and promotes only a passing candidate
Attempt identity SHALL remain <character-id>:<target-rank>:<attempt-number>. PASS SHALL atomically advance one rank and bank paired title (autoequip only empty slot), with merit unchanged. Fail/flee/forfeit/invalid recovery/round cap SHALL not promote. Settlement SHALL close once, remove exam-owned effects/restriction and restore host normal outfit and both full normal pools without deleting the host. Rollback SHALL restore storage/caches for retry. Cold recovery SHALL resume coherent persisted identity/kit/restriction/session or close invalid simulation and restore host; deletion SHALL NOT repair it.

#### Scenario: Replayed settlement cannot promote twice
- **WHEN** terminal settlement repeats
- **THEN** rank/title/restoration and attempt state settle once

#### Scenario: A rolled-back promotion revokes its title
- **WHEN** terminal persistence fails after staging changes
- **THEN** pre-settlement surfaces/caches are restored and retry settles exactly once

#### Scenario: Passing promotes exactly one rank
- **WHEN** an eligible F member defeats the persistent E host
- **THEN** PASS advances rank to E once without spending merit

#### Scenario: Promotion carries its title
- **WHEN** PASS commits
- **THEN** the new paired title is banked atomically, autoequipping only an empty fixed slot

#### Scenario: Failed attempt can be retried
- **WHEN** a failed exam closes and candidate remains eligible
- **THEN** the next attempt gets the next deterministic number with the same qualified host

#### Scenario: Corrupt reload
- **WHEN** exam identity/session/restriction mismatch after cold start
- **THEN** invalid simulation closes and host normal state/dbref is retained

#### Scenario: Valid resume
- **WHEN** coherent active simulation reloads
- **THEN** same host, restriction and session continue

### Requirement: Guild exam opponents carry canonical age
Qualified persistent hosts SHALL carry canonical authored age/apparent_age integers in 0..10000 before any exam start. Start SHALL validate existing identity without respawning/reinitializing age or card. Invalid age SHALL reject without attempt/resource/affinity change.

#### Scenario: Exam opponent has canonical age
- **WHEN** a qualified host enters a second examination
- **THEN** canonical age pair remains unchanged

#### Scenario: Invalid examiner age leaves no partial examination
- **WHEN** stored host age is invalid
- **THEN** start rejects without partial mutation

### Requirement: Exam opponents use collision-free unique display keys
Persistent host creation SHALL use authored name when unoccupied or authored-name plus its persistent primary-key suffix when occupied, through the shared live occupancy check. Later participant-key collisions SHALL reject start with participant_name_collision before mutation, without host renaming/cloning. Persistent dbrefs SHALL determine qualification/participant identity and repeated exams SHALL retain the same normal key/persona. No display-name search or first component match SHALL select a host. Host SHALL NOT join simultaneous exams.

#### Scenario: Player name collision
- **WHEN** a player later acquires the existing persistent host's exact object key
- **THEN** preflight rejects participant_name_collision with no exam mutation, selecting no different host and preserving the existing host key/dbref/persona

#### Scenario: Same host contention
- **WHEN** another actor requests a busy host
- **THEN** request/start rejects without concurrent session

#### Scenario: A free authored name is used verbatim
- **WHEN** normal persistent host assembly finds its authored key free
- **THEN** that key is assigned once and retained across exams

#### Scenario: A taken authored name gains a unique suffix
- **WHEN** normal persistent host creation finds its authored key occupied
- **THEN** the host receives its own persistent primary-key suffix once and later exams do not rename it

#### Scenario: Concurrent same-rank exams never share a key
- **WHEN** another candidate requests a host already in an active exam
- **THEN** start rejects, preventing simultaneous reuse of the same participant key/dbref

### Requirement: Exam opponents receive their rank examiner's card at spawn
Persistent host assembly SHALL initialize each person once from its authored profile with canonical provenance, age and bounded card. Examination start SHALL reuse existing card/persona/identity without creating or resetting it. Rank-owned card spawn contracts and orphaned F/E/D/C examiner profiles SHALL be removed without aliases.

#### Scenario: An opponent carries its examiner's card
- **WHEN** a host has an edited persona and starts/settles two exams
- **THEN** the same edited persona/provenance remains with no reset or copy from rank profile

#### Scenario: A persona failure aborts the start
- **WHEN** host assembly or identity preflight finds an invalid persona
- **THEN** start rejects before examination mutation and never deletes the existing host

#### Scenario: Spawns do not share edits
- **WHEN** one persistent person's card is edited and another person's exam starts
- **THEN** each retains its own independent card and no rank factory copies or resets either

