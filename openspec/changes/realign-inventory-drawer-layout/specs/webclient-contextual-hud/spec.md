# webclient-contextual-hud — delta

## MODIFIED Requirements

### Requirement: The bag renders the bounded inventory rows without inventing a total or a rarity
The bag drawer SHALL use the shared drawer chrome for the `背包 · 裝備` title, local `inventory` SVG icon, close control, and a wallet subtitle formatted as integer copper from the committed available `character` panel. The wallet SHALL additionally render exactly once in the drawer body, as the single row of a `金錢` section, and in no other body location. Its available body SHALL be the redesign's three-section stack rendered directly on the drawer body without a panel-card wrapper: an `裝備` section carrying the read-only equipment doll built from the committed `character` panel's equipment rows, an `物品` section whose heading carries the shipped listing size as its tag and whose body carries the bounded responsive grid of the committed `services` panel's inventory rows, and a `金錢` section rendering the committed wallet as one labelled row with grouped integer copper. The listing SHALL remain bounded by the server's row ceiling; when it holds that many rows the drawer SHALL state the ceiling in words. The `物品` tag and the shipped row count label only the shipped listing size and SHALL NOT be presented as a count of the player's untruncated holdings, because the panel's inventory total is that same shipped count and carries no information about what was truncated.

Each registered row's non-null `presentation` object SHALL select one local inline SVG by `icon_key`, an item-kind label, a rarity label, a bounded summary, and a rarity border treatment. Its tile SHALL show the committed held count in a stable lower corner and a non-colour equipped check marker when equipped. Rarity SHALL use a distinct border pattern as well as its colour, and the focused or hovered inspector SHALL spell the rarity word. A null `presentation` SHALL render only the neutral unknown-item SVG and visible unknown marker; the browser SHALL NOT derive type, icon, rarity, or summary from `item_key` or `display_name`. The grid SHALL use native keyboard-focusable buttons and one non-focusable inspector shared by pointer hover and keyboard focus; both paths SHALL expose the same committed display name, kind, rarity, held count, equipped state, and summary. The currently focused tile SHALL use `aria-describedby` to reference that inspector's stable ID, and the relationship SHALL clear when no inspector is present. Selection SHALL be client-local, reset on panel replacement, and SHALL dispatch no action.

The bag SHALL NOT render a numeric item statistic, recovery amount, requirement, set bonus, comparison value, sorting, filtering, search, use, consume, equip, drag, or drop control; the redesign mock's static 排序/篩選/找尋 pills SHALL NOT be reproduced because the payload carries no ordering or filter state. When the `services` panel commits its unavailable form, or when its inventory section is absent, the bag SHALL render only the registry-owned reason and SHALL fabricate no wallet, equipment slot, row or count. When services are available but the character panel is unavailable, the held-item grid remains available, the doll renders its registered unavailable state, and the drawer header renders no balance and the body renders no `金錢` row. Any cell or inspector transition SHALL use existing motion tokens so the reduced-motion setting makes it effectively instant.

#### Scenario: A registered row renders as an inspectable inventory tile
- **WHEN** a committed inventory row carries valid non-null presentation metadata
- **THEN** its native button renders the mapped local SVG, lower-corner held count, rarity border pattern and colour, equipped check when applicable, and the identical committed metadata in its hover and focus inspector without dispatching an action

#### Scenario: An unknown row has a neutral truthful fallback
- **WHEN** a committed inventory row has `presentation` null
- **THEN** its tile shows the neutral unknown-item SVG and unknown marker with its real name and held count, and no inferred kind, rarity, icon, summary, numeric value, or action control

#### Scenario: Keyboard inspection matches pointer inspection
- **WHEN** a keyboard user focuses an inventory tile that a pointer user can hover
- **THEN** both users receive the same real name, kind, rarity word, held count, equipped state, and summary without the inspector entering the tab order, and the focused tile references the inspector through `aria-describedby`

#### Scenario: The bag body is the redesign's three-section stack
- **WHEN** the bag is available with at least one inventory row and a committed wallet
- **THEN** the body renders, in order, the `裝備` section (the doll), an `物品` heading tagged with the shipped listing size over the tile grid, and a `金錢` section whose single row shows the grouped integer copper wallet; none of these sections is wrapped in its own bordered panel card

#### Scenario: The wallet renders in the head and in the 金錢 section only
- **WHEN** the bag renders with an available character panel and an available inventory section
- **THEN** the integer copper wallet appears in the head subtitle and in the `金錢` section row, and in no other element of the drawer

#### Scenario: The ceiling is stated, the total is not invented
- **WHEN** the inventory listing holds the server's maximum number of rows
- **THEN** the drawer states that the listing is bounded at that maximum, and it never renders a figure claiming to be the player's complete holdings

#### Scenario: No state-changing control appears
- **WHEN** the bag renders a held item, whether equipped or not
- **THEN** it offers no use, consume, equip, drag, drop, sort, filter, or search control, and renders no static sort/filter/search pill

#### Scenario: An unavailable services panel fabricates nothing
- **WHEN** the `services` panel commits its unavailable form
- **THEN** the bag renders only the registry-owned reason message, with no rows, wallet, equipment slot, count, `物品` heading, or `金錢` row

#### Scenario: Character unavailability does not fabricate a balance or equipment
- **WHEN** the services inventory is available and the character panel is unavailable
- **THEN** the bag renders its held grid, renders the equipment section's registered unavailable reason, and shows no wallet subtitle, no wallet value, and no zero balance

#### Scenario: The reduced-motion setting preserves information
- **WHEN** the reduced-motion preference is active and an inventory tile gains focus or an inspector changes row
- **THEN** the transition is effectively instant while all tile, rarity, count, equipped, and inspector information remains visible

### Requirement: The equipment doll renders only server-authored slots and drops nothing
The equipment presentation SHALL be built from the committed `character` panel's equipment rows, each of which carries a slot, an item key and a display name and nothing more. The section SHALL be introduced by the bag's small tracked section heading `裝備` carrying the right-aligned tag `真值 · 偽裝不影響`, and SHALL NOT be introduced by a standalone `裝備人偶` title. The doll SHALL lay out as the redesign's equipment row: a compact two-column square slot grid beside a 裝備描述 column that lists the committed rows grouped under their slot labels. The doll SHALL render the server's three singleton slots and one accessory summary as four named positions in the square grid. The main-hand, armor, and accessory-summary positions SHALL each render a fixed local SVG selected by its server-authored slot role; the off-hand position SHALL be the iconless position. The doll SHALL NOT select an item icon from an item key or display name. A singleton slot with no row SHALL render a visible named empty state with a dashed outline. An occupied singleton slot SHALL render its visible slot label in the grid and its committed display name in the 裝備描述 column; when the committed rows carry more than one row for a recognised singleton slot, the square position consumes only the first row and every further row for that slot SHALL render as a labelled overflow row, so no committed row is lost. The accessory summary SHALL render its visible label and committed item count, while every repeatable accessory row SHALL render in the 裝備描述 column's accessory group. Any slot key outside the recognised set SHALL render as a labelled fallback row rather than being discarded, so no row the payload sends is lost. When the committed rows carry no equipment at all the doll SHALL render only its visible empty statement.

The doll SHALL NOT render an item statistic, attack or defence value, rarity, item icon, summary, or comparison against another item: the equipment rows carry none of those. Equipment SHALL be presented as true values that a disguise does not affect, and the section tag SHALL state exactly that.

#### Scenario: The equipment section is titled 裝備 with the true-value tag
- **WHEN** the bag renders its equipment section
- **THEN** the section heading reads `裝備` with the tag `真值 · 偽裝不影響` in the bag's shared section-heading style, and the string `裝備人偶` appears nowhere in the drawer

#### Scenario: An empty slot is shown as empty
- **WHEN** the committed equipment rows carry no row for a singleton slot
- **THEN** that slot renders its visible name with a dashed explicit empty state, and no item is invented for it

#### Scenario: An occupied singleton slot is identified without guessing its item type
- **WHEN** the committed equipment rows carry one primary-hand item
- **THEN** the square grid renders only that position's fixed slot SVG and visible slot name, the 裝備描述 column renders its committed display name under the `主手` label, and nothing is inferred about the item's icon, rarity, statistic, or comparison

#### Scenario: An occupied off-hand position renders without an item icon
- **WHEN** the committed equipment rows carry a `weapon_off` item
- **THEN** the off-hand position stays the iconless position of the binding design, rendering its visible slot label in the grid and its committed display name in the 裝備描述 column with no item icon

#### Scenario: The description column lists only committed rows
- **WHEN** the committed equipment rows carry equipment
- **THEN** the 裝備描述 column shows exactly one labelled entry per committed row (slot label plus committed display name), grouped by slot, and with no committed row it shows only the visible empty statement

#### Scenario: Duplicate singleton rows are rendered, not discarded
- **WHEN** the committed equipment rows carry more than one row for a recognised singleton slot
- **THEN** the square position shows the first row for that slot and every additional row renders as a labelled overflow row, so the duplicate committed row is never dropped

#### Scenario: Repeated accessories all render
- **WHEN** the committed equipment rows carry more than one accessory row
- **THEN** the accessory summary states the committed count and every accessory row renders in the description column's accessory group, and none is dropped for want of a fixed position

#### Scenario: An unrecognised slot is rendered, not discarded
- **WHEN** an equipment row carries a slot key outside the recognised set
- **THEN** the row renders with its slot key as its label and its display name, and the doll drops no row

#### Scenario: No statistics are invented for an equipped item
- **WHEN** an equipped item renders in the doll
- **THEN** it shows its display name and its slot only, with no attack, defence, rarity, item icon, summary, or comparison value

### Requirement: The drawer layer renders the wallet exactly once
Across every drawer, the player's wallet SHALL be rendered exactly once per opening of the inventory drawer — once in its shared header subtitle and once as the single row of its `金錢` body section, both read from the committed available panel that owns the value — and nowhere else in the drawer layer. The shop, the lore reference, the character-status drawer, and every other body element of the inventory drawer SHALL NOT render a balance of their own. A drawer that cannot read the wallet from an available character panel (or, for the body row, from an available inventory section carrying a committed non-negative integer wallet) SHALL render no balance at all rather than a zero.

#### Scenario: One wallet per drawer-layer opening
- **WHEN** every drawer is opened in turn with the `services` and `character` panels available
- **THEN** the only wallet values rendered across all of them are the inventory drawer's header subtitle and its `金錢` section row, both carrying the same integer copper value, and no other drawer or body element renders a balance

#### Scenario: An unavailable panel renders no balance
- **WHEN** the character panel that carries the wallet is unavailable
- **THEN** no drawer renders a balance, and none renders a zero in its place

#### Scenario: A missing wallet field renders no body row
- **WHEN** the inventory section is available but carries no committed non-negative integer wallet
- **THEN** the `金錢` section renders no balance row while the header subtitle keeps whatever the available character panel legitimately carries
