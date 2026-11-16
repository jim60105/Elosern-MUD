# Design

## Context

Facts below were checked on master at e076e764.

- Evennia 6.1.0 defaults `START_LOCATION` and `DEFAULT_HOME` to `"#2"`, and
  `server/conf/settings.py` overrides neither. The account hook creates the character
  shell before any race is known. `typeclasses/accounts.py::at_post_create_character`
  only sets `creation_pending = True`.
- The race and subrace are fixed in `activate_player_character()`
  (`world/rules/character_creation.py`). It is reached from the Telnet command
  (`commands/character_creation.py::_activate_creation`) and from the webclient through
  `activate_draft()` (`world/rules/creation_wizard.py`). `activate_draft` wraps the call
  in a second, outer `transaction.atomic()`.
- Activation already snapshots and restores attributes (`_CREATION_ATTRIBUTE_KEYS`) and
  traits, because the idmapper cache does not follow transactions. Preset starting
  companions are built at `player.location` by `bind_starting_companions`
  (`world/rules/starting_companions.py`, `npc.location = player.location`).
- `LimboRoom.at_pre_object_receive` (`typeclasses/rooms.py`) refuses every
  non-superuser character. `move_to(..., move_hooks=False)` skips that hook, as
  verified in `evennia/objects/objects.py` (around line 1260). The movement settlement
  already returns traversers this way (`world/rules/movement_settlement.py::_compensate_traverser`).
- Every settlement document has exactly one `anchor_room` node, and the map composer
  rejects a document without one. `ANCHOR_PLACEMENT_REGISTRY`
  (`world/lore/anchor_placement.py`) maps each document's `location_ref` to that node
  as a `QualifiedRef`. `static_references.anchor_entrance_xyz(placement)` turns it into
  the current `(x, y, map_id)`. `GridRoom.objects.filter_xyz(xyz=...)` uses
  `filter_family`, so it also finds `AnchorRoom`.
- For each of the 15 subraces in the table in D7, the anchor key equals the
  settlement's `location_ref` and its id. Each landing node is the document's only
  `anchor_room` node. Checked against `content/maps/settlements/*.yaml`, including the
  merged `elven_village_eolas.yaml` (`valley_floor`) and `elven_village_fionnen.yaml`
  (`light_court`).
- `record_arrival(character)` (`world/rules/map_knowledge.py`) never raises. It writes
  the `map_knowledge` attribute for a `PlayerCharacter` standing on a representable node.
- A hooks-enabled `PlayerCharacter.move_to` runs `at_pre_move` (combat check,
  direct-move capture) and `at_post_move` (auto look, arrival lore, encounter dispatch).
  It does not record map knowledge.
- The webclient activation adapter publishes a full `exploration` snapshot after a
  committed activation (`web/webclient/actions/creation_actions.py::_creation_activate_adapter`),
  so no extra movement publication is needed.

## Goals / Non-Goals

Goals: every subrace starts in its own settlement's anchor room, with `home` set to that
room and the arrival in map knowledge. The move stays inside the activation's
all-or-nothing rule. A missing or broken start row fails at load or adoption, not halfway
through a player's activation.

Non-goals:
- No change to 虛境 exits, `CITY_GATE_REGISTRY`, `world/rules/city_gates.py` or the
  `city_gate` document field. Those belong to the follow-up changes
  `retire-limbo-city-gates` and `drop-settlement-city-gate-field`. Once this change sets
  `home`, the gate re-anchor can no longer fire for a player character, because its
  guard requires `home == 虛境`. It is removed in the follow-up.
- No `START_LOCATION` or `DEFAULT_HOME` setting change.
- No guild-service requirement for start settlements, and no distance rule.
- No per-preset override. A preset starts where its subrace starts.
- No population catch-up, dialogue clearing or operator-console relocation semantics.
  `settle_relocation` is the operator teleport. It raises console errors and is not reused.

## Decisions

### D1. Registry shape: subrace to anchor key, in the lore layer

New file `world/lore/start_locations.py`:

```python
@dataclass(frozen=True)
class SubraceStartLocation:
    """One subrace's start settlement, named by its anchor (location) identity."""

    subrace_key: str
    anchor_key: str


SUBRACE_START_LOCATION_REGISTRY: dict[str, SubraceStartLocation] = {
    row.subrace_key: row
    for row in (
        SubraceStartLocation("human_royal", "town_olive_ferry"),
        # ... one row per SUBRACE_REGISTRY key, table in D7
    )
}


def validate_start_locations(
    registry: Mapping[str, object], subraces: Mapping[str, object]
) -> None:
    """Reject a start registry that does not cover ``subraces`` exactly once."""


validate_start_locations(SUBRACE_START_LOCATION_REGISTRY, SUBRACE_REGISTRY)
```

`validate_start_locations` raises `ValueError` in this order:
1. a value is not a `SubraceStartLocation`: `f"start location {key!r} must be a SubraceStartLocation"`
2. `row.subrace_key != key`: `f"start location {key!r} declares mismatched subrace {row.subrace_key!r}"`
3. `key not in subraces`: `f"start location {key!r} names an unknown subrace"`
4. `anchor_key` is not a non-empty `str`: `f"start location {key!r} must name a non-empty anchor key"`
5. after the loop, `missing = sorted(set(subraces) - set(registry))`. If it is non-empty:
   `f"subraces without a start location: {missing}"`

Why an anchor key and not a `(settlement, node)` reference? The owner wants the
landing room to be the settlement's gathering room, which in the map data is its anchor
room. Each settlement has exactly one, and its placement is already a qualified node
identity. Naming only the anchor means a row cannot point at the wrong node of the
right settlement. Moving the anchor node moves the start room with it. Whether the
anchor exists cannot be checked when the lore module is imported, because anchors come
from the published geography. That check runs at adoption instead (D2).

A separate module, not a new `Subrace` field. `Subrace` is built positionally in
`races.py` and in the synthetic kit, and its `home_anchor_key` means the lore homeland.
For humans that is not where a character starts (for example `human_royal` lore points
at the capital, while it starts in a town).

Registry inventory: add
`_spec("start_locations", "起始地點", "聚落", _attr("world.lore.start_locations", "SUBRACE_START_LOCATION_REGISTRY"), f"{_LORE}/start_locations.py", "anchor_key")`
to `world/lore/registry_index.py`, after the `starting_kits` line. Use no `ref(...)`
metadata.

### D2. Adoption-time closure: one more StaticWorld family

In `world/maps/static_references.py`:
- `StaticWorld` gains the field `start_locations: Mapping[str, str]` (subrace key to
  anchor key), placed after `place_rooms`.
- `problems()`, after the place-room loop:

```python
        for subrace_key, anchor_key in self.start_locations.items():
            placement = self.anchor_placements.get(anchor_key)
            if placement is None:
                problems.append(
                    f"start location {subrace_key}: anchor {anchor_key!r} has no "
                    "settlement placement"
                )
                continue
            check_node(f"start location {subrace_key}", placement.node)
```

- `fingerprint`: append `tuple(sorted(self.start_locations.items()))` to `parts`.
- `published_static_world()` and `static_world_for_candidate()` both pass
  `start_locations=MappingProxyType({key: row.anchor_key for key, row in SUBRACE_START_LOCATION_REGISTRY.items()})`,
  importing the registry inside the function as the other families do.
- `binding_signature()` is unchanged. It keys presenter caches, and no presenter reads
  start locations.

This rejects adoption at server start (`runtime.adopt` and `sync_all`), before any
persistent write, as the spec requires. It is the same pattern `PLACE_REGISTRY` uses.

### D3. Resolver: `world/rules/start_location.py`

```python
class StartLocationError(ValueError):
    """A subrace's start room cannot be resolved."""


def resolve_start_room(subrace_key: str | None) -> Any:
    """Return the materialized anchor room of ``subrace_key``'s start settlement."""
```

The body uses function-local imports (`GridRoom`, `ANCHOR_PLACEMENT_REGISTRY`,
`SUBRACE_START_LOCATION_REGISTRY`, `anchor_entrance_xyz`,
`elosern_map_core.references.ReferenceError`). Steps:
1. `row = SUBRACE_START_LOCATION_REGISTRY.get(subrace_key) if subrace_key else None`.
   If `None`, raise `StartLocationError(f"subrace {subrace_key!r} has no start location")`.
2. `placement = ANCHOR_PLACEMENT_REGISTRY.get(row.anchor_key)`. If `None`, raise
   `f"start settlement {row.anchor_key!r} has no map placement"`.
3. `xyz = anchor_entrance_xyz(placement)`. Convert a `ReferenceError` to
   `f"start settlement {row.anchor_key!r} does not resolve"`.
4. `room = GridRoom.objects.filter_xyz(xyz=xyz).first()`. If `None`, raise
   `f"start room of {row.anchor_key!r} is not built"`.

There is no fallback room, because `world/maps/AGENTS.md` forbids reader fallbacks.
Function-local imports matter for two reasons: the synthetic kit's swaps stay visible,
and test patches can target one attribute, `world.rules.start_location.resolve_start_room`.

### D4. Activation ordering and rollback

In `activate_player_character`, right after
`validated = preflight_character_creation(...)`:

```python
    try:
        start_room = start_location.resolve_start_room(validated.subrace)
    except start_location.StartLocationError as error:
        raise CharacterCreationError(str(error)) from error
    origin = character.location
```

The module import is `from world.rules import start_location` at the top. The call must
go through the module attribute so that the test stub (D6) works.

Inside the transaction, insert this block after the `creation_draft` removal and before
the starting-companions block:

```python
            # Start-location placement (subrace-start-settlements D4): the
            # character moves into its subrace's start room, is homed there and
            # records the arrival, BEFORE companions are built at its location.
            if not character.move_to(start_room, quiet=True, move_type="teleport"):
                raise CharacterCreationError("start room refused the character")
            character.home = start_room
            from world.rules.map_knowledge import record_arrival

            record_arrival(character)
            if write_observer:
                write_observer("start_location")
```

The move keeps hooks enabled. It is an ordinary direct move, so `at_post_move` sends the
auto look (which Telnet players see), observes arrival lore and runs encounter dispatch.
`creation_pending` is already `False` at this point, because the attribute loop has run.

Rollback:
- Add `"map_knowledge"` to `_CREATION_ATTRIBUTE_KEYS`, with a comment naming this
  change. The attribute snapshot then restores the record in both `activate_player_character`
  and `activate_draft`, since the latter reuses the same tuple.
- New public helper in `character_creation.py`:

```python
def restore_activation_placement(character: Any, origin: Any) -> None:
    """Undo a rolled-back activation placement in-process; never raises.

    The rollback reverted the durable location and home rows, but the idmapper
    object and both rooms' contents caches still hold the moved state. A
    hook-free ``move_to`` returns the character even into a room whose entry
    hook refuses character arrivals (the 虛境 birth room); ``home`` is re-read
    from the rolled-back row and applied in memory only.
    """
```

  Body:
  1. If `character.location is not origin`: when `origin is None`, set
     `character.location = None`. Otherwise call
     `character.move_to(origin, quiet=True, move_hooks=False)`. Wrap this in `try`. On an
     exception, call `log_warn("rollback_restore_failed", exc=error, context={"stage": "activation_placement", "char": character.key, "key": "location"})`.
  2. `row_home = ObjectDB.objects.filter(id=character.id).values_list("db_home_id", flat=True).first()`.
     If `character.db_home_id != row_home`, set `character.db_home_id = row_home`. Wrap
     this the same way, with `"key": "home"`.

  `log_warn` comes from `world.observability`.
- The `except` branch of `activate_player_character` becomes: discard companions (as
  today), then `restore_activation_placement(character, origin)`, then key, traits and
  attributes restore (as today), then `raise`.
- `activate_draft` sets `origin = character.location` before its `try`. Its `except`
  calls `restore_activation_placement(character, origin)` before the existing restores.
  This covers the outer-commit failure, where the inner `except` never runs.
- After the `try` succeeds, `activate_player_character` emits
  `log_info("character_start_placed", context={"char": character.key, "char_dbref": character.dbref, "subrace": validated.subrace, "room": start_room.key, "room_dbref": start_room.dbref})`
  before the lore reveals. This is the observability boundary event for the new state change.

### D5. Interaction with other systems

- Starting companions need no code change. They are built after the move, so
  `player.location` is the start room.
- `home` points at the start room, so the `home` command and anything else that sends a
  character home lands in the settlement.
- The gate re-anchor (`world/rules/city_gates.py`) now sees a home that is not 虛境 and
  does nothing. It is removed in the follow-up.

### D6. Test seams

- `world/tests/start_room_fixture.py` (new):

```python
STUB_START_ROOM_KEY = "t_start_room"


def stub_start_room():
    """Patch start-room resolution to a plain synthetic room.

    For activation tests that do not test placement. Usable as a class or
    method decorator or with ``self.enterContext(stub_start_room())``. The
    room is found by key or created on first use inside the running test, so
    a per-test database rollback never leaves a stale object behind.
    """
    return unittest.mock.patch(
        "world.rules.start_location.resolve_start_room", new=_stub_resolve
    )
```

  `_stub_resolve(subrace_key)` returns the first object of
  `ObjectDB.objects.filter(db_key=STUB_START_ROOM_KEY)` that is an instance of
  `typeclasses.rooms.Room`. If there is none, it returns
  `create_object(Room, key=STUB_START_ROOM_KEY, nohome=True)`. Pass `new=`, so no mock
  argument is injected into test methods.
- Synthetic kit: in `world/tests/synthetic_data/data_characters.py` add
  `SYNTH_START_LOCATIONS: dict[str, SubraceStartLocation] = {"t_duskmari_evensong": SubraceStartLocation("t_duskmari_evensong", "t_hollow_tarn")}`.
  In `targets.py`, add it to the content table as `"start_locations": lambda: SYNTH_START_LOCATIONS`,
  and add
  `"start_locations": ("world.lore.start_locations", "SUBRACE_START_LOCATION" + "_REGISTRY")`
  to `REGISTRY_TARGETS`. Export `SYNTH_START_LOCATIONS` from `__init__.py` the same way
  as `SYNTH_STARTING_KITS`. `t_hollow_tarn` already has a synthetic placement on a
  borrowed node that is materialized as a real room, so the real resolver works inside a
  scope of `("subraces", "start_locations", "anchor_placements")` once
  `sync_test_settlements((placement.node.map_id,))` has run.
- Browser seed process (`web/tests/browser/seed/runner.py`, `seed/npc_persona_fixture.py`):
  wrap each `activate_player_character(...)` call in
  `unittest.mock.patch("world.rules.start_location.resolve_start_room", new=lambda subrace_key: <room>)`,
  where `<room>` is the room the seed has just put that character in (`dummy_room`,
  `room`, `character.location`). Seeded characters therefore keep today's placement and
  `home`. Every existing browser journey depends on that room.
- Creation browser runtimes activate in the server process with shipped catalogs, so the
  start rooms must exist. In `web/tests/browser/fixtures.py::journey_settlement_scope`,
  when `os.environ.get("ELOSERN_BROWSER_CREATION") == "1"`, add
  `{ANCHOR_PLACEMENT_REGISTRY[row.anchor_key].zcoord for row in SUBRACE_START_LOCATION_REGISTRY.values()}`
  to the returned set. Only creation runtimes pay the extra boot cost.

### D7. Shipped mapping (game data, not spec)

| Subrace | Anchor key | Anchor node (room name) |
|---|---|---|
| `fionnen` | `elven_village_fionnen` | `light_court` (林間光庭) |
| `ciaran` | `elven_village_ciaran` | `village_plaza` (村中廣場) |
| `eolas` | `elven_village_eolas` | `valley_floor` (谷底空地) |
| `human_royal` | `town_olive_ferry` | `central_plaza` (中央廣場) |
| `human_noble` | `town_steed_plain` | `central_plaza` (中央廣場) |
| `human_coastal` | `port_fishers_cove` | `central_plaza` (中央廣場) |
| `human_plains` | `town_orange_blossom` | `central_plaza` (中央廣場) |
| `human_highland` | `town_silver_ridge` | `central_plaza` (中央廣場) |
| `foxkin` | `city_fox_fire` | `central_plaza` (狐火石坪) |
| `bearkin` | `city_iron_claw` | `central_plaza` (鐵砧石坪) |
| `catkin` | `city_shadow_wood` | `central_plaza` (苔石坪) |
| `wolfkin` | `city_moon_howl` | `central_plaza` (嚎月石坪) |
| `bovinekin` | `city_horn_plain` | `central_plaza` (野牛石坪) |
| `tigerkin` | `city_tiger_roar` | `central_plaza` (虎嘯石坪) |
| `rabbitkin` | `city_swift_wind` | `central_plaza` (長風石坪) |

The registry stores only the first two columns. The node column is what adoption
derives, and it is listed for review only.

### D8. Decided: 虛境 becomes a backstage holding room; split into three changes

The owner approved this: 虛境 only holds creation-pending shells. The 虛境-to-city
bridging exits, the `CITY_GATE_REGISTRY` bridging sync and the first-gate `home`
re-anchor are removed. That work is not in this change. It is split out for size:
- `retire-limbo-city-gates` covers the game side: bootstrap bridging and prune, the
  registry view, the re-anchor, the static-reference family, about 40 test and fixture
  modules that probe the gate registry, and four main specs.
- `drop-settlement-city-gate-field` covers the authoring side: the map-core schema, the
  map editor backend and frontend, the synthesis tools, and one line in each of the 338
  settlement documents. Only four of those documents carry a filled-in row; the other
  334 have an empty `city_gate:` key.

Doing all of this in one change would be several engineer-days. This change alone is a
complete, shippable behavior: no player walks out of 虛境 any more.

## Risks / Trade-offs

- [Every existing activation test now needs a start room.] Mitigation: one stub (D6),
  added to each module listed in tasks.md. Placement behavior is tested only in the
  dedicated tests.
- [Creation browser runtimes now materialize 15 extra settlements.] Accepted. This is
  limited to runtimes with `ELOSERN_BROWSER_CREATION=1`, and no timing gate is added.
- [A synthetic scope that swaps `start_locations` and then adopts a fresh candidate map
  world would reject adoption, because the candidate has no `t_hollow_tarn` placement.]
  Mitigation: tests publish the shipped world in module or class setup, before entering
  the scope, as `world/maps/AGENTS.md` already requires. The process-wide browser
  install publishes a merged snapshot through `runtime.publish`, not a candidate
  adoption. Task 6.4 runs the synthetic browser composition fixture to confirm.
- [The auto look from `at_post_move` reaches the webclient before the full snapshot.]
  Accepted. The snapshot replaces all panels.
