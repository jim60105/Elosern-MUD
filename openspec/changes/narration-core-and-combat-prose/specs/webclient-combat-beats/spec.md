# Spec Delta

## ADDED Requirements

### Requirement: Authored narration cannot make a round's beats unavailable

Every beat's text SHALL come from a narration line that is bounded when it is authored and
re-checked against the actual rendered names when the entry is built, degrading to a
participant-free compact line when no named variant fits. Beat derivation SHALL keep every
existing bound and HP-projection check; narration SHALL NOT be a possible cause of an
unavailable panel.

#### Scenario: An over-long participant key does not lose the panel

- **WHEN** a settled round's log contains a `damage` entry whose target key is far longer than
  any authored name
- **THEN** the round's beats are available, each beat's text is within the beat-text bound, and
  the projected HP equals the round's recorded HP

#### Scenario: The bounds themselves are unchanged

- **WHEN** a round exceeds the beat count or the round-id bound
- **THEN** the panel is unavailable exactly as before, with the same named error reason

### Requirement: Narration adds no beat to an ordinary round

An ordinary resolved action SHALL keep exactly the entry cardinality it has today, because the
action line is composed into the log's first entry rather than appended as its own entry. The
only entry narration may add SHALL be the single action-narration entry for a successful log
that would otherwise contain no entries.

#### Scenario: A damage action yields the same beat count

- **WHEN** an attack action emits `resource_spend`, `roll`, `damage` and `skill_practice`
  entries
- **THEN** the round's beat list has exactly four beats for it, in the same order as before

#### Scenario: An empty successful cast yields one beat

- **WHEN** a successful action stages no effects at all
- **THEN** its log contains one action-narration entry and the round's beat list contains that
  single additional beat
