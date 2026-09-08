# preset-authoring-docs Specification

## Purpose

Give a preset author one written path through the registry's current field
set — where a preset card's data lives, the decisions to make before writing
an entry, the load-time validators that guard it, and the mistakes that
non-obvious rules make easy — and keep that writing honest against the
dataclass so a future field cannot ship undocumented.

## Requirements

### Requirement: The player-preset authoring guide exists and is reachable
The repository SHALL carry a docsify page at
`docs/development/adding-player-presets.md`, written in Traditional Chinese and
structured after `docs/development/adding-items.md`, that walks an author through
adding one entry to `PLAYER_PRESET_REGISTRY`. It SHALL cover where a preset's
data lives, the decisions to make before writing the entry, a step-by-step
walkthrough, every load-time validator and what triggers it, the common
authoring mistakes, and the point at which another guide takes over.

The guide SHALL explain that a preset declares *allocations* bounded by
`resolve_starting_profile()` while the import card declares *absolute stats*, so
the difference reads as a deliberate balance decision rather than an omission.

The page SHALL be registered in `docs/_sidebar.md` under 開發者指南 alongside the
existing 新增魔法指南 and 新增物品指南 entries, and SHALL cross-link to those two
pages and to `docs/gm/characters.md` for the JSON import path.

#### Scenario: The guide is present and linked
- **WHEN** the documentation tree is inspected
- **THEN** `docs/development/adding-player-presets.md` exists and `docs/_sidebar.md` contains an entry pointing at it under 開發者指南

#### Scenario: The guide covers the authoring decisions
- **WHEN** the guide is read
- **THEN** it explains the allocation-versus-absolute-stats difference, names each load-time validator and what triggers it, and points to the item, spell, and GM import guides for work it does not cover

### Requirement: The guide stays in sync with the registry field set
A repo-wide contract test SHALL assert that every field name of `PlayerPreset`
appears in `docs/development/adding-player-presets.md` **as an inline-code span**
(`` `field_name` ``), not as a bare substring, so a short or common name such as
`key`, `age`, `sex`, or `race` cannot be satisfied incidentally by ordinary
prose. A field added to the registry without documentation SHALL fail the build.
The test SHALL derive the field set from the dataclass itself rather than from a
duplicated literal list.

#### Scenario: A documented registry passes
- **WHEN** the contract test runs against the shipped registry and guide
- **THEN** every `PlayerPreset` field name is found in the guide as an inline-code span and the test passes

#### Scenario: A field mentioned only in prose does not count
- **WHEN** a field name appears in the guide only as plain prose text and never as an inline-code span
- **THEN** the contract test fails, naming that field

#### Scenario: An undocumented new field fails the build
- **WHEN** a field is added to `PlayerPreset` and the guide is not updated
- **THEN** the contract test fails, naming the undocumented field
