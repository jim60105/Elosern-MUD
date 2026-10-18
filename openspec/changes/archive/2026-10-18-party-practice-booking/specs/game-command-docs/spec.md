# Spec Delta

## MODIFIED Requirements

### Requirement: Accurate command details

The reference entry for each project-authored and contrib command SHALL state the command's
primary key, its aliases (including Traditional Chinese aliases and, for localized wrappers, the
retained full English alias set), its argument syntax, its availability context, and a non-empty
Traditional Chinese description. The key and aliases SHALL match the command class definition,
and the syntax and context SHALL match the curated command manifest in `tests/test_command_docs.py`.

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

- **WHEN** a command class is locked to `Developer` permission (the `art` command family and the
  account character-management commands `charcreate` and `chardelete`)
- **THEN** the reference entry SHALL mark the command as admin-only and the contract test SHALL
  verify the class locks require `Developer`

#### Scenario: Raising the character cap does not open a player creation command

- **WHEN** the configured character capacity is greater than one and an account holding only
  Player permission enters `charcreate` or `chardelete`
- **THEN** the command is refused by its lock, no character is created or deleted, and the
  reference page's 管理員 rows remain accurate

#### Scenario: Builder-gated commands carry a permission note

- **WHEN** a command class is locked to `Builder` permission (the XYZGrid `map`, `@teleport`, and
  `@open` commands)
- **THEN** the reference entry SHALL state the builder restriction and the contract test SHALL
  verify the class locks require `Builder`

#### Scenario: The rest entry documents the practice clause

- **WHEN** the drift contract test inspects the `rest` canonical entry
- **THEN** the syntax row equals the manifest's `rest <duration> [practice <skill>]` form, the
  description mentions hourly declared-practice settlement, that a clause-less rest settles the
  present members' standing bookings, and that it grows nothing only when no member has one, and
  the overview's rest row agrees

#### Scenario: The practice entry documents the standing booking

- **WHEN** the drift contract test inspects the `修煉` canonical entry
- **THEN** its key is `修煉`, its alias set is `practice`, its syntax row equals the manifest's
  `修煉 <技能> [= <成員>]` form, its context row equals the manifest context, its description
  states that booking advances no time, settles by whole hours and refuses in combat, and the
  overview carries a linked row naming the member clause

#### Scenario: Admin commands carry their permission requirement

- **WHEN** the reference documents an admin command
- **THEN** the entry SHALL carry its permission requirement

#### Scenario: Account character-management commands are Developer-locked

- **WHEN** the account character-management commands `charcreate` and `chardelete` are mounted
- **THEN** they SHALL be mounted on the project `AccountCmdSet` locked to `Developer` permission
  rather than Evennia's default player permission, so the documented 管理員 context is enforced by
  the mounted classes and the character-creation wizard remains the single player-facing creation path

#### Scenario: The rest clause obligations span reference, manifest, and overview

- **WHEN** the `rest` documentation is authored
- **THEN** the entry's syntax SHALL document the optional declared-practice clause
  (`rest <duration> [practice <skill>]`) and its description SHALL state that a declared practice
  settles hourly proficiency for the owned, uncapped skill, that an unlabeled rest declares no new
  practice but still settles the present members' standing bookings, and that it advances time
  with no growth only when none stands
- **AND** the curated manifest and the `docs/game/commands.md` rest row SHALL carry the same clause
