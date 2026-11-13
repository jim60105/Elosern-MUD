# Spec Delta

## Purpose

Defines how a set of edit commands changes a dream proposal: which commands and fields exist, when an edit set is invalid, how fields are normalized and bounded, and how the resulting change report is computed.

## ADDED Requirements

### Requirement: Edit commands apply in order and all or nothing

An edit set SHALL be applied in order to a copy of the proposal, each proposal field being treated as text with one list item or requirement row per line. The commands SHALL be `str_replace`, `insert` and `create` over the seven fields summary, themes, atmosphere, participants, emphasis, exclusions and requirements. When any edit is invalid the whole set SHALL fail with one error naming a stable code and the failing edit's position, and the input proposal SHALL stay unchanged.

#### Scenario: Each command succeeds
- **WHEN** a set replaces one unique substring, inserts a line after a given line and overwrites a whole field
- **THEN** the returned proposal reflects all three edits in order and the input proposal is unchanged

#### Scenario: Later edits see earlier ones
- **WHEN** the second edit's search text exists only because of the first edit
- **THEN** the set succeeds

#### Scenario: Search text does not match exactly once
- **WHEN** a `str_replace` search text occurs zero times or more than once in its field
- **THEN** the set fails with a distinct code for each case and no edit is kept

#### Scenario: Unknown command, field or malformed edit
- **WHEN** an edit names an unknown command, an unknown field, a missing or extra parameter, or an insert position outside the field's lines
- **THEN** the set fails with the matching code and no edit is kept

#### Scenario: Failure after a valid edit rolls back
- **WHEN** the first edit is valid and the second is invalid
- **THEN** the error names the second edit and the input proposal is unchanged

#### Scenario: Empty edit set
- **WHEN** the edit set is empty
- **THEN** the result equals the input proposal

### Requirement: Edited fields are normalized and bounded

After every edit the edited field SHALL be normalized: list items and requirement rows are trimmed, blank lines dropped and duplicates removed keeping the first; the summary is trimmed. A requirement row SHALL be one line of a known kind, a colon (either width) and non-empty text, stored and rendered in the canonical half-width form. A result outside any direction bound — summary length, item count, item length, requirement count or row length — SHALL make the edit set invalid.

#### Scenario: List normalization
- **WHEN** a list field is overwritten with padded lines, a blank line and a repeated item
- **THEN** the stored list holds each distinct trimmed item once in first-seen order

#### Scenario: Requirement rows parse and render
- **WHEN** a requirements field is overwritten with lines of the form kind, colon, text
- **THEN** each row is stored as its kind and trimmed text and the field renders back one canonical line per row

#### Scenario: Full-width colon
- **WHEN** a requirements line separates its kind and text with a full-width colon
- **THEN** the row is stored with the same kind and trimmed text as the half-width form and renders with the canonical half-width separator

#### Scenario: Malformed requirement line
- **WHEN** a requirements line has no colon, an unknown kind or empty text
- **THEN** the edit set is invalid

#### Scenario: Bounds
- **WHEN** an edit would make the summary, a list, a list item, the requirement set or a requirement text exceed its bound
- **THEN** the edit set is invalid with the code of the exceeded bound, and a value exactly at the bound is accepted

#### Scenario: Bounds match the direction store
- **WHEN** the editing bounds and requirement kinds are compared with those the direction store validates
- **THEN** they are equal

### Requirement: Aggregate byte budgets bound the proposal and its change report

The canonical JSON of a stored proposal and of a computed change report SHALL each stay within a fixed byte budget, so that the published panel and the saved draft both fit the limits of the surfaces that carry them.

#### Scenario: Aggregate size
- **WHEN** the proposal or the change report of an edit set would exceed its aggregate byte budget while every field stays inside its own bound
- **THEN** the edit set is invalid with the code of the exceeded budget and no edit is kept

#### Scenario: A result inside both budgets is accepted
- **WHEN** a proposal and its change report both sit at or below their byte budgets
- **THEN** the edit set succeeds

### Requirement: The change report names what an edit set changed

Comparing a proposal before and after SHALL yield a change report: for each of the five list fields the items added and the items removed, for requirements the rows added and removed, and for the summary whether it first took shape, was changed or was untouched. Removed items SHALL be named explicitly.

#### Scenario: Added and removed list items
- **WHEN** one item is replaced by another in a list field
- **THEN** the report lists the new item as added and the old item as removed for that field and nothing for the other fields

#### Scenario: Summary first takes shape, then changes
- **WHEN** an empty summary receives text, and later that text is altered
- **THEN** the first report marks the summary as formed and the second as changed

#### Scenario: Nothing changed
- **WHEN** before and after are equal
- **THEN** every list reports no additions and no removals and the summary is reported as untouched

#### Scenario: Requirement rows compare by kind and text
- **WHEN** a requirement row's text changes
- **THEN** the report lists the old row as removed and the new row as added
