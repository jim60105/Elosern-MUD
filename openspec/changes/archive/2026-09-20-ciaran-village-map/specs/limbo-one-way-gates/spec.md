## MODIFIED Requirements

### Requirement: The city-gate registry is the sole authored source of 虛境 city gates
`world/maps/city_gates.py` SHALL define a frozen, slotted `CityGateDef` dataclass with the fields `map_id` (str), `gate_xyz` (a `(int, int, str)` grid coordinate), `exit_key` (str), and `exit_aliases` (a tuple of strings), and SHALL expose `CITY_GATE_REGISTRY` as a `MappingProxyType` keyed by map id. Today it SHALL carry exactly two rows — `capital_altoria` with `gate_xyz` `(2, 0, "capital_altoria")`, `exit_key` 「南門」, and `exit_aliases` `("王都", "城門")`, and `village_ciaran` with `gate_xyz` at the village's entrance node, `exit_key` 「隱密小徑」, and its own aliases. A row SHALL NOT be assumed to describe a walled settlement: the registry slot expresses "the authored way in from 虛境", and an entry may name a concealed path where the destination has no gate. `world/maps/bootstrap.py` SHALL author gate exits exclusively from this registry: no gate exit key, alias, or coordinate SHALL be duplicated as a bootstrap constant (the former `EXIT_TO_CITY` / `EXIT_TO_LIMBO` constants SHALL NOT exist), and no reverse-direction gate data SHALL be authored anywhere.

#### Scenario: The registry pins the single capital row
- **WHEN** `CITY_GATE_REGISTRY` is inspected
- **THEN** its `capital_altoria` row carries `gate_xyz` `(2, 0, "capital_altoria")`, `exit_key` 「南門」, and `exit_aliases` `("王都", "城門")`

#### Scenario: Every registry row yields exactly one forward exit
- **WHEN** `sync_grid()` runs against a database holding every registered map
- **THEN** the starting room has exactly one forward exit per registry row, each leading to its row's `gate_xyz`, and no two rows' exit keys or aliases collide

#### Scenario: The registry cannot be mutated at runtime
- **WHEN** a caller attempts to insert, replace, or delete a `CITY_GATE_REGISTRY` entry
- **THEN** the attempt raises and the registry contents are unchanged

#### Scenario: Bootstrap carries no gate surface of its own
- **WHEN** `world/maps/bootstrap.py` is inspected for gate exit authoring
- **THEN** no `EXIT_TO_CITY` or `EXIT_TO_LIMBO` constant exists and the only gate keys, aliases, and coordinates it uses are read from `CITY_GATE_REGISTRY` rows
