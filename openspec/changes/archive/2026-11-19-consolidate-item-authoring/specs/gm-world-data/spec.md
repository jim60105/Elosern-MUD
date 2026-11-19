# GM World Data Delta

## ADDED Requirements

### Requirement: Item detail identifies the file that supplied the loaded row
The existing read-only item detail response and page SHALL report the loaded row's exact repository-relative source file. Registry index and list pages SHALL continue to identify the catalog directory.

#### Scenario: Items in different files expose distinct provenance
- **WHEN** an operator opens the detail for two loaded items from different authored files
- **THEN** each detail shows its own source file, not just the catalog directory, and existing item reference links remain navigable

#### Scenario: Unapplied edits do not change provenance
- **WHEN** an item is moved on disk but the server still serves the previous loaded catalog
- **THEN** the item detail reports the file that provided the loaded row
