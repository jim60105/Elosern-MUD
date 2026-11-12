## ADDED Requirements

### Requirement: The version-4 projection carries one category with tile artwork
The version-4 gallery projection SHALL carry every category descriptor and only the selected category's groups. Each listed subject SHALL carry its stored card count and the artwork descriptor of its resolved default image, or null when none resolves. The projection SHALL read only.

#### Scenario: Only the selected category's subjects are listed
- **WHEN** the selection names `party` for an actor with two account characters and one companion
- **THEN** the projection lists exactly the companion and still reports the counts of all five categories

#### Scenario: A tile carries its default artwork without a selection
- **WHEN** a listed companion that is not selected has a default card
- **THEN** its subject row carries that card's artwork descriptor and its card count

#### Scenario: Building twice changes nothing
- **WHEN** the projection is built twice for the same session
- **THEN** both results are identical and no gallery record, card, job or preference changed

### Requirement: The version-4 selection is remembered per category with fallbacks
The session SHALL remember one category and one subject per category for the owning character, kept across possession and retired when the session puppets another owner or ends. A remembered subject no longer listed SHALL fall back to the category default (the live character in `mine`, else the first listed subject, else null); a remembered category that is disabled SHALL fall back to `mine`. A fresh session SHALL open on `mine` with the live character selected.

#### Scenario: A fresh session opens on the live character
- **WHEN** a session with no stored selection builds the projection
- **THEN** `category` is `mine` and `selected` is the live character

#### Scenario: Each category keeps its own subject
- **WHEN** the player selects companion B in `party`, switches to `monster`, selects species `t_a`, then switches back to `party`
- **THEN** `selected` is B

#### Scenario: A vanished subject falls back to the category default
- **WHEN** the remembered `party` subject leaves the party
- **THEN** `selected` is the first listed companion, or null when the party is empty

#### Scenario: Possession keeps the stored selection
- **WHEN** the player possesses a companion after selecting species `t_a` in `monster`
- **THEN** the projection still selects `monster` and `t_a`

#### Scenario: Unknown or disabled targets are refused without a write
- **WHEN** the store is asked to select the disabled `people` category, or a subject not listed in the selected category
- **THEN** it returns the `unknown_category` or `unknown_subject` rejection and the stored selection is unchanged
