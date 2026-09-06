# Delta spec: webclient-lore-codex-panel (webclient-lore-codex-drawer)

## ADDED Requirements

### Requirement: The codex drawer renders the panel in two navigation levels

The codex drawer SHALL render only the committed `lore_codex` panel. It SHALL present a category
strip carrying one control per shipped category plus an aggregate control covering every discovered
entry, an entry list for the selected category, and the selected entry's card. Navigation between
these levels SHALL be local to the client: selecting a category or an entry SHALL dispatch no action
and SHALL trigger no fetch, because the panel already carries every discovered entry and its rendered
card.

The card SHALL render the panel's card fields in the order the panel supplies them, with no field
added, reordered, reworded, or truncated by the drawer.

#### Scenario: Selecting a category filters locally
- **WHEN** the player selects a category control
- **THEN** the entry list shows exactly that category's entries and no request is dispatched

#### Scenario: Selecting an entry shows its card
- **WHEN** the player selects an entry
- **THEN** its card renders exactly the panel's field list in the panel's order, and no request is
  dispatched

#### Scenario: The aggregate control shows everything discovered
- **WHEN** the player selects the aggregate control
- **THEN** every discovered entry across every category is listed

### Requirement: The codex drawer discloses no more than the panel does

Each category control SHALL show that category's discovered count and nothing else — no registry
total, no denominator, no completion percentage, and no locked, hidden, or greyed entry placeholder.
A category shipped with zero entries SHALL render as a zero-count control. A codex with nothing
discovered SHALL render an honest empty state rather than a list of unavailable entries. An
unavailable panel SHALL render the registry-owned unavailable reason and no codex content.

#### Scenario: A category with nothing discovered shows zero, not a total
- **WHEN** the player has discovered nothing in a category
- **THEN** its control shows a count of zero and its entry list is empty, with no indication of how
  many entries the category could hold

#### Scenario: An empty codex renders an honest empty state
- **WHEN** the panel ships every category empty
- **THEN** the drawer renders an empty-codex message and no entry rows

#### Scenario: An unavailable panel renders its reason
- **WHEN** the panel is the common unavailable form
- **THEN** the drawer renders that reason and no category strip, entry list, or card

### Requirement: The codex opens from the command-line utility strip, not from the quest drawer

The codex drawer SHALL be opened by a labelled control in the command line's utility strip, and by no
control inside the quest drawer. The control SHALL open the codex reference drawer through the
store's single open-drawer entry point, so at most one focus-trapped surface is open at a time and
the existing drawer teardown rules apply unchanged. Its glyph SHALL be visually distinct from the
adjacent title-codex control, which opens a different system.

#### Scenario: The utility strip opens the codex
- **WHEN** the player activates the codex control in the command line's utility strip
- **THEN** the codex reference drawer opens and any previously open drawer or overlay closes

#### Scenario: The quest drawer offers no codex control
- **WHEN** the quest drawer renders
- **THEN** it contains no control that opens the codex

#### Scenario: The two codex controls are distinguishable
- **WHEN** the utility strip renders
- **THEN** the world-codex control and the title-codex control carry distinct labels and distinct
  glyphs
