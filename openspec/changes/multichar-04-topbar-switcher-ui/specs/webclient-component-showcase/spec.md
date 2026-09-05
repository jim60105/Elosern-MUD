# Delta spec: webclient-component-showcase (multichar-04-topbar-switcher-ui)

The redesign roadmap's delivery table is complete (H1–H6 are all done), yet the manifest still has
to grow whenever a feature change adds a backed surface — as this one does. The governance
requirement is restated to admit a named feature change under the *same* lockstep obligations,
rather than leaving the manifest to grow outside the rule it declares.

## MODIFIED Requirements

### Requirement: The frozen component set grows only through a governed redesign wave
The required-component manifest SHALL remain the authoritative frozen set, and it SHALL grow only
through a change that names the growth as part of its own scope: a change in the WebClient
Contextual HUD Redesign roadmap's delivery table, or a feature change that introduces a component
backed by a committed presentation panel. A change that adds a component SHALL, in the same change,
add its title to the manifest, ship its Storybook story with deterministic offline args, and extend
this capability's spec in lockstep — never a manifest edit alone. A component whose surface has no
committed backing read model SHALL NOT be added under either route; it belongs on the deferred list
instead. A component SHALL NOT be wired into the live application before its story exists. On
completion of the redesign the manifest SHALL be re-frozen at the complete set then current, and
each later growth SHALL re-freeze it at its new complete set.

#### Scenario: A wave adds a component with its story in the same change
- **WHEN** a roadmap wave introduces a new component
- **THEN** the same change adds its manifest title, its Storybook story with deterministic offline args, and the matching spec entry, and the component-coverage gate passes

#### Scenario: A feature change adds a backed component under the same obligations
- **WHEN** a feature change outside the redesign roadmap introduces a component rendered entirely from a committed presentation panel
- **THEN** the same change adds its manifest title, its Storybook story with deterministic offline args, and the matching spec entry, and the component-coverage gate passes

#### Scenario: An unbacked component cannot enter the manifest
- **WHEN** a change proposes a component whose surface has no committed backing read model
- **THEN** it is refused entry to the manifest and remains a deferred surface

#### Scenario: A manifest edit without a story fails the gate
- **WHEN** a manifest title is added without a matching registered story
- **THEN** the component-coverage gate fails and the change cannot land

#### Scenario: A story without a manifest entry fails the gate
- **WHEN** a story is registered whose title is absent from the manifest
- **THEN** the component-coverage gate fails, so the frozen set cannot grow silently
