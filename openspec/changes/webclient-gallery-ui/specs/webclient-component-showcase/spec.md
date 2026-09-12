# Delta spec: webclient-gallery-ui (webclient-component-showcase)

## MODIFIED Requirements

### Requirement: The frozen component set grows only through a governed redesign wave

The required-component manifest SHALL remain the authoritative frozen set, and it SHALL grow only
through a change that names the growth as part of its own scope: a change in the WebClient
Contextual HUD Redesign roadmap's delivery table, or a feature change that introduces a component
backed by a committed presentation panel — the portrait-gallery family
(`Data/GalleryPanel`, `Data/GalleryDetailRail`, `Overlays/GalleryGenerateDrawer`,
`Overlays/GalleryBindingDrawer`, `Overlays/GalleryFaceRectModal`) joins the frozen set under
exactly this route. A change that adds a component SHALL, in the same change, add its title to
the manifest, ship its Storybook story with deterministic offline args, and extend this
capability's spec in lockstep — never a manifest edit alone. A component whose surface has no
committed backing read model SHALL NOT be added under either route; it belongs on the deferred
list instead. A component SHALL NOT be wired into the live application before its story exists.
On completion of the redesign the manifest SHALL be re-frozen at the complete set then current,
and each later growth SHALL re-freeze it at its new complete set.

#### Scenario: A wave adds a component with its story in the same change

- **WHEN** a roadmap wave introduces a new component
- **THEN** the same change adds its manifest title, its Storybook story with deterministic offline args, and the matching spec entry, and the component-coverage gate passes

#### Scenario: A feature change adds a backed component under the same obligations

- **WHEN** a feature change outside the redesign roadmap introduces a component rendered entirely from a committed presentation panel
- **THEN** the same change adds its manifest title, its Storybook story with deterministic offline args, and the matching spec entry, and the component-coverage gate passes

#### Scenario: The gallery family joins the frozen set in its own change

- **WHEN** the gallery-UI change lands its five gallery components
- **THEN** the same change's manifest append, story files, and spec entry keep the component-coverage gate green, and no gallery component is mounted in the live application before its story exists

#### Scenario: A manifest edit without a story fails the gate

- **WHEN** a manifest title is added without a matching registered story
- **THEN** the component-coverage gate fails and the change cannot land

#### Scenario: A story without a manifest entry fails the gate

- **WHEN** a story is registered whose title is absent from the manifest
- **THEN** the component-coverage gate fails, so the frozen set cannot grow silently
