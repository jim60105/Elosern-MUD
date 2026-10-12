# Spec Delta

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
- **THEN** the card grid renders exactly the two card rows, the filter tabs keep the committed card counts, and the official rows render separately as read-only entries

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

- **WHEN** the card filter tabs compute their counts
- **THEN** official rows SHALL NOT be counted by the card filter tabs

#### Scenario: Species previews preserve generation while declining personal writes
- **WHEN** a registered visual-species gallery row carries supports_personal_official_preferences false
- **THEN** its runtime generation, shared default selection and placement controls remain available according to existing capabilities, and official images are previewable with no personal selection or geometry controls

#### Scenario: Official-only artwork suppresses empty-card guidance
- **WHEN** an available committed gallery panel has three `official_entries` and zero visible card rows
- **THEN** the three official rows remain available and no `gallery-panel__empty` paragraph is rendered inside the cards area
- **AND** the decision uses only the committed official-entry list length, without a new payload field or client-composed official fact

#### Scenario: Empty filters with official rows do not claim missing artwork
- **WHEN** committed `official_entries` is non-empty and the player selects any card filter with zero matching visible card rows, including all, defaults, bound, pending or failed
- **THEN** `gallery-panel__empty` is absent on that tab, the separate official rows remain visible, and committed card filter counts remain unchanged

#### Scenario: Empty-card guidance remains unchanged without official entries
- **WHEN** the selected card filter has zero visible card rows and committed `official_entries` is an empty list
- **THEN** the existing paragraph remains inside the cards area with class `gallery-panel__empty` and text `此分類尚無肖像。選擇「生成新圖」，記錄角色的模樣。`
- **AND** this holds for an empty subject and a filter with no matches on a subject that has other card rows

#### Scenario: Committed official-entry replacement updates guidance
- **WHEN** zero visible card rows remain and a committed panel replacement changes `official_entries` from non-empty to empty or from empty to non-empty
- **THEN** the existing guidance appears or disappears respectively from that committed list alone, without an action dispatch or local official-entry inference
