## MODIFIED Requirements

### Requirement: Accurate command details

The reference entry for each project-authored and contrib command SHALL state the command's
primary key, its aliases (including Traditional Chinese aliases and, for localized wrappers, the
retained full English alias set), its argument syntax, its availability context, and a non-empty
Traditional Chinese description. The key and aliases SHALL match the command class definition, the
syntax and context SHALL match the curated command manifest in `tests/test_command_docs.py`, and
admin commands SHALL carry their permission requirement. The `rest` entry's syntax SHALL document the optional declared-practice clause
(`rest <duration> [practice <skill>]`) and its description SHALL state that a declared practice
settles hourly proficiency for the owned, uncapped skill while an unlabeled rest advances time
with no growth; the curated manifest and the `docs/game/commands.md` rest row SHALL carry the
same clause.

#### Scenario: Key and aliases match the command class

- **WHEN** the contract test inspects a project-authored command class mounted in a player cmdset
- **THEN** the class key and aliases SHALL appear in the corresponding reference entry

#### Scenario: Syntax and context match the curated manifest

- **WHEN** the contract test runs
- **THEN** the syntax row of each canonical entry SHALL equal the manifest syntax for that key and
  the context row SHALL equal the manifest context

#### Scenario: Context restrictions are documented

- **WHEN** a command is only available in a specific context (combat session, guild service host,
  shop merchant, character creation, or admin permission)
- **THEN** the reference entry SHALL state that restriction, and for commands whose
  `help_category` is `Combat`, `Guild`, `Economy`, or `Admin` the context row SHALL be consistent
  with it

#### Scenario: Admin commands carry a permission note

- **WHEN** a command class is locked to `Developer` permission (the `art` command family)
- **THEN** the reference entry SHALL mark the command as admin-only and the contract test SHALL
  verify the class locks require `Developer`

#### Scenario: Builder-gated commands carry a permission note

- **WHEN** a command class is locked to `Builder` permission (the XYZGrid `map`, `@teleport`, and
  `@open` commands)
- **THEN** the reference entry SHALL state the builder restriction and the contract test SHALL
  verify the class locks require `Builder`

#### Scenario: The rest entry documents the practice clause

- **WHEN** the drift contract test inspects the `rest` canonical entry
- **THEN** the syntax row equals the manifest's `rest <duration> [practice <skill>]` form, the
  description mentions hourly declared-practice settlement and the zero-growth plain rest, and
  the overview's rest row agrees
