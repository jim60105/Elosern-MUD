# Spec Delta

## ADDED Requirements

### Requirement: Distance-bearing traversal uses authored physical geometry
Distance-bearing outdoor traversal SHALL use Euclidean straight-edge length or full authored meter polyline length and terrain speed. The entire committed duration SHALL round upward once. Coordinate-free interior connectors SHALL retain explicit durations without invented district-length door distances.

#### Scenario: Healthy segment and bent road
- **WHEN** a healthy party traverses (0,0) to (60,80), then separately (0,0)->(0,60)->(80,60)
- **THEN** the 100m straight edge costs 80s at 1.25m/s; the 140m bent edge costs 112s; no hidden detour/elevation factor applies.

#### Scenario: Once-only rounding
- **WHEN** two physical legs take 0.4s each
- **THEN** the traversal commits 1s, not 2s; coordinate precision introduces no per-meter commands.

#### Scenario: Scale is explicit
- **WHEN** the same road calculation consumes declared wilderness cell spans of 10000m and 1000m
- **THEN** cardinal durations are 8000s and 800s respectively; no seconds-to-meters inference, fallback, or dual runtime authority exists.

### Requirement: Terrain and the slowest eligible traveller determine speed
Healthy settlement and good-road speed SHALL be 1.25m/s; open ground 3km/h, passable woodland 2km/h, rough mountain trail 1.5km/h. The slowest eligible source-present intended traveller SHALL determine party speed, including the commander body under possession.

#### Scenario: Terrain calibration
- **WHEN** healthy party traverses 1km road/open/woodland/mountain
- **THEN** costs are 800/1200/1800/2400 seconds; five or six healthy members add no headcount penalty and combat agility or averaging never defines travel speed.

#### Scenario: Restricted member
- **WHEN** a present member sustains 1m/s while others sustain 1.25m/s over 100m
- **THEN** cost is 100s; remote members are excluded from eligibility, charges and speed.

#### Scenario: Diagonal and blocked corner
- **WHEN** a 1km-grid road diagonal is evaluated
- **THEN** it costs ceil(800 sqrt(2))=1132s; either impassable orthogonal neighbor rejects the diagonal before writes, consistently in resolver and traversal.

### Requirement: Physical gate approaches are charged exactly once
Gate crossings SHALL use authored absolute-meter approach geometry and the settlement anchor transform. Eligibility and edge resolution SHALL precede relocation. A crossing SHALL charge its physical segment once without adding duplicate wilderness and city hops.

#### Scenario: Cross-layer approach
- **WHEN** gate and approach lie at absolute (1000,1000) and (1300,1400)
- **THEN** 500m at healthy road speed costs 400s in either direction; no extra full-cell step is charged.

#### Scenario: No automatic travel-day quota
- **WHEN** unreduced road costs are aggregated
- **THEN** six walking hours correspond to 27km and 1200km to about 267 walking hours or 45 six-hour walking days; a seventh walking hour is legal, no unperformed rests/sleep are charged, no route automation or exact fifty-day relocation is introduced.

#### Scenario: Existing flight waiver
- **WHEN** an allowed owned flight user crosses wilderness
- **THEN** the existing wilderness time waiver persists without a new flight speed; settlement walking is charged, flash_step alone does not waive wilderness time, and legality still runs before the waiver.

## MODIFIED Requirements

### Requirement: charge_movement() is the single, shared movement-cost charging function
`world/rules/movement.py` SHALL provide `charge_movement(traversing_object,
cost_key: str, *, source_location, wilderness_source_coordinates=None) -> None`.
It prices distance-bearing traversal from the preflight record and
non-distance connectors from their authored duration, and calls
`get_world_clock().advance(cost, AdvanceSource.COMMAND, entities)` only when
`is_player_driven(traversing_object)`; `entities` is the traverser plus
the followers the follow step moves from `source_location`.

#### Scenario: charge_movement advances the clock by the resolved cost for a PlayerCharacter
- **WHEN** `charge_movement(player_character, "move")` is called
- **THEN** `get_world_clock().tick` after the call equals its value before the call plus
  the resolved physical traversal duration (or authored non-distance connector duration)

#### Scenario: charge_movement is a no-op for a non-PlayerCharacter traverser
- **WHEN** `charge_movement(npc, "move")` is called for an `NPC`-typeclassed (not `PlayerCharacter`)
  entity
- **THEN** `get_world_clock().tick` is unchanged

#### Scenario: A possessed NPC charges movement like a player
- **WHEN** `charge_movement(npc, "move")` is called for an NPC that is possessed and puppeted
- **THEN** the clock advances by the resolved physical traversal duration (or authored non-distance connector duration) with
  `AdvanceSource.COMMAND`, settling the possessed NPC first and then the commander's body and
  every companion co-located with it in the source room

#### Scenario: charge_movement always uses AdvanceSource.COMMAND
- **WHEN** `charge_movement()` is called with any registered `cost_key`
- **THEN** the underlying `WorldClock.advance()` call receives `AdvanceSource.COMMAND`

#### Scenario: A flight-owning PlayerCharacter is waived the wilderness_move cost
- **WHEN** `charge_movement(player_character, "wilderness_move")` is called on a `PlayerCharacter`
  owning `flight`
- **THEN** `get_world_clock().tick` is unchanged

#### Scenario: The waiver does not extend to other cost keys
- **WHEN** `charge_movement(player_character, "move")` is called on the same flight-owning
  `PlayerCharacter`
- **THEN** the clock advances by the resolved physical traversal duration (or authored non-distance connector duration) exactly as it would for a
  non-flight-owning entity

#### Scenario: A non-flight-owning PlayerCharacter still pays the wilderness_move cost
- **WHEN** `charge_movement(player_character, "wilderness_move")` is called on a `PlayerCharacter` not
  owning `flight`
- **THEN** the clock advances by the resolved physical edge duration

#### Scenario: Movement-event clock advancement is exclusive to charge_movement
- **WHEN** any function or inline call site in this project is inspected for movement-event clock
  advancement
- **THEN** none calls `world.rules.clock.get_world_clock().advance()` for a movement event, and
  every exit lineage that charges movement calls `charge_movement()`

#### Scenario: The flight waiver is keyed on the exact owned-skill membership check
- **WHEN** `charge_movement(traversing_object, cost_key)` runs with `cost_key == "wilderness_move"`
  and `"flight" in traversing_object.skills.owned_keys()`
- **THEN** `charge_movement()` returns without advancing the clock, while every other `cost_key`
  charges normally regardless of owned skills

#### Scenario: A player traversal settles its co-located companions
- **WHEN** `charge_movement(player_character, "move", source_location=room)` runs while companion 艾拉
  is in `room` and companion 卡恩 is elsewhere
- **THEN** the single advance settles the player character and 艾拉, and 卡恩's state is unchanged

### Requirement: MovementCostMixin charges via at_post_traverse, not at_traverse's return value
`typeclasses/exits.py` SHALL define `MovementCostMixin`, a plain mixin carrying a class attribute
`movement_cost_key: str` (default `"move"`) and overriding `at_post_traverse(traversing_object,
source_location, **kwargs)` to call `super().at_post_traverse(...)` followed by
`after_successful_movement(traversing_object, source_location, cost_key=self.movement_cost_key,
destination=traversing_object.location)` — the shared movement-completion helper.

#### Scenario: A successful traversal through a MovementCostMixin exit charges exactly once and records arrival
- **WHEN** a `PlayerCharacter` successfully traverses an exit whose class includes
  `MovementCostMixin`
- **THEN** `get_world_clock().tick` increases by exactly one `CLOCK_YAML["command_defaults"][
  movement_cost_key]`, the traversing object's location is the exit's destination, and the traversing
  character's map-knowledge record contains the destination's canonical node ID

#### Scenario: A locked exit never charges and never records
- **WHEN** an exit whose class includes `MovementCostMixin` has a `traverse` lock that denies the
  traversing object
- **THEN** the traversal command does not call `at_traverse` at all (the access check runs first, per
  Evennia's own `ExitCommand.func`), the traversing object's location is unchanged,
  `get_world_clock().tick` is unchanged, and no map-knowledge observation is recorded

#### Scenario: A vetoed at_pre_move never charges and never records
- **WHEN** the traversing object's `at_pre_move` returns a falsy value during an attempted traversal
  through a `MovementCostMixin` exit
- **THEN** `move_to()` returns `False`, `at_post_traverse` is never called, the traversing object's
  location is unchanged, `get_world_clock().tick` is unchanged, and no map-knowledge observation is
  recorded

#### Scenario: A teleport-style move_to never records arrival
- **WHEN** `traversing_object.move_to(destination, move_type="teleport")` is called directly, with no
  `Exit` involved
- **THEN** `get_world_clock().tick` is unchanged and no map-knowledge observation is recorded, even
  though the move itself succeeds

#### Scenario: A quiet relocation (instance reclamation style) never records arrival
- **WHEN** `traversing_object.move_to(destination, quiet=True)` is called directly (the exact shape
  change 14's `_relocate_to_default_home()` uses)
- **THEN** `get_world_clock().tick` is unchanged and no map-knowledge observation is recorded, even
  though `at_post_move` still fires on the moved object

#### Scenario: The MovementCostMixin delegates to the shared completion helper
- **WHEN** `typeclasses/exits.py::MovementCostMixin.at_post_traverse` is inspected
- **THEN** it calls `after_successful_movement(...)` with `cost_key=self.movement_cost_key`, the
  shared helper (not the mixin) calls `world.rules.movement.charge_movement(traversing_object,
  cost_key)` and `world.rules.map_knowledge.record_arrival(traversing_object)`, and neither the mixin
  nor the helper calls `world.rules.clock.get_world_clock().advance()` directly

#### Scenario: The MovementCostMixin at_traverse opens the settlement boundary and delegates the traversal
- **WHEN** `typeclasses/exits.py::MovementCostMixin.at_traverse` is inspected
- **THEN** it invokes the movement-settlement boundary (the movement-settlement-atomicity entry point)
  around a call to `super().at_traverse(...)`, contains no inline
  `world.rules.clock.get_world_clock().advance()` call, and its `at_post_traverse` is unchanged

#### Scenario: The completion helper charges then records arrival
- **WHEN** `after_successful_movement(traversing_object, source_location, cost_key=..., destination=...)`
  runs
- **THEN** it calls `world.rules.movement.charge_movement(traversing_object, cost_key)` and then
  `world.rules.map_knowledge.record_arrival(traversing_object)`

#### Scenario: Map knowledge is recorded only after the movement transaction succeeded
- **WHEN** `MovementCostMixin.at_post_traverse` fires
- **THEN** it fires exclusively from the stock `DefaultExit.at_traverse` success branch — the same
  structural guarantee that already makes the charge correct — so recording map knowledge happens
  only after the movement transaction has already succeeded

#### Scenario: at_traverse never inspects or reinterprets super()'s return value
- **WHEN** `MovementCostMixin.at_traverse` delegates the traversal to `super().at_traverse(...)`
  inside the settlement boundary
- **THEN** it does not inspect or reinterpret any return value from that call — `at_traverse`'s
  return value remains `None` in both branches, and success detection stays with `at_post_traverse`
  and the callers' location checks

#### Scenario: Recording map knowledge leaves movement-charge behavior unchanged
- **WHEN** `record_arrival` recording is performed alongside a movement charge
- **THEN** the movement-charge behavior is not changed in any way by the recording

### Requirement: typeclasses.exits.Exit and CostedXYZExit both carry MovementCostMixin with
movement_cost_key "move"
`typeclasses/exits.py::Exit(MovementCostMixin, ObjectParent, DefaultExit)` SHALL include
`MovementCostMixin` in its base classes, with `movement_cost_key = "move"`.
`typeclasses/exits.py` SHALL also define `CostedXYZExit(MovementCostMixin,
evennia.contrib.grid.xyzgrid.xyzroom.XYZExit)`, likewise with `movement_cost_key = "move"`.

#### Scenario: Exit charges move on successful traversal
- **WHEN** a `PlayerCharacter` successfully traverses a plain `typeclasses.exits.Exit` instance
- **THEN** `get_world_clock().tick` increases by exactly the resolved physical traversal duration (or authored non-distance connector duration)

#### Scenario: CostedXYZExit charges move and preserves XYZExit's own coordinate behavior
- **WHEN** a `CostedXYZExit` is created via `CostedXYZExit.create(key=..., location=..., destination=
  ...)` and a `PlayerCharacter` successfully traverses it
- **THEN** `isinstance(exit_obj, evennia.contrib.grid.xyzgrid.xyzroom.XYZExit)` is `True`,
  `get_world_clock().tick` increases by exactly the resolved physical traversal duration (or authored non-distance connector duration), and the
  traversing object's location is the exit's destination

#### Scenario: An instance-room exit pair charges move with no code change beyond Exit's own retrofit
- **WHEN** an origin/return `Exit` pair is created with `typeclasses.exits.Exit.create()` (the exact
  call shape `world/maps/instance.py::spawn_instance_room()`, change 14, uses) and a
  `PlayerCharacter` successfully traverses either exit of the pair
- **THEN** `get_world_clock().tick` increases by exactly the resolved physical traversal duration (or authored non-distance connector duration) per
  successful traversal, with no edit to change 14's own `spawn_instance_room()` required

#### Scenario: Exit inherits the mixin's default cost key unmodified
- **WHEN** `typeclasses/exits.py::Exit` is inspected
- **THEN** its `movement_cost_key = "move"` is the mixin's default, inherited unmodified

#### Scenario: CostedXYZExit preserves XYZExit's pre-existing behaviors
- **WHEN** a `CostedXYZExit` is inspected or used
- **THEN** every other behavior `XYZExit` already provides is preserved (coordinate tags,
  `.xyz`/`.xyz_destination` properties, `.create()`)
