## MODIFIED Requirements

### Requirement: The gallery has an offline interactive storyboard
The gallery component Storybook families SHALL include an interactive storyboard
under Overlays/GalleryWindow covering category switching, browse, generation, pending and failure, binding, face editing,
stage transform editing/reset/save/rejection, default selection and delete confirmation.

#### Scenario: The storyboard runs without game or AI services
- **WHEN** the player opens the built Storybook gallery storyboard offline
- **THEN** the real components expose every documented frame with deterministic fixtures and no game-server or AI-service requests

#### Scenario: Context changes invalidate an editor
- **WHEN** the selected subject changes, its card disappears or the panel becomes unavailable
- **THEN** stale drafts are discarded and cannot dispatch against the replacement context

#### Scenario: An unrelated pending job does not complete a submission
- **WHEN** another pending row is published before this editor's correlated result
- **THEN** the editor remains open and a rejected result preserves its draft

#### Scenario: The frame guide documents the journey
- **WHEN** the storyboard's frame guide is inspected
- **THEN** it references the four existing design images, states each transition and recovery path, and distinguishes fixture publications from live behavior

#### Scenario: The stage editor reuses local assets
- **WHEN** the storyboard stages its stage-editor frames
- **THEN** it reuses existing local assets without requiring a new reference image


### Requirement: Official entries render as selectable read-only rows with personal geometry affordances

The gallery surface SHALL render the committed `official_entries` beside the
card rows as selectable, previewable rows and, when the committed
`supports_personal_official_preferences` flag is true, SHALL offer exactly the official-entry
affordances 設為預設 (清除選取 while current), 臉框, 舞台位置 and 清除個人調整, gated by the declared geometry facts. Delete, replace, and
regenerate-overwrite affordances SHALL NOT be rendered for an official entry, and the surface SHALL
compose no official fact locally.

#### Scenario: An official row offers selection and geometry only

- **WHEN** a committed official row whose `is_current` is true is selected in the surface
- **THEN** the surface previews that committed URL, offers 清除選取 instead of 設為預設, and renders no 刪除, replace, or regenerate affordance

#### Scenario: A geometry edit dispatches only the edited component

- **WHEN** the player saves a face-rectangle edit for a committed official identity
- **THEN** exactly one `gallery.official.geometry.set` carries `{subject_key, identity, face_rect}` and no `stage` value, so the stored stage override for that identity is untouched

#### Scenario: Official rows never reach the card grid

- **WHEN** a payload carries three official rows and two card rows
- **THEN** the card grid renders exactly the two card rows and the official rows render separately as read-only entries

#### Scenario: Official row facts come verbatim from the payload

- **WHEN** an official row renders
- **THEN** its image URL, rectangle facts, and current/catalog-default markers come verbatim from the committed payload

#### Scenario: Selection and clearing dispatch the committed identity

- **WHEN** the player activates 設為預設 or 清除選取 on an official row
- **THEN** the dispatch is exactly one `gallery.official.select` or `gallery.official.clear_selection` carrying that row's committed identity

#### Scenario: Geometry edits touch only the edited component

- **WHEN** the player uses 臉框 or 舞台位置 on an official row
- **THEN** each dispatches one `gallery.official.geometry.set` carrying only the edited component for that committed identity, so the component the player did not touch stays exactly as the server stores it

#### Scenario: Personal-geometry clearing has its own action

- **WHEN** the player activates 清除個人調整 on an official row
- **THEN** the dispatch is exactly one `gallery.official.geometry.clear`

#### Scenario: Hiding destructive affordances is not the guarantee

- **WHEN** an official entry hides its delete, replace, and regenerate-overwrite affordances
- **THEN** the client's hiding SHALL never be the guarantee, because the backend refuses every such request independently

#### Scenario: Official rows stay out of the card filter counts

- **WHEN** the surface counts or lists card rows
- **THEN** official rows SHALL NOT be counted or listed as card rows

#### Scenario: Species previews preserve generation while declining personal writes
- **WHEN** a registered visual-species gallery row carries supports_personal_official_preferences false
- **THEN** its runtime generation, shared default selection and placement controls remain available according to existing capabilities, and official images are previewable with no personal selection or geometry controls

#### Scenario: Official-only artwork suppresses empty-card guidance
- **WHEN** an available committed gallery panel has three `official_entries` and zero card rows
- **THEN** the three official entries remain available in the tray and the page shows an official entry, not the no-image page
- **AND** the decision uses only the committed official-entry list length, without a new payload field or client-composed official fact

#### Scenario: Empty filters with official rows do not claim missing artwork
- **WHEN** committed `official_entries` is non-empty and the selected subject has zero card rows
- **THEN** the no-image page is not shown and the official entries remain selectable

#### Scenario: Empty-card guidance remains unchanged without official entries
- **WHEN** the selected subject has zero card rows and committed `official_entries` is an empty list
- **THEN** the page shows the no-image state with the 生成新圖 action

#### Scenario: Committed official-entry replacement updates guidance
- **WHEN** zero visible card rows remain and a committed panel replacement changes `official_entries` from non-empty to empty or from empty to non-empty
- **THEN** the no-image state appears or disappears respectively from that committed list alone, without an action dispatch or local official-entry inference

## REMOVED Requirements

### Requirement: The detail rail presents the selected card and gates destructive intent
**Reason**: `GalleryDetailRail.vue` is deleted; the selected image is presented by the gallery image page (design D5, D7).
**Migration**: Covered by `webclient-gallery-image-page` (footer, two-step deletion, facts); retarget tests there.
