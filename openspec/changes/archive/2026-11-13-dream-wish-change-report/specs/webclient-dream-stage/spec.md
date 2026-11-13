# Spec Delta

## ADDED Requirements

### Requirement: The keepsake card reports what the last exchange changed

While conversing, the keepsake card SHALL show a change line built from the server's change report: each changed field named in words with a glyph, list fields with their counts of added and removed items, or a statement that nothing changed. With no report the line SHALL be absent. After a live exchange the card's wish and change line SHALL update only once the goddess's line has finished revealing, SHALL stay until the next exchange settles, and SHALL be announced once through the live region.

#### Scenario: Changed fields are named
- **WHEN** the report says the summary changed, one list gained an item and lost another, and the other fields are untouched
- **THEN** the line names the summary and that list, shows the list's added and removed counts as text, and names no other field

#### Scenario: Nothing changed
- **WHEN** the report shows no change in any field
- **THEN** the line states that nothing changed, in different text from a changed turn

#### Scenario: No report yet
- **WHEN** the state carries no change report
- **THEN** no change line is rendered

#### Scenario: The line waits for the reveal
- **WHEN** a live exchange arrives with a new proposal and report while its scene and line are still being presented
- **THEN** the card still shows the previous wish and line, and shows the new ones only after the last beat has been shown in full

#### Scenario: Announced once
- **WHEN** the new line appears after a reveal
- **THEN** the live region carries its text once, and a republish of the same report does not announce again

#### Scenario: Mount shows the committed report
- **WHEN** the panel mounts on a state that already carries a report
- **THEN** the line is shown at once without waiting for a reveal

#### Scenario: Not shown when finalized
- **WHEN** the session is finalized
- **THEN** the card shows no change line

### Requirement: The whole-wish view marks changes and names removed items

The whole-wish view SHALL mark each field the last change report touched, SHALL mark each added list item and requirement row, and SHALL list the removed items of a field by name under that field. Marks SHALL use text or a glyph and not colour alone. The view SHALL show the same wish and report the card currently shows.

#### Scenario: Added and removed are visible
- **WHEN** the report says a list gained one item and lost another
- **THEN** that field carries a changed mark, the gained item carries an added mark, and the lost item's text is listed under the field as removed

#### Scenario: Removed requirement row
- **WHEN** the report says a requirement row was removed
- **THEN** the row's text is listed as removed under the requirement section

#### Scenario: Untouched fields are unmarked
- **WHEN** a field is absent from the report's changes
- **THEN** it carries no changed mark and no removed list

#### Scenario: Summary state
- **WHEN** the report marks the summary as formed, and when it marks it as changed
- **THEN** the summary section's mark differs between the two

### Requirement: Requirement rows are editable when finalized

In the edit sheet of a finalized session the player SHALL be able to add a requirement row with a kind chosen from the closed set, edit a row's kind and text, and remove a row. The section SHALL show the row count against the limit of eight and SHALL offer no add control at the limit. A row whose text is blank SHALL block draft and confirm, be marked invalid with a message at that row, and keep every other local value. Unedited rows SHALL follow a republished proposal; edited rows SHALL be kept.

#### Scenario: Add, edit and remove
- **WHEN** the player adds a row, chooses its kind, types its text, removes an earlier row and saves a draft
- **THEN** `dream.draft` carries exactly the remaining rows with their kinds and trimmed texts in display order

#### Scenario: Limit
- **WHEN** eight rows exist
- **THEN** the count shows eight of eight and no add control is rendered

#### Scenario: Blank row blocks submission
- **WHEN** one row's text is blank and the player confirms or saves a draft
- **THEN** nothing is dispatched, that row is marked invalid with an alert message, and the other rows and fields keep their values

#### Scenario: Unsaved rows are protected on awaken
- **WHEN** the player has changed a row and activates the awaken row
- **THEN** the awaken check opens and names the unsaved edits

#### Scenario: Rows rehydrate like other fields
- **WHEN** the rows are unedited and a republish carries different rows, and when the player has edited a row before the republish
- **THEN** the first form shows the republished rows and the second keeps the player's rows
