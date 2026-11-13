# Spec Delta

## ADDED Requirements

### Requirement: Text dream commands reach thread choice, finalize and the change report

The text dream command SHALL offer thread choice and finalize through the same guarded operations as the browser actions. Bare `dream` SHALL show the whole current proposal, the thread it belongs to and the last change report, naming removed items. A delivered `dream say` SHALL end its output with a one-line change summary. Hints SHALL list only the operations the current stage allows. Command documentation SHALL match the syntax and availability.

#### Scenario: Thread choice by number or new
- **WHEN** the owner types the thread command with the number of an offered thread, and later with the new-story word, before any message
- **THEN** each invokes the shared thread-choice operation with that thread or with none, and the stored choice follows

#### Scenario: Thread command without argument lists choices
- **WHEN** the owner types the thread command with no argument
- **THEN** the output lists the new-story option and each offered thread with its number, and nothing is written

#### Scenario: Unknown thread argument
- **WHEN** the argument is neither an offered number, an offered thread identity nor the new-story word
- **THEN** a local refusal is shown and the shared operation is not invoked

#### Scenario: Finalize command
- **WHEN** the owner types the finalize command while conversing with no response pending
- **THEN** the shared finalize operation runs and the next state output offers draft and confirmation and no longer offers free text

#### Scenario: Bare dream shows the proposal and removed items
- **WHEN** the last settled exchange added one list item and removed another, and the owner types bare `dream`
- **THEN** the output contains every non-empty proposal field, the thread line, and a change report that names both the added and the removed item

#### Scenario: Say ends with the change summary
- **WHEN** a `dream say` is delivered, once with edits and once with none
- **THEN** the last output line is the one-line change summary, which names the changes in the first case and states that nothing changed in the second

#### Scenario: Summary replacement only after finalize
- **WHEN** the owner types the draft command with text while conversing, and again after finalize
- **THEN** the first is refused with the server's reason and the second replaces only the summary, keeping lists, requirement rows and thread

#### Scenario: Documentation parity
- **WHEN** the command documentation contract is checked
- **THEN** the documented dream syntax equals the mounted command's usage, including the thread and finalize forms
