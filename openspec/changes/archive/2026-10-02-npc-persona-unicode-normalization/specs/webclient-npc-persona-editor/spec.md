## ADDED Requirements

### Requirement: NPC editor dirty and reconnect comparisons use canonical normalization
NPC editor comparisons SHALL apply the same complete card-and-greeting normalized equality as the server, including the explicit boundary-whitespace set and exact CRLF conversion. Boundary-only changes SHALL remain clean; preserved interior or excluded-character changes SHALL be dirty. Normalization for comparison SHALL NOT destructively rewrite local inputs or discard drafts after rejected/uncertain saves. After transport loss the editor SHALL obtain a fresh read before another commit and SHALL NOT infer a successful prior save merely from local equality. Existing session correlation, expected-version and explicit conflict reload rules SHALL remain in force.

#### Scenario: Boundary-only typing stays clean
- **WHEN** the user adds only enumerated outer whitespace to a card leaf or greeting
- **THEN** the editor remains normalized-clean and does not request dirty-close discard confirmation

#### Scenario: Interior whitespace is a real edit
- **WHEN** the user adds interior U+0085 or boundary U+200B to a previously clean draft
- **THEN** the editor reports dirty state and the normalized save is a real server change

#### Scenario: Reconnect after uncertain boundary-only save
- **WHEN** transport is lost during a boundary-only submission and later reconnects
- **THEN** the editor re-reads authoritative data/version before another save, reconciles normalized equality without claiming unobserved success, and does not create spurious dirty state or duplicate version advances
