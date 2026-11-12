## ADDED Requirements

### Requirement: Group selection expands one place and writes only presentation state
The production registry SHALL register `gallery.group.select` with an exact payload of `group`. While the selected category pages by group (`people`), it SHALL record that group as the category's expanded group for the owning character and SHALL reject a key naming no current group, or any call in another category, with `unknown_group`. It SHALL write no gallery record, card or job, declare the affected panels `gallery`, `art` and `roster`, and emit one `gallery_action` event.

#### Scenario: Expanding another place collapses the current one
- **WHEN** `people` shows P2 expanded and P1 collapsed, and a client dispatches `gallery.group.select` with `group` P1
- **THEN** the result succeeds and the refreshed panel shows P1 expanded with its subjects and P2 collapsed with its count

#### Scenario: A tier group cannot be selected
- **WHEN** the selected category is `monster` and a client dispatches `gallery.group.select` with a tier key
- **THEN** the result is `rejected` with `unknown_group` and the stored selection is unchanged

#### Scenario: An extra field fails the schema
- **WHEN** the payload carries a field beside `group` or a key outside the group grammar
- **THEN** the dispatcher returns `malformed_payload` and the adapter never runs
