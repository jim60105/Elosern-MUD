## ADDED Requirements

### Requirement: Official entries render as selectable read-only rows with personal geometry affordances

The gallery surface SHALL render the committed `official_entries` beside the
card rows as selectable, previewable rows whose image URL, rectangle facts, and
current/catalog-default markers come verbatim from the payload, and SHALL offer
exactly the official-entry affordances 選為預設影像 (`gallery.official.select`
carrying that row's committed identity), 清除選取 (`gallery.official.clear_selection`),
臉部框選 and 比例調整 (each dispatching one `gallery.official.geometry.set`
carrying only the edited component for that committed identity, so the
component the player did not touch stays exactly as the server stores it), and
清除個人調整 (`gallery.official.geometry.clear`). Delete, replace, and
regenerate-overwrite affordances SHALL NOT be rendered for an official entry;
the client's hiding SHALL never be the guarantee, because the backend refuses
every such request independently. The surface SHALL NOT compose any official
fact locally: the identity, URL, rectangle, and both markers are committed
payload values, and official rows SHALL NOT be counted by the card filter tabs.

#### Scenario: An official row offers selection and geometry only

- **WHEN** a committed official row whose `is_current` is true is selected in the surface
- **THEN** the surface previews that committed URL, offers 清除選取 instead of 選為預設影像, and renders no 刪除, replace, or regenerate affordance

#### Scenario: A geometry edit dispatches only the edited component

- **WHEN** the player saves a face-rectangle edit for a committed official identity
- **THEN** exactly one `gallery.official.geometry.set` carries `{subject_key, identity, face_rect}` and no `stage` value, so the stored stage override for that identity is untouched

#### Scenario: Official rows never reach the card grid

- **WHEN** a payload carries three official rows and two card rows
- **THEN** the card grid renders exactly the two card rows, the filter tabs keep the committed card counts, and the official rows render separately as read-only entries
