## Purpose

Define the single, shared movement-cost charging entry point: `charge_movement()` resolves a
distance-bearing outdoor traversal's physical duration from authored geometry and the slowest
eligible source-present traveller's terrain speed (or a non-distance connector's authored
`command_defaults` duration) and advances the world clock only for a player-driven traverser.
Every non-teleport exit lineage charges successful player movement through it via
`MovementCostMixin.at_post_traverse` — never through a bespoke, inline `advance()` call.

## Requirements

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

### Requirement: Movement never charges through a teleport, spawn, or non-exit relocation
No call to `DefaultObject.move_to()` that is not routed through an `Exit`'s own `at_traverse` (for
example, a `move_type="teleport"` call, or a raw `move_to(quiet=True)` relocation such as change 14's
`_relocate_to_default_home()`) SHALL cause `charge_movement()` to be invoked, because
`at_post_traverse` — the hook `MovementCostMixin` relies on — is only ever called from within
`DefaultExit.at_traverse`'s own success branch.

#### Scenario: A teleport-style move_to call does not advance the clock
- **WHEN** `traversing_object.move_to(destination, move_type="teleport")` is called directly, with no
  `Exit` involved
- **THEN** `get_world_clock().tick` is unchanged, even though the move itself succeeds

#### Scenario: A quiet relocation (instance-room reclamation style) does not advance the clock
- **WHEN** `traversing_object.move_to(destination, quiet=True)` is called directly (the exact shape
  change 14's `_relocate_to_default_home()` uses)
- **THEN** `get_world_clock().tick` is unchanged, even though `at_post_move` still fires on the moved
  object (verified: `quiet=True` alone does not suppress `move_hooks`)

### Requirement: Movement charges only for a player-driven traverser, never for an autonomous NPC
or monster
`charge_movement()` SHALL consult `world.rules.player_control.is_player_driven(traversing_object)`
(a puppeted `PlayerCharacter` or a possessed-and-puppeted NPC) and SHALL NOT advance `WorldClock`
for any other traverser, matching design doc D4 ("the world advances only on player action").
This requirement supersedes the removed same-rule requirement titled for `PlayerCharacter`
specifically; the scenarios below are its continuation.

#### Scenario: An NPC traversing a MovementCostMixin exit does not advance the clock
- **WHEN** an `NPC`-typeclassed object successfully traverses an exit whose class includes
  `MovementCostMixin`
- **THEN** the traversal itself succeeds (the traverser's location changes), but
  `get_world_clock().tick` is unchanged

#### Scenario: A possessed NPC traversing the same exit charges the clock
- **WHEN** a possessed, puppeted NPC traverses a `MovementCostMixin` exit
- **THEN** the traversal succeeds and the clock advances by the exit's resolved movement cost

### Requirement: Flight-required exits pass only for flight/flash_step owners
`typeclasses/exits.py` SHALL support an opt-in `requires_flight: bool` class/instance attribute
(default `False`) on exit typeclasses using `MovementCostMixin`. An exit with `requires_flight=True`
SHALL deny traversal (via its access-lock check, alongside any other existing lock) to a
`PlayerCharacter` that owns neither `flight` nor `flash_step`. No exit shipped by this change sets
`requires_flight=True` — the flag exists for future map content to opt into.

#### Scenario: An entity without flight or flash_step cannot traverse a flight-required exit
- **WHEN** a `PlayerCharacter` owning neither `flight` nor `flash_step` attempts to traverse an exit
  with `requires_flight=True`
- **THEN** the traversal is denied the same way a locked exit denies traversal (per this capability's
  existing "A locked exit never charges and never records" scenario)

#### Scenario: An entity with flight or flash_step can traverse a flight-required exit
- **WHEN** a `PlayerCharacter` owning `flight` (or, separately, one owning only `flash_step`) attempts
  to traverse an exit with `requires_flight=True`
- **THEN** the traversal succeeds (subject to any other unrelated lock on the same exit)

#### Scenario: No existing exit is flight-required by default
- **WHEN** any exit shipped before this change is inspected
- **THEN** its `requires_flight` is `False`

### Requirement: Traversal integrates fatigue over remaining distance
Traversal SHALL consume the external fatigue owner’s prediction and settlement semantics, recomputing the slowest sustainable speed at each member threshold or terrain boundary. Only remaining distance SHALL use a changed speed; rounding and fractional mental state SHALL agree with accepted settlement.

#### Scenario: Threshold within an edge
- **WHEN** synthetic external physiology permits 1.25m/s for 40s then half speed on a 100m edge
- **THEN** first 50m costs 40s and remaining 50m costs 80s, totaling 120s, rather than 80s or 160s.

#### Scenario: Limiting member changes
- **WHEN** an initially faster member crosses a threshold before the initial slowest member
- **THEN** remaining distance uses the newly limiting member; processing is per authored leg/event boundary, never per meter or second.

#### Scenario: Fractional prediction agreement
- **WHEN** two short accepted traversals and a subsecond rounding boundary are predicted and committed
- **THEN** external fractional mental remainder is preserved and prediction uses the same final integer elapsed-time semantics as settlement.

### Requirement: Sparse edge admission refuses pre-destination depletion
Every exit lineage SHALL reject departure before writes if any intended present traveller is forced sleeping or predicted to exhaust mental reserve before the next named destination. Exactly zero at arrival SHALL be permitted, followed by the external forced-sleep consequence at that destination.

#### Scenario: Exhaustion before destination
- **WHEN** piecewise prediction exhausts any member at 90m of a 100m edge although initial-speed estimation appeared sufficient
- **THEN** departure refuses with a clear reason; clock, location, mental remainder, knowledge, owning effects and wilderness materialization remain unchanged; no unnamed partial room or automatic rest is created.

#### Scenario: Exact-zero destination
- **WHEN** reserve reaches zero exactly at the destination under shared rounded-time semantics
- **THEN** full accepted traversal commits and external forced sleep applies there; next departure refuses.

#### Scenario: Possession and every lineage
- **WHEN** a source-present follower or possessed commander body is forced sleeping
- **THEN** plain exit, costed grid exit, both gate directions and ordinary wilderness movement all refuse before relocation or flight-waiver early return; a remote sleeping member does not block travel.
