## ADDED Requirements

### Requirement: Exactly one people group is expanded
When the selected category is `people`, the panel SHALL carry every place group's label and count, and the subjects of exactly one expanded group: the session's remembered place for the owning character, else the most recent place. Collapsed groups SHALL carry no subjects. The selected person SHALL be listed in the expanded group, falling back to its first subject.

#### Scenario: The most recent place opens first
- **WHEN** a fresh session selects `people` and the record has places P2 (most recent) and P1
- **THEN** P2 is expanded with its subjects, P1 is collapsed with its count and no subjects, and `selected` is P2's first subject

#### Scenario: A remembered place that is gone falls back
- **WHEN** the remembered expanded place no longer has any listed person
- **THEN** the most recent remaining place is expanded

#### Scenario: Admission covers collapsed places
- **WHEN** a mutating gallery action names a person listed only in a collapsed place
- **THEN** the subject is admitted
