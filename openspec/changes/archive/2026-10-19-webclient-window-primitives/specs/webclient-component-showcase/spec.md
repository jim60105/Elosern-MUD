# Spec Delta

## MODIFIED Requirements

### Requirement: The frozen component set grows only through a governed redesign wave

The required-component manifest SHALL remain the authoritative frozen set, and it SHALL grow only
through a change that names the growth as part of its own scope: a change in the WebClient
Contextual HUD Redesign roadmap's delivery table, a change in the WebClient AVG stage redesign
series, or a feature change that introduces a component backed by a committed presentation panel
or by a committed action-result read model.

#### Scenario: A wave adds a component with its story in the same change

- **WHEN** a roadmap wave introduces a new component
- **THEN** the same change adds its manifest title, its Storybook story with deterministic offline args, and the matching spec entry, and the component-coverage gate passes

#### Scenario: A feature change adds a backed component under the same obligations

- **WHEN** a feature change outside the redesign roadmap introduces a component rendered entirely from a committed presentation panel
- **THEN** the same change adds its manifest title, its Storybook story with deterministic offline args, and the matching spec entry, and the component-coverage gate passes

#### Scenario: The gallery family joins the frozen set in its own change

- **WHEN** the gallery-UI change lands its five gallery components
- **THEN** the same change's manifest append, story files, and spec entry keep the component-coverage gate green, and no gallery component is mounted in the live application before its story exists
- **AND** `Data/GalleryPanel` includes an offline interactive storyboard for the
  complete management journey, with a documented frame guide

#### Scenario: A manifest edit without a story fails the gate

- **WHEN** a manifest title is added without a matching registered story
- **THEN** the component-coverage gate fails and the change cannot land

#### Scenario: A story without a manifest entry fails the gate

- **WHEN** a story is registered whose title is absent from the manifest
- **THEN** the component-coverage gate fails, so the frozen set cannot grow silently

#### Scenario: A governed wave deletes a component in lockstep

- **WHEN** a change in the AVG stage redesign series deletes a manifest-listed component
- **THEN** the same change removes the component file, its manifest title, its Storybook story, and every spec and test reference to it, and the component-coverage gate passes on the smaller re-frozen set

#### Scenario: The NPC author editor joins through the action-result route

- **WHEN** the NPC author-editor window change lands `Overlays/NpcPersonaEditor`
- **THEN** the same change adds its manifest title, its Storybook story with deterministic offline args for every editor state, and the matching spec entry, the component-coverage gate passes, and the component is not mounted in the live application before its story exists

#### Scenario: The AVG stage redesign series is a governed add-and-delete wave
- **WHEN** a change in the WebClient AVG stage redesign series
  (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md`) names a component
  change as part of its own scope
- **THEN** the change grows or shrinks the frozen set under the governed wave route, since such a
  wave MAY both add and delete components

#### Scenario: The portrait-gallery family joins through the presentation-panel route
- **WHEN** a feature change introduces a component backed by a committed presentation panel
- **THEN** it joins the frozen set under exactly this route, as the portrait-gallery family
  (`Data/GalleryPanel`, `Data/GalleryDetailRail`, `Overlays/GalleryGenerateDrawer`,
  `Overlays/GalleryBindingDrawer`, `Overlays/GalleryFaceRectModal`) did

#### Scenario: The NPC author editor route needs a main-spec-shaped action-result model
- **WHEN** a feature change introduces a component rendered entirely from a committed
  action-result read model whose exact data shape is a main-spec requirement
- **THEN** it joins the frozen set under exactly this route, as the NPC author editor
  (`Overlays/NpcPersonaEditor`, backed by the `npc.persona.read`/`npc.persona.update` result
  data) did

#### Scenario: An unbacked component belongs on the deferred list
- **WHEN** a proposed component's surface has no committed backing read model
- **THEN** it SHALL NOT be added to the frozen set under any route and belongs on the deferred
  list instead

#### Scenario: No component goes live before its story exists
- **WHEN** a component is wired into the live application
- **THEN** its story already exists, since a component SHALL NOT be wired in before then

#### Scenario: A governed deletion leaves nothing behind
- **WHEN** a governed wave change deletes a component
- **THEN** the same change deletes the component file, removes its title from the manifest,
  deletes its Storybook story, deletes or re-points every test that mounts it, and edits this
  capability's spec so no requirement names it — never a component deletion that leaves a
  manifest title, a story, or a spec reference behind

#### Scenario: The manifest re-freezes at each complete set
- **WHEN** the redesign completes, and again at each later growth of the frozen set
- **THEN** the manifest is re-frozen at the complete set then current, and each later growth
  re-freezes it at its new complete set

#### Scenario: The party member management series is a governed add-and-delete wave
- **WHEN** a change in the party member management series (`docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md`) names a component addition or deletion as part of its own scope
- **THEN** it grows or shrinks the frozen set under the governed wave route, adding `Core/WindowFrame`, `Core/MemberRail`, `Core/ListDetail`, `Core/ActionBar` and `Data/HoldingsStrip` and the party window and shop window components with their stories, and deleting `InventoryPanel`, `EquipmentDoll`, `CharacterStatusDrawer`, `SkillBook`, `LineagePanel`, `PartyDrawer` and `ShopPanel` in lockstep with their stories, manifest titles, spec references and `.elosern-root` duplicate rules
