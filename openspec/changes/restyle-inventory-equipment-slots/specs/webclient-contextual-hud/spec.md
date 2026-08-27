## MODIFIED Requirements

### Requirement: The equipment doll renders only server-authored slots and drops nothing
The equipment presentation SHALL be built from the committed `character` panel's equipment rows, each of which carries a slot, an item key and a display name and nothing more. The doll SHALL render the server's three singleton slots and one accessory summary as four named positions in a compact two-column square layout. Each position SHALL use only a fixed local SVG selected by its server-authored slot role; it SHALL NOT select an item icon from an item key or display name. A singleton slot with no row SHALL render a visible named empty state with a dashed outline. An occupied singleton slot SHALL render its visible slot label and committed display name. The accessory summary SHALL render its visible label and committed item count, while every repeatable accessory row SHALL render in the retained accessory detail group. Any slot key outside the recognised set SHALL render as a labelled fallback row rather than being discarded, so no row the payload sends is lost.

The doll SHALL NOT render an item statistic, attack or defence value, rarity, item icon, summary, or comparison against another item: the equipment rows carry none of those. Equipment SHALL be presented as true values that a disguise does not affect.

#### Scenario: An empty slot is shown as empty
- **WHEN** the committed equipment rows carry no row for a singleton slot
- **THEN** that slot renders its visible name with a dashed explicit empty state, and no item is invented for it

#### Scenario: An occupied singleton slot is identified without guessing its item type
- **WHEN** the committed equipment rows carry one primary-hand item
- **THEN** the primary-hand square renders only its fixed slot SVG, visible slot name, and committed display name without an inferred item icon, rarity, statistic, or comparison

#### Scenario: Repeated accessories all render
- **WHEN** the committed equipment rows carry more than one accessory row
- **THEN** the accessory summary states the committed count and every accessory row renders in the accessory group, and none is dropped for want of a fixed position

#### Scenario: An unrecognised slot is rendered, not discarded
- **WHEN** an equipment row carries a slot key outside the recognised set
- **THEN** the row renders with its slot key as its label and its display name, and the doll drops no row

#### Scenario: No statistics are invented for an equipped item
- **WHEN** an equipped item renders in the doll
- **THEN** it shows its display name and its slot only, with no attack, defence, rarity, item icon, summary, or comparison value
