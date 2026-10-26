# Spec Delta

## MODIFIED Requirements

### Requirement: start_guild_exam is the sole trigger and validates authority itself
`start_guild_exam(actor, examiner, target_rank, requested_by=...)` SHALL be the only mutation-capable
examination-start API. It SHALL validate the co-located `GuildExamReception` counter through the shared
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
- **WHEN** the place-bound examination-reception counter is away from its service anchor
- **THEN** service_available refuses the start before resources, affinity or records change

#### Scenario: Gate verdicts refuse before eligibility
- **WHEN** the gate returns a `remote` verdict (actor and reception counter not co-located) or an
  `off_anchor` verdict (place-bound reception counter away from its anchor room)
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
