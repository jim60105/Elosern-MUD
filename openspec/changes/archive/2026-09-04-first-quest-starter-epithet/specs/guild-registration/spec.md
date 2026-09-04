# guild-registration — delta

## MODIFIED Requirements

### Requirement: Guild registration grants the paired starter titles atomically
The registration transaction SHALL additionally grant the F-rank fixed title
(「F級冒險者」) into `db.title_collection`,
auto-equipping the empty fixed slot, inside the same all-or-nothing commit that
grants F rank — no planner, no LLM. The starter epithet (「南門新客」) SHALL NOT
be granted at registration; it is granted by the first guild reward claim
(quest-reward-settlement). Re-registration SHALL leave title state
byte-identical (the fixed-key dedupe rule makes it a no-op), and a
rejected registration SHALL grant no title.

#### Scenario: Registration writes rank and the fixed title in one commit
- **WHEN** a fresh member completes guild registration
- **THEN** F rank, the fixed entry, and the auto-equipped fixed slot are all present at that single commit, with no epithet entry in `title_collection`

#### Scenario: Repeated registration is inert on titles
- **WHEN** an already-registered member registers again
- **THEN** `title_collection` and `title_equipped` are unchanged
