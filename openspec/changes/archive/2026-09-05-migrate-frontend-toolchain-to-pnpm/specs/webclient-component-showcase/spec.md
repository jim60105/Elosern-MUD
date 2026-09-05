## MODIFIED Requirements

### Requirement: Breakdown-state stories cover the frozen manifest components

Storybook SHALL provide breakdown-state stories for the character drawer,
equipment doll, and inventory panel driven by a version-5 character fixture
mirroring the server contract's serialized sample — the fixture MUST carry
a worn bias-bearing item whose stored-base exposure differs from its
effective ordinal, at least one row at the 16-layer bound, and at least
one adjustment-bearing item — and the component coverage check SHALL pass
against the UNCHANGED frozen required-set manifest.

#### Scenario: v5 breakdown stories build

- **WHEN** `pnpm run build-storybook` builds the updated stories
- **THEN** the drawer, doll, and inventory stories render the version-5
  fixture's layers (including the 16-layer-bound row, all rendered without
  truncation) and adjustment strings

#### Scenario: Coverage gate stays clean

- **WHEN** `pnpm run showcase-coverage` runs after the change
- **THEN** the frozen required-set manifest is unchanged and coverage
  passes
