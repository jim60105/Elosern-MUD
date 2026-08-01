## MODIFIED Requirements

### Requirement: Inventory remains a flat list of item-key strings behind one deterministic planning boundary
The read-only `world/skills/equipment.py` SHALL define `list_items(entity)`. The mutating
`world/rules/equipment.py` SHALL define `plan_inventory_delta(entity, additions=(), removals=())`,
`apply_inventory_plan(plan)`, and convenience `add_item(entity, item_key)` / `remove_item(entity,
item_key)` operations over `entity.db.inventory`, the same flat repeated-key list populated by the import
loader. Gameplay mutations SHALL validate item keys and positive integer quantities and SHALL use the
planner. Import construction MAY populate the initial raw list without emitting acquisition progress.

#### Scenario: add_item appends through an inventory plan
- **WHEN** `entity.db.inventory` is `["healing_potion"]` and `add_item(entity, "iron_ore")` is called
- **THEN** the committed inventory becomes `["healing_potion", "iron_ore"]`

#### Scenario: add_item tolerates an entity with no inventory yet
- **WHEN** `entity.db.inventory` is `None` and `add_item(entity, "healing_potion")` is called
- **THEN** the committed inventory becomes `["healing_potion"]` rather than raising

#### Scenario: remove_item removes exactly one matching entry
- **WHEN** `entity.db.inventory` is `["healing_potion", "iron_ore"]` and `remove_item(entity,
  "iron_ore")` is called
- **THEN** the committed inventory becomes `["healing_potion"]`

#### Scenario: insufficient removal fails before mutation
- **WHEN** a plan requests removal of two potions but inventory contains one
- **THEN** planning raises a named inventory error and the raw list is unchanged

#### Scenario: list_items reflects change 4's already-populated inventory verbatim
- **WHEN** an entity was constructed by change 4's `instantiate_character()` with a non-empty
  `inventory` array
- **THEN** `list_items(entity)` returns that same array's contents, unmodified

## ADDED Requirements

### Requirement: Inventory plans compose with larger atomic operations
An InventoryPlan SHALL expose complete before/after item lists and positive additions without applying
them. Reward and shop operations SHALL be able to combine its inventory write and computed ACQUIRE
quest-log replacement with wallet, merit, claims, or merchant-stock effects in one outer transaction.
`apply_inventory_plan()` used alone SHALL provide its own atomic transaction and cache restoration.

#### Scenario: Planning has no side effects
- **WHEN** a valid additions/removals plan is created but not applied
- **THEN** inventory and quest log remain byte-for-byte unchanged

#### Scenario: Outer transaction owns composed commit
- **WHEN** a shop purchase composes an InventoryPlan with wallet and stock replacements
- **THEN** inventory is written exactly once inside the shop transaction rather than committed early

#### Scenario: Standalone application restores cache on failure
- **WHEN** a standalone plan's inventory or ACQUIRE quest-log write is fault-injected to fail
- **THEN** database and in-process inventory/quest-log values equal their pre-application state
