## ADDED Requirements

### Requirement: The frozen component set grows only through a governed redesign wave
The required-component manifest SHALL remain the authoritative frozen set, and it SHALL grow only
through a change named in the WebClient Contextual HUD Redesign roadmap's delivery table. A wave that
adds a component SHALL, in the same change, add its title to the manifest, ship its Storybook story
with deterministic offline args, and extend this capability's spec in lockstep — never a manifest edit
alone. A component SHALL NOT be wired into the live application before its story exists. On completion
of the redesign the manifest SHALL be re-frozen at the complete new set.

#### Scenario: A wave adds a component with its story in the same change
- **WHEN** a roadmap wave introduces a new component
- **THEN** the same change adds its manifest title, its Storybook story with deterministic offline args, and the matching spec entry, and the component-coverage gate passes

#### Scenario: A manifest edit without a story fails the gate
- **WHEN** a manifest title is added without a matching registered story
- **THEN** the component-coverage gate fails and the change cannot land

#### Scenario: A story without a manifest entry fails the gate
- **WHEN** a story is registered whose title is absent from the manifest
- **THEN** the component-coverage gate fails, so the frozen set cannot grow silently
