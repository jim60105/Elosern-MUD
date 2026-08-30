## ADDED Requirements

### Requirement: Guild registration grants the paired starter titles atomically
The registration transaction SHALL additionally grant the F-rank fixed title
(「F級冒險者」) and the starter epithet (「南門新客」, `origin_quote` from
`world/lore/titles.py`'s `STARTER_EPITHET`) into `db.title_collection`,
auto-equipping both empty slots, inside the same all-or-nothing commit that
grants F rank — no planner, no LLM. Re-registration SHALL leave title state
byte-identical (the fixed-key and display dedupe rules make it a no-op), and a
rejected registration SHALL grant no title.

#### Scenario: Registration writes rank and titles in one commit
- **WHEN** a fresh member completes guild registration
- **THEN** F rank, the fixed entry, the epithet entry, and both auto-equipped slots are all present at that single commit

#### Scenario: Repeated registration is inert on titles
- **WHEN** an already-registered member registers again
- **THEN** `title_collection` and `title_equipped` are unchanged
