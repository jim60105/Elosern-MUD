## MODIFIED Requirements

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
