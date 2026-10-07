## MODIFIED Requirements

### Requirement: The vitals island is shown only in combat or while a vital or a condition needs attention
Subject to the existing committed-mode visibility matrix and status availability gate, the HUD SHALL show the vitals dock, comprising the condition icon row and vitals bars, only while at least one of these holds for the committed state: the committed mode is `combat`; the derived low-HP presentation state is true; any `status.resources` vital (hp, mp, sp) carries a numeric `current` below its numeric `maximum`; or `status.conditions` carries an entry whose `severity` is `warning`, `harmful`, or `critical` and whose `provenance.kind` is `non_equipment`, `mixed`, or `unknown`. A proven equipment-only condition SHALL NOT independently reveal the dock, regardless of adverse severity. A beneficial or informational condition, including a passive skill-owned combat modifier, SHALL NOT independently reveal it. An entry with a missing or unknown severity SHALL NOT independently reveal it. Missing or malformed required provenance SHALL be rejected under the status protocol contract rather than interpreted as an equipment exemption.

While the dock is visible its condition icons SHALL render every committed condition, regardless of severity or provenance. Otherwise the dock SHALL be hidden: from the moment the committed revision turns the rule false it SHALL leave the accessibility tree, the tab order, and pointer hit-testing, and once its exit transition has finished it SHALL be `display:none` and contribute no visible box. The dock SHALL enter and leave with the existing fade and 12px slide at the client's motion level; at `off` it SHALL show and hide in the same frame as the commit. The overall rule SHALL be derived client-side from the committed mode and status panel, including server-authored condition provenance; it SHALL NOT use narrative text, action-result predictions, local equipment inference, an extra server request, or a timer. A vital absent from the payload or carrying non-numeric fields SHALL NOT count as below its maximum.

The existing visibility matrix SHALL keep the dock hidden in dialogue and creation, even with depleted resources or independently adverse conditions. An unavailable `status` panel SHALL render no dock, including in combat. Leaving dialogue SHALL reapply the data rule to then-committed state. While hidden, the dock SHALL keep its trailing-bar memory, so the first committed revision that lowers a vital from full shows the dock with the trailing bar lagging from the previously committed ratio exactly as an always-visible dock would. When a committed revision turns the rule false while focus is inside the dock, focus SHALL move to the action dock before hiding through the existing focus-restore path; mode changes SHALL retain their existing mode-specific focus home.

#### Scenario: Full health outside combat hides the island
- **WHEN** the committed mode is exploration, every committed vital's `current` equals its `maximum`, and `status.conditions` is empty
- **THEN** the vitals dock is absent from the accessibility tree and tab order, and after any exit transition it is hidden with `display:none` and no bars, numerals, icons, or low-HP marker visible

#### Scenario: A vital below its maximum shows the island
- **WHEN** a committed revision in exploration carries `mp` at 40 of 60 with no condition
- **THEN** the dock renders every vital's icon, label, and on-track `current / maximum` numerals

#### Scenario: A condition shows the island at full health
- **WHEN** an exploration revision carries full vitals and a harmful condition with non-equipment provenance
- **THEN** the dock renders its bars and condition icon

#### Scenario: A beneficial-only condition keeps the island hidden at full health
- **WHEN** an exploration revision carries full vitals and only beneficial conditions, including a passive skill-owned combat-modifier row
- **THEN** the dock stays hidden with `display:none`, none of its condition icons is visible or focusable, and no enter transition plays

#### Scenario: Visible island renders every condition chip
- **WHEN** the dock is visible because a vital is below its maximum and committed conditions include beneficial, informational, and equipment-only adverse entries
- **THEN** its row renders every entry without changing severity or removing equipment-origin icons

#### Scenario: Combat always shows the island
- **WHEN** available status commits in combat with every vital full and no condition or only equipment-only conditions
- **THEN** the vitals dock renders

#### Scenario: The first hit from full health keeps its trailing bar
- **WHEN** the dock is hidden at full health with only equipment-only adverse conditions and the next same-epoch committed revision lowers `hp`
- **THEN** the dock renders, hp fill shows the new ratio, and the trailing bar starts from the previously committed full ratio

#### Scenario: Focus is rescued before the island hides
- **WHEN** focus is inside the dock outside combat with full vitals and a revision removes the final independently adverse condition, leaving only beneficial or equipment-only adverse entries
- **THEN** focus moves to the action dock before the dock is hidden, with no focus lost to the document body

#### Scenario: Every adverse severity respects the equipment exemption
- **WHEN** separate exploration fixtures have full resources and only a proven equipment-origin warning, harmful, or critical condition
- **THEN** each fixture keeps the dock hidden while its original severity and condition remain available in status

#### Scenario: Mixed and independent sources retain attention
- **WHEN** full-health exploration has an equipment-only condition plus an independent adverse condition, or one adverse condition with mixed provenance
- **THEN** the dock is visible and displays all conditions, including the equipment-only row

#### Scenario: Unknown origin is not an equipment exemption
- **WHEN** full-health exploration carries an adverse condition with valid unknown provenance
- **THEN** the dock reveals without inventing an equipment source

#### Scenario: Equip and unequip follow accepted canonical updates
- **WHEN** synthetic equipment induces a threshold warning at full resources, a committed equip update arrives, and a later committed unequip update removes the equipment-dependent warning
- **THEN** both revisions keep the dock hidden, condition membership and source detail match each accepted revision, and an independent same-definition buff would continue to reveal the dock after unequip

#### Scenario: Same-code warning changes provenance on a state commit
- **WHEN** full-health exploration has an equipment-dependent threshold warning and a later committed stored-state change makes the same warning match independently
- **THEN** the dock reveals on that accepted revision although condition code and severity are unchanged, and the replacement provenance reports its independent or mixed source

#### Scenario: Stale updates cannot restore old attention
- **WHEN** an accepted status revision changes a warning from mixed to equipment-only and an older revision or retired-epoch message arrives
- **THEN** the old message is discarded and cannot restore the old provenance or reveal the hidden dock

#### Scenario: Dialogue and creation keep their existing gates
- **WHEN** mode is dialogue or creation with available depleted resources and an independent critical condition
- **THEN** the vitals dock remains hidden through the mode gate, and returning to exploration reveals it from the committed data without a new attention request

#### Scenario: Unavailable status does not fabricate attention
- **WHEN** status commits its unavailable form in exploration or combat after previously carrying independent adverse conditions
- **THEN** no vitals dock, old condition icon, or fabricated resource is rendered, while other registered presentation remains usable

## ADDED Requirements

### Requirement: Condition detail preserves equipment provenance without hiding gameplay conditions
The dock's existing tooltip, overflow detail, and accessible condition names, and the complete character-status condition roster SHALL preserve the label, severity, supplied duration and exact modifier values of every committed condition. These surfaces SHALL disclose all equipment source labels supplied by `provenance.equipment_sources`, without guessing a label from an item key or requiring another panel. Mixed provenance SHALL identify that an independent source also applies; unknown provenance SHALL state neutrally that the source is unavailable. Non-equipment provenance SHALL NOT claim an equipment source. Equipment-only conditions SHALL remain available in the full status surface when the contextual dock is hidden. Distinct committed buff instances sharing a code SHALL remain individually readable with their own source and duration in normal and overflow detail paths.

#### Scenario: Hidden equipment condition remains inspectable
- **WHEN** full-health exploration has only a synthetic equipment-origin warning and the player opens character status
- **THEN** the dock remains hidden and the full roster contains that warning with its original severity, values, and registry-backed equipment source label

#### Scenario: Another trigger reveals equipment detail
- **WHEN** depleted resources reveal the dock while an equipment-origin adverse condition remains committed
- **THEN** its icon, tooltip, overflow detail when applicable, and accessible name retain the condition's exact data and identify its supplied equipment source

#### Scenario: Same-definition instances disclose distinct sources
- **WHEN** attached and independent buff instances share a condition code but have different durations and provenance
- **THEN** both rows remain readable and focusing or hovering either row discloses that row's source and duration, including when one or both are in overflow

#### Scenario: Independent source remains explicit for a mixed row
- **WHEN** a condition has mixed provenance naming two synthetic worn contributors
- **THEN** its detail identifies both supplied item labels and an independent source without downgrading the adverse severity

#### Scenario: Detail works when the character panel is unavailable
- **WHEN** combat reveals the dock and status supplies equipment provenance while the character panel is unavailable
- **THEN** condition detail still uses the status-supplied source labels and invents no equipment data from the unavailable panel
