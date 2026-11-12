## MODIFIED Requirements

### Requirement: Official entries render as selectable read-only rows with personal geometry affordances

The gallery surface SHALL render the committed `official_entries` beside the
card rows as selectable, previewable rows and, when the committed
`supports_personal_official_preferences` flag is true, SHALL offer exactly the official-entry
affordances 選為預設影像, 清除選取, 臉部框選, 比例調整 and 清除個人調整. Delete, replace, and
regenerate-overwrite affordances SHALL NOT be rendered for an official entry, and the surface SHALL
compose no official fact locally.

#### Scenario: An official row offers selection and geometry only

- **WHEN** a committed official row whose `is_current` is true is selected in the surface
- **THEN** the surface previews that committed URL, offers 清除選取 instead of 選為預設影像, and renders no 刪除, replace, or regenerate affordance

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

- **WHEN** the player activates 選為預設影像 or 清除選取 on an official row
- **THEN** the dispatch is exactly one `gallery.official.select` or `gallery.official.clear_selection` carrying that row's committed identity

#### Scenario: Geometry edits touch only the edited component

- **WHEN** the player uses 臉部框選 or 比例調整 on an official row
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
- **WHEN** an available committed gallery panel has three `official_entries` and zero visible card rows
- **THEN** the three official rows remain available and no `gallery-panel__empty` paragraph is rendered inside the cards area
- **AND** the decision uses only the committed official-entry list length, without a new payload field or client-composed official fact

#### Scenario: Empty filters with official rows do not claim missing artwork
- **WHEN** committed `official_entries` is non-empty and the selected subject has zero card rows
- **THEN** `gallery-panel__empty` is absent and the separate official rows remain visible

#### Scenario: Empty-card guidance remains unchanged without official entries
- **WHEN** the selected subject has zero card rows and committed `official_entries` is an empty list
- **THEN** the existing paragraph remains inside the cards area with class `gallery-panel__empty`

#### Scenario: Committed official-entry replacement updates guidance
- **WHEN** zero visible card rows remain and a committed panel replacement changes `official_entries` from non-empty to empty or from empty to non-empty
- **THEN** the existing guidance appears or disappears respectively from that committed list alone, without an action dispatch or local official-entry inference


## ADDED Requirements

### Requirement: The gallery surface renders committed categories, subjects and rows
The gallery surface SHALL render, from the committed `gallery` panel only, one control per committed category (disabled categories focusable and announcing their committed reason), the selected category's committed groups and subjects, and the selected subject's rows, chips, crown, pending and failed states verbatim. It SHALL render no filter tabs, compose no chips or labels and re-sort nothing.

#### Scenario: A category press dispatches and waits for the panel
- **WHEN** an enabled category control other than the committed `category` is activated
- **THEN** exactly one `gallery.category.select` dispatch carries that key and the subjects shown change only when the new committed panel arrives

#### Scenario: A disabled category announces its reason and sends nothing
- **WHEN** a committed category with `enabled: false` is focused and activated
- **THEN** its committed reason is exposed to assistive technology and no action is dispatched

#### Scenario: Subject selection dispatches and waits for the panel
- **WHEN** a listed subject is activated
- **THEN** exactly one `gallery.subject.select` dispatch carries that committed subject key, and the surface re-renders only when the new committed panel arrives

#### Scenario: A failed row renders the committed failure line
- **WHEN** a row carries status `failed` with the committed zh-TW message
- **THEN** the card shows that message verbatim and no image element, and the surface remains usable

#### Scenario: Dates derive only from the structured created_at
- **WHEN** a row's date is presented
- **THEN** it is a localized relative time from `created_at` alone, with the exact local date and time available to assistive technology and on hover, and an unusable value reads 日期不詳

#### Scenario: Mutation gates follow panel availability
- **WHEN** the committed panel is unavailable
- **THEN** the surface locks every mutation control

## REMOVED Requirements

### Requirement: The gallery surface renders only committed panel facts
**Reason**: The subject rail and the filter tabs are removed with the version-4 panel (design D6, D7).
**Migration**: Replaced by "The gallery surface renders committed categories, subjects and rows"; retarget its tests and drop filter-tab tests.
