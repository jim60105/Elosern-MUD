# Spec Delta

## MODIFIED Requirements

### Requirement: The 念頭 sheet edits the direction in one flat modal layer

Opening the edit row SHALL show a modal sheet that traps focus and renders the rest of the stage inert. It SHALL contain, without nested disclosure:
- the summary field, with a code-point counter out of 2000 and a revert-to-server control when the field differs;
- a radio group offering 一段新的故事 and each server-offered thread;
- five chip lists: themes, atmosphere, participants, emphasis, exclusions;
- the readable experience requirements and their reviewed version when available.

#### Scenario: Chips and draft
- **WHEN** the player adds the theme 重逢 twice and saves a draft
- **THEN** one chip exists, `dream.draft` carries `themes: ["重逢"]`, the sheet closes, and the draft toast appears only after the newer state with the saved draft is committed

#### Scenario: Revision follows reconnect
- **WHEN** the edited summary and its corresponding requirements have been shown at a newer committed revision and the player confirms
- **THEN** `dream.confirm` carries the newer revision, edited summary as a new story and the exact shown requirements/version identity without requiring another model call

#### Scenario: Unreviewed summary edit cannot confirm stale requirements
- **WHEN** the player edits the summary but its corresponding requirement version has not been presented
- **THEN** confirmation refuses without losing local words or confirming stale requirements, while draft preservation and awakening remain usable offline

#### Scenario: Many threads
- **WHEN** more than eight threads are offered and the player filters by text
- **THEN** only matching threads remain listed

#### Scenario: A vanished saved thread stays selectable
- **WHEN** a saved thread is no longer offered by the server
- **THEN** it remains selectable in the radio group as 先前選定的故事線（已不在清單中）

#### Scenario: The thread filter appears above eight threads
- **WHEN** more than eight threads are offered
- **THEN** a text filter narrows the list

#### Scenario: Chip editing rules
- **WHEN** the player presses Enter in a chip input, or Backspace on an empty chip input
- **THEN** Enter adds a trimmed, de-duplicated chip and Backspace removes the last chip

#### Scenario: The draft button closes the sheet and keeps the dream
- **WHEN** the sheet's draft button is activated
- **THEN** it dispatches `dream.draft`, closes the sheet, and keeps the dream open

#### Scenario: Draft confirmation waits for the committed state
- **WHEN** a draft save is in progress
- **THEN** 念頭已記下，夢仍在繼續。 is shown and announced only once a newer committed state carries a saved draft, and a refused draft shows no confirmation

#### Scenario: Both buttons send the same payload shape
- **WHEN** the sheet's draft or confirm button dispatches (`dream.draft` / `dream.confirm`)
- **THEN** both send `{kind, thread_id, summary, requirements, requirement_version}` plus only the non-empty preference lists, at the latest committed revision; requirements are bounded structured data and requirement_version identifies the shown server-authored draft/version
- **AND** an unreviewed draft may carry empty requirements and null requirement_version, but confirmation requires the persisted shown valid version and deterministic equality validation without a model call

#### Scenario: Escape keeps the sheet's edits
- **WHEN** the player presses Escape with the sheet open
- **THEN** the sheet closes and keeps its edits

## ADDED Requirements

### Requirement: Dream confirmation displays the frozen experience requirements

The existing keepsake/draft presentation SHALL show readable bounded experience requirements for the version being confirmed alongside its direction. Rehydration and confirmation SHALL preserve server-authored requirement identity with the draft/version. Summary edits SHALL invalidate stale requirement confirmation until the corresponding version is presented. Existing exit, local-word preservation and accessibility behavior SHALL remain intact, without JSON or a new story panel.

#### Scenario: Player sees the intended executable experience
- **WHEN** the south-gate girl request is prepared for confirmation
- **THEN** the current dream surface displays place/new-role/private-commission meaning and sends the exact shown current version requirements with confirmation

#### Scenario: Reconnect and local edit
- **WHEN** the saved draft republishes during unsent local editing
- **THEN** unsent words survive, current requirements track the reviewed version and unseen or stale server requirements are not silently confirmed

#### Scenario: Confirmation closes without preparation lock
- **WHEN** valid confirmation commits with generation still pending
- **THEN** the dream stage closes and waking controls remain usable; preparation/waiting messages appear through ordinary output rather than keeping the dream modal locked
