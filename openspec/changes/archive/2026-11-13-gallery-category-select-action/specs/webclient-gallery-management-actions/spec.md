## ADDED Requirements

### Requirement: Category selection writes only session presentation state
The production registry SHALL register `gallery.category.select` with an exact payload of `category` (one of the five category keys). It SHALL write only the session's stored gallery category, SHALL reject a disabled or unknown category with `unknown_category`, SHALL declare the affected panels `gallery`, `art` and `roster`, and SHALL emit one `gallery_action` event.

#### Scenario: Selecting an enabled category succeeds
- **WHEN** a client dispatches `gallery.category.select` with `category: "monster"`
- **THEN** the result succeeds, the stored category is `monster`, one update refreshes gallery, art and roster, and no gallery record, card or job changed

#### Scenario: A disabled category is refused without a write
- **WHEN** a client dispatches `gallery.category.select` with `category: "people"` while that category is disabled
- **THEN** the result is `rejected` with `unknown_category`, the stored selection is unchanged, and one update refreshes the three panels

#### Scenario: An extra field fails the schema
- **WHEN** the payload carries a field beside `category`, or a category outside the five keys
- **THEN** the dispatcher returns `malformed_payload` and the adapter never runs
