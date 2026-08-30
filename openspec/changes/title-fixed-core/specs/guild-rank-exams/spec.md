## MODIFIED Requirements

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
