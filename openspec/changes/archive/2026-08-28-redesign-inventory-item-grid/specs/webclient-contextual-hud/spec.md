## MODIFIED Requirements

### Requirement: The bag renders the bounded inventory rows without inventing a total or a rarity
The bag drawer SHALL use the shared drawer chrome for the `背包 · 裝備` title, local `inventory` SVG icon, close control, and a wallet subtitle formatted as integer copper from the committed available `character` panel. It SHALL render that wallet in no other body location. Its available body SHALL begin with the read-only equipment doll built from the committed `character` panel's equipment rows, followed by a bounded responsive grid of the committed `services` panel's inventory rows. The listing SHALL remain bounded by the server's row ceiling; when it holds that many rows the drawer SHALL state the ceiling in words. The shipped row count SHALL NOT be presented as a count of the player's untruncated holdings, because the panel's inventory total is that same shipped count and carries no information about what was truncated.

Each registered row's non-null `presentation` object SHALL select one local inline SVG by `icon_key`, an item-kind label, a rarity label, a bounded summary, and a rarity border treatment. Its tile SHALL show the committed held count in a stable lower corner and a non-colour equipped check marker when equipped. Rarity SHALL use a distinct border pattern as well as its colour, and the focused or hovered inspector SHALL spell the rarity word. A null `presentation` SHALL render only the neutral unknown-item SVG and visible unknown marker; the browser SHALL NOT derive type, icon, rarity, or summary from `item_key` or `display_name`. The grid SHALL use native keyboard-focusable buttons and one non-focusable inspector shared by pointer hover and keyboard focus; both paths SHALL expose the same committed display name, kind, rarity, held count, equipped state, and summary. The currently focused tile SHALL use `aria-describedby` to reference that inspector's stable ID, and the relationship SHALL clear when no inspector is present. Selection SHALL be client-local, reset on panel replacement, and SHALL dispatch no action.

The bag SHALL NOT render a numeric item statistic, recovery amount, requirement, set bonus, comparison value, sorting, filtering, search, use, consume, equip, drag, or drop control. When the `services` panel commits its unavailable form, or when its inventory section is absent, the bag SHALL render only the registry-owned reason and SHALL fabricate no wallet, equipment slot, row or count. When services are available but the character panel is unavailable, the held-item grid remains available, the doll renders its registered unavailable state, and the drawer header renders no balance. Any cell or inspector transition SHALL use existing motion tokens so the reduced-motion setting makes it effectively instant.

#### Scenario: A registered row renders as an inspectable inventory tile
- **WHEN** a committed inventory row carries valid non-null presentation metadata
- **THEN** its native button renders the mapped local SVG, lower-corner held count, rarity border pattern and colour, equipped check when applicable, and the identical committed metadata in its hover and focus inspector without dispatching an action

#### Scenario: An unknown row has a neutral truthful fallback
- **WHEN** a committed inventory row has `presentation` null
- **THEN** its tile shows the neutral unknown-item SVG and unknown marker with its real name and held count, and no inferred kind, rarity, icon, summary, numeric value, or action control

#### Scenario: Keyboard inspection matches pointer inspection
- **WHEN** a keyboard user focuses an inventory tile that a pointer user can hover
- **THEN** both users receive the same real name, kind, rarity word, held count, equipped state, and summary without the inspector entering the tab order, and the focused tile references the inspector through `aria-describedby`

#### Scenario: The ceiling is stated, the total is not invented
- **WHEN** the inventory listing holds the server's maximum number of rows
- **THEN** the drawer states that the listing is bounded at that maximum, and it never renders a figure claiming to be the player's complete holdings

#### Scenario: No state-changing control appears
- **WHEN** the bag renders a held item, whether equipped or not
- **THEN** it offers no use, consume, equip, drag, drop, sort, filter, or search control

#### Scenario: An unavailable services panel fabricates nothing
- **WHEN** the `services` panel commits its unavailable form
- **THEN** the bag renders only the registry-owned reason message, with no rows, wallet, equipment slot or count

#### Scenario: Character unavailability does not fabricate a balance or equipment
- **WHEN** the services inventory is available and the character panel is unavailable
- **THEN** the bag renders its held grid, renders the equipment section's registered unavailable reason, and shows no wallet subtitle or zero balance

#### Scenario: The reduced-motion setting preserves information
- **WHEN** the reduced-motion preference is active and an inventory tile gains focus or an inspector changes row
- **THEN** the transition is effectively instant while all tile, rarity, count, equipped, and inspector information remains visible
