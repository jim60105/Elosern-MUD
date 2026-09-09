## MODIFIED Requirements

### Requirement: Monster subjects resolve through the chain without the binding steps
The chain SHALL run steps 1 through 3 — the equipment snapshot, the binding candidates, and the
most-specific-mask selection — only for a subject kind whose capability declaration supports
bindings. A kind that does not support them, which the monster portrait kind does not, SHALL resolve
by skipping those steps: the default card, then the classic asset record, then the fallback seam, then
the placeholder. No equipment snapshot SHALL be computed for such a subject and no card of such a
subject SHALL be selected by a binding. The skip SHALL be decided by reading the declaration, never by
comparing the subject kind inline.

#### Scenario: A monster resolves its single card
- **WHEN** a monster subject holds its one card
- **THEN** that card is resolved with no equipment read

#### Scenario: A monster with no card falls through unchanged
- **WHEN** a monster subject holds no card and its classic asset record is `done`
- **THEN** the classic asset is resolved exactly as it is today

#### Scenario: The binding steps follow the declaration
- **WHEN** display resolution runs for a kind whose declaration does not support bindings
- **THEN** the binding steps are skipped and no equipment snapshot is computed, with no edit to the resolution module
