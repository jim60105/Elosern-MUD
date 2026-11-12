## ADDED Requirements

### Requirement: Each kind declares its card face rectangle, stage and deletion support
Every capability record SHALL declare three booleans: whether a card may carry a player-set face rectangle, whether it may carry a player-set stage transform, and whether a player may delete a card. A kind declared as having no gallery SHALL declare all three false.

#### Scenario: The three facts are readable from the declaration
- **WHEN** the capability records of every kind are read
- **THEN** each reports `supports_face_rect`, `supports_stage` and `supports_card_delete` as booleans without consulting any other module

#### Scenario: A gallery-less kind claiming an operation fails the contract
- **WHEN** the contract check runs against a table whose gallery-less entry declares `supports_stage` true
- **THEN** it reports a violation naming that kind

### Requirement: The sole writer refuses card operations a kind does not declare
The gallery writer SHALL refuse, with a typed error and no write, a face-rectangle update or official face-rectangle override for a kind not declaring face rectangles, a stage update or official stage override for a kind not declaring stage, and a generation request carrying a face rectangle for a kind not declaring face rectangles. Card deletion is enforced at the player action (see `webclient-gallery-management-actions`).

#### Scenario: A changed declaration changes what the writer allows
- **WHEN** a test patches a kind's declaration to `supports_stage` false and a stage update is attempted on its card
- **THEN** a typed error is raised and the stored card is unchanged, with no edit to the enforcing module

#### Scenario: Declared operations keep working
- **WHEN** the same operations are attempted for a kind declaring all three facts true
- **THEN** each succeeds exactly as before this declaration existed
