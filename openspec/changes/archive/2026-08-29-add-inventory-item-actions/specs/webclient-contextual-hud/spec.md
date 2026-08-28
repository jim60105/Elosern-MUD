## MODIFIED Requirements

### Requirement: The bag renders the bounded inventory rows without inventing a total or a rarity
The bag drawer SHALL use the shared drawer chrome for the `背包 · 裝備` title, local inventory SVG icon, close control, and wallet subtitle formatted as integer copper from the committed available character panel. The wallet SHALL additionally render exactly once in the drawer body as the single row of a `金錢` section. The available body SHALL remain the redesign's unwrapped three-section stack: an `裝備` section carrying the read-only equipment doll, an `物品` section whose heading carries the shipped listing size above the bounded responsive grid, and a `金錢` section carrying the same committed wallet. The listing SHALL remain bounded by the server row ceiling and state that ceiling in words when reached; no shipped count SHALL claim to be the player's untruncated holdings.

Each registered row's non-null `presentation` SHALL select one local inline SVG by `icon_key`, an item-kind label, rarity label, bounded summary, and non-colour-only rarity treatment. Its tile SHALL show committed held count and a non-colour equipped marker. A null presentation SHALL render only the neutral unknown-item SVG and visible unknown marker; the browser SHALL NOT derive type, icon, rarity, summary, or mechanics from item key or display name. The grid SHALL use native keyboard-focusable buttons and one non-focusable inspector shared by pointer hover and keyboard focus; both inspection paths SHALL expose identical committed name, kind, rarity, count, equipped state, and summary, and the focused tile SHALL reference the stable inspector through `aria-describedby`.

Each tile SHALL follow only its committed nullable action descriptor. Inspect-only and unknown tiles SHALL dispatch nothing. Disabled tiles SHALL remain keyboard reachable, expose `aria-disabled`, and show the committed reason on activation without dispatch. Enabled usable items SHALL open a labelled, focus-trapped inventory-use confirmation; enabled equipment SHALL dispatch its toggle immediately. Selection and dialog state SHALL remain client-local and reset on panel replacement, drawer close, mode/epoch change, or transport loss. The bag SHALL NOT render or infer numeric item statistics, recovery amounts, conditions, effects, consumable flags, slots, set bonuses, comparisons, sorting, filtering, search, drag, or drop behavior, and SHALL render no static sort/filter/search pill.

The drawer SHALL remain available from its combat affordance when services v3 inventory is available. When services commits its unavailable form or inventory is absent, the bag SHALL render only the registered reason and fabricate no wallet, equipment, row, count, action, or dialog. When services inventory is available but character is unavailable, the grid SHALL remain available, the doll SHALL render its registered unavailable state, and no wallet subtitle, wallet body value, or zero balance SHALL be invented. All inspector, confirmation, and warning transitions SHALL use existing motion tokens so reduced motion makes them effectively instant.

#### Scenario: A registered actionable row preserves truthful inspection
- **WHEN** a committed registered inventory row carries presentation and an enabled action descriptor
- **THEN** its tile renders committed visual identity and inspector data, and deliberate activation follows the descriptor without deriving mechanics locally

#### Scenario: An unknown row has a neutral truthful fallback
- **WHEN** a committed inventory row has `presentation` null and `action` null
- **THEN** its tile shows the neutral unknown state and real quantity with no inferred metadata or mutation

#### Scenario: Keyboard inspection and activation match pointer behavior
- **WHEN** keyboard and pointer users inspect and activate the same tile
- **THEN** both receive identical committed inspector data and action behavior, and the focused tile references the inspector through `aria-describedby`

#### Scenario: Eligible item use opens confirmation
- **WHEN** the player activates an enabled usable-item tile
- **THEN** the labelled confirmation dialog opens without dispatch and confirm is the only path that submits use

#### Scenario: Equipment activates directly
- **WHEN** the player activates an enabled equipment tile
- **THEN** one equipment-toggle intent is emitted without opening a confirmation

#### Scenario: Disabled item presents its reason
- **WHEN** the player activates a full-HP potion or an unequipped accessory at the five-slot cap
- **THEN** the committed reason is presented and no request is dispatched

#### Scenario: Combat bag keeps personal items reachable
- **WHEN** mode changes to active combat and services v3 commits canonical inventory
- **THEN** the combat root's client-local `背包` row opens the frameless bag without dispatch or a router frame, and personal item tiles remain reachable while guild and shop surfaces are absent

#### Scenario: The bag body retains the three-section stack
- **WHEN** the bag is available with inventory, character equipment, and wallet
- **THEN** it renders equipment, items, and money in order without a bordered panel-card wrapper or invented total

#### Scenario: Wallet renders only in the bag head and money row
- **WHEN** the bag renders with available character and inventory panels
- **THEN** the same integer copper wallet appears in the head subtitle and the single `金錢` row and nowhere else in the drawer

#### Scenario: Ceiling is stated without inventing a total
- **WHEN** the shipped inventory reaches its maximum row count
- **THEN** the bag states the listing ceiling and never labels that count as complete holdings

#### Scenario: Unavailable services fabricates nothing
- **WHEN** the services panel commits its unavailable form
- **THEN** the bag renders only the registered reason with no rows, wallet, equipment, count, heading, action, or dialog

#### Scenario: Character unavailability preserves inventory without fabricating equipment
- **WHEN** services inventory is available but the character panel is unavailable
- **THEN** the bag renders held tiles, the equipment registered unavailable reason, and no wallet subtitle, wallet value, or zero balance

#### Scenario: Reduced motion preserves action information
- **WHEN** reduced motion is active and focus, inspector, confirmation, or warning state changes
- **THEN** transitions are effectively instant while labels, reasons, focus, and committed item information remain available
