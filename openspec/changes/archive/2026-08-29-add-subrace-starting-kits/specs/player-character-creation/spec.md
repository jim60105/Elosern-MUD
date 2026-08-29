# player-character-creation delta for add-subrace-starting-kits

## MODIFIED Requirements

### Requirement: Preset activation grants the preset's declared starting inventory
Preset mode SHALL additionally grant the selected preset's declared starting inventory: the
activated character's `inventory` SHALL equal the preset's `(item_key, quantity)` pairs flattened
into the flat repeated-key list shape in declared order, written inside the same all-or-nothing
activation transaction. A preset's declared inventory SHALL NOT be overridden by the chosen
subrace's basic starting kit. Custom mode SHALL instead start with the chosen subrace's basic
starting kit as defined by the `Custom activation grants the chosen subrace's basic starting kit`
requirement. A starting kit SHALL reference only keys that exist in `ITEM_REGISTRY`, with a
positive integer quantity per key and no repeated key — an invalid kit SHALL fail at registry
load, never at player activation. Starting items are granted unequipped; the player equips them
through the ordinary equipment surface.

#### Scenario: A preset activation grants the declared starting items
- **WHEN** a pending player activates a shipped preset that declares `starting_items`
- **THEN** the activated character's `db.inventory` equals the declared pairs flattened by
  quantity in declared order, written atomically with the rest of the activation state, and the
  preset's subrace basic starting kit grants nothing extra

#### Scenario: Custom activation starts with its subrace kit
- **WHEN** a pending player completes the custom creation flow with a registered subrace
- **THEN** the activated character's `db.inventory` equals that subrace's basic starting kit
  flattened by quantity, never the empty list

#### Scenario: A preset kit with a registry-invalid item is rejected at load
- **WHEN** a preset declares an item key absent from `ITEM_REGISTRY`, a non-positive or
  non-integer quantity, or the same item key twice
- **THEN** importing `world.lore.player_presets` raises, so the invalid kit can never reach a
  player's activation

## ADDED Requirements

### Requirement: Every subrace has a validated basic starting equipment kit in the item catalog
Every subrace registered in `SUBRACE_REGISTRY` SHALL have a basic starting kit: a non-empty set of
item keys that all exist in `ITEM_REGISTRY` and all denote equipment — every kit item SHALL declare
an `equipment_slot`, so consumables and inspect-only items can never compose a kit. Because every
subrace has a kit, every registered race SHALL likewise have fitting basic starting equipment
available to its players. The kit mapping SHALL live in an immutable lore registry keyed by
subrace, validated at registry load time: a subrace without a kit, a kit referencing an unknown or
non-equipment item key, a duplicated item key within one kit, an empty kit, or a non-positive
quantity SHALL fail at load, before any activation can observe the registry. One item key MAY
appear in any number of subrace kits (basic gear is a shared catalog pool, not a per-subrace
bespoke item). Each kit SHALL be composed of gear that fits its subrace's lore identity; the
concrete per-subrace selections are registry data deliberately NOT fixed by this requirement —
only existence, equipment-only validity, sharing, and load-time enforcement are normative and
mechanically tested.

#### Scenario: Every registered subrace resolves a non-empty kit of registered equipment
- **WHEN** the starting-kit registry is inspected against `SUBRACE_REGISTRY` and `ITEM_REGISTRY`
- **THEN** every subrace key has exactly one kit, every kit is non-empty, and every item key in
  every kit resolves in `ITEM_REGISTRY` with a non-null `equipment_slot`

#### Scenario: A broken kit fails at load
- **WHEN** a starting-kit registry under construction omits a registered subrace, declares an
  unknown or non-equipment (no `equipment_slot`) item key, duplicates one item key within a kit,
  declares an empty kit, or declares a non-positive quantity
- **THEN** registry validation raises at load time instead of the broken kit ever reaching an
  activation

#### Scenario: A basic item is shared across kits
- **WHEN** two or more subrace kits declare the same basic equipment key (for example a common
  knife or leather armor)
- **THEN** both kits remain valid; sharing catalog items across subraces is conforming behavior

### Requirement: Custom activation grants the chosen subrace's basic starting kit
Custom-mode activation of a pending player shell SHALL set the character's starting inventory to
the chosen subrace's basic starting kit, flattened into the same repeated item-key list shape the
deterministic core already stores in `inventory`, written inside the same all-or-nothing activation
transaction as the identity, traits, and other creation-owned mechanical state. The kit SHALL be
resolved from the lore registry before any activation write, so an unresolvable kit fails preflight
and leaves the character pending. This applies only to player-shell creation activation: imported
characters keep their record-owned inventory unchanged and SHALL NOT receive a subrace kit.
Preset-mode activation SHALL keep granting only the preset's own declared inventory.

#### Scenario: A custom character wakes with its subrace kit
- **WHEN** custom creation activates with a registered subrace whose kit declares item keys K1 and
  K2
- **THEN** the activated character's `inventory` contains exactly one entry per declared quantity
  of K1 and K2, unequipped, and the gear is visible through the normal inventory surface

#### Scenario: Kit coverage holds for every subrace at activation
- **WHEN** custom activation runs once for each registered subrace
- **THEN** each activated character's `inventory` equals that subrace's kit expanded by quantity,
  with no subrace activated into an empty starting inventory

#### Scenario: An activation write failure grants no kit items
- **WHEN** a test injects a failure at any activation write position after the kit was resolved
- **THEN** the character remains pending and its inventory retains its pre-activation value, with
  no partially granted kit

#### Scenario: An imported character is not re-kitted
- **WHEN** a character import record with its own declared inventory loads successfully
- **THEN** its inventory is exactly the record's inventory and no subrace kit is added, since the
  kit contract governs player-shell activation only
