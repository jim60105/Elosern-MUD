## MODIFIED Requirements

### Requirement: start_guild_exam is the sole trigger and validates authority itself
`start_guild_exam(actor, examiner, target_rank, requested_by=...)` SHALL be the only mutation-capable
examination-start API. It SHALL validate the co-located `GuildExaminer` counter through the shared
`service_available` resolver, the selected persistent host's qualification and identity for the
registered branch's next rank, true cumulative merit, and no active battle or exam for either
participant. `requested_by` SHALL be audit metadata and SHALL NOT bypass validation.

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

#### Scenario: Gate verdicts refuse before eligibility
- **WHEN** the gate returns a `remote` verdict (actor and examiner not co-located) or an
  `off_anchor` verdict (place-bound examiner away from its anchor room)
- **THEN** both are refused before any eligibility check, and a `malformed_binding` verdict fails
  closed

#### Scenario: A started exam grants +1 affinity atomically
- **WHEN** an examination starts successfully
- **THEN** it additionally grants +1 affinity (`guild` source) with the examiner through the
  sole-writer affinity API (`world/rules/affinity.py`), applied inside the same atomic block that
  creates the exam record and combat session (the persistent host is resolved and preflighted
  before any mutation)

#### Scenario: The affinity record joins the restore surfaces
- **WHEN** an exam start fails after the affinity grant would have been staged
- **THEN** the examiner's affinity record, joined to the existing exam snapshot/restore surfaces,
  is restored, and a rejected start grants nothing

### Requirement: Examination start is all-or-nothing across opponent, record, and session
The opponent SHALL be the existing persistent qualified host. Start SHALL preflight the profile,
permitted lineage and equipment slots before mutation, then atomically snapshot the normal outfit,
activate the kit, restriction and schedule hold, restore full pools, and publish the exam record,
session and affinity. Any failure SHALL restore persistent attributes, inventory mirrors, ORM and
handler caches and skip-safety registration without deleting the host.

#### Scenario: Spawn succeeds but session persistence fails
- **WHEN** session persistence fails after kit/restriction installation
- **THEN** all storage/caches/resources/affinity equal pre-start snapshots and host dbref survives

#### Scenario: Exam-record creation fails before spawn
- **WHEN** kit or prerequisite validation fails
- **THEN** no outfit, restriction, attempt or session mutation occurs

#### Scenario: Closure restores the host before releasing the schedule hold
- **WHEN** a terminal settlement or recovery closes an examination
- **THEN** the host's normal state is restored before the held occurrence is released, the release
  never advances world time a second time, and a valid resume keeps the hold

#### Scenario: Schedule departures never interrupt an active exam
- **WHEN** a scheduled departure falls due while the host's examination is active
- **THEN** the host stays in the battle and the departure is replayed once after the hold releases

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

#### Scenario: Both sides are restored to full regardless of outcome
- **WHEN** an examination begins and later settles, win or lose
- **THEN** the candidate's and the examiner's HP, MP, and SP are restored to full before the exam
  starts and after it settles, regardless of outcome

#### Scenario: The simulation emits no ordinary kill rewards
- **WHEN** an examination fight ends lethally
- **THEN** it emits no ordinary kill rewards — no kill loot, no DEFEAT quest progress, and no
  protected-entity failure

#### Scenario: The simulated marker skips all growth
- **WHEN** an examination resolves
- **THEN** it carries the `simulated` event-context marker, so lineage practice accrual is skipped
  for every skill used — no growth of any kind

#### Scenario: Costs and upkeep still commit during the exam
- **WHEN** exam rounds resolve
- **THEN** MP/SP costs and ordinary upkeep remain committed during the battle

### Requirement: Exam settlement is idempotent and promotes only a passing candidate
Attempt identity SHALL remain `<character-id>:<target-rank>:<attempt-number>`. PASS SHALL atomically
advance one rank and bank the paired title with merit unchanged; fail, flee, forfeit, invalid
recovery and round cap SHALL NOT promote. Settlement SHALL close once, remove exam-owned effects and
the restriction, and restore the host's normal outfit and both full pools without deleting the host.

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
- **THEN** invalid simulation closes as FAIL and host normal state/dbref is retained; deletion never
  repairs recovery

#### Scenario: Valid resume
- **WHEN** coherent active simulation reloads
- **THEN** same host, restriction and session continue

#### Scenario: A PASS grants the rank's paired fixed title
- **WHEN** a PASS settlement promotes a candidate
- **THEN** the new rank's paired fixed title is granted into `db.title_collection` within the same
  promotion transaction, auto-equipping the fixed slot only when empty

### Requirement: Guild exam opponents carry canonical age
Qualified persistent hosts SHALL carry canonical authored age/apparent_age integers in 0..10000 before any exam start. Start SHALL validate existing identity without respawning/reinitializing age or card. Invalid age SHALL reject without attempt/resource/affinity change.

#### Scenario: Exam opponent has canonical age
- **WHEN** a qualified host enters a second examination
- **THEN** canonical age pair remains unchanged

#### Scenario: Invalid examiner age leaves no partial examination
- **WHEN** stored host age is invalid
- **THEN** start rejects without partial mutation

### Requirement: Exam opponents use collision-free unique display keys
Persistent host creation SHALL use the authored name when free, or the authored name suffixed with
its persistent primary key when occupied. A later participant-key collision SHALL reject start with
`participant_name_collision` before mutation, without renaming or cloning the host. Persistent
dbrefs SHALL determine qualification and participant identity; no display-name search SHALL select
a host, and a host SHALL NOT join simultaneous exams.

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

#### Scenario: A persona failure deletes the partial opponent
- **WHEN** an examination start fails after the kit or restriction was staged
- **THEN** the whole start rolls back, no partial opponent exists to delete, and the persistent host survives with its existing card, persona and provenance unchanged

#### Scenario: Each spawn gets its own card instance
- **WHEN** different persistent hosts examine repeatedly across ranks
- **THEN** each host keeps its own independently editable card instance from assembly, and no examination spawns, copies or resets a card

