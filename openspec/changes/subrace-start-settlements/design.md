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
- For each of the 15 subraces in the table in `subrace-start-locations` D5, the anchor key equals the
  settlement's `location_ref` and its id. Each landing node is the document's only
  `anchor_room` node. Checked against `content/maps/settlements/*.yaml`, including the
  merged `elven_village_eolas.yaml` (`valley_floor`) and `elven_village_fionnen.yaml`
  (`light_court`).
- `record_arrival(character)` (`world/rules/map_knowledge.py`) never raises. It writes
  the `map_knowledge` attribute for a `PlayerCharacter` standing on a representable node.
- A hooks-enabled `PlayerCharacter.move_to` runs several hooks. `at_pre_move` does the
  combat check and the direct-move capture. `at_post_move` sends the auto look, observes
  arrival lore, dispatches encounters and registers an on-commit alignment fact.
  `GridRoom.at_object_receive` (`typeclasses/rooms.py`, lines 144-153) calls
  `ensure_scene_asset` and `record_scene_entry`; the latter writes the entered-archetypes
  attribute in its own savepoint. None of these hooks records map knowledge. Several of
  these effects are not transactional: a sent message cannot be recalled, and an attribute
  cache written in a savepoint goes stale after an outer rollback.
- The webclient activation adapter publishes a full `exploration` snapshot after a
  committed activation (`web/webclient/actions/creation_actions.py::_creation_activate_adapter`),
  so no movement publication is needed.

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

### D1-D3. Registry, adoption closure and resolver

Delivered by `subrace-start-locations`: `world/lore/start_locations.py`, the
`StaticWorld.start_locations` family, `world/rules/start_location.py`
(`StartLocationError`, `resolve_start_room`) and `SYNTH_START_LOCATIONS`. This change
only calls `start_location.resolve_start_room(subrace_key)`.

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
            # The move is hook-free so the transaction holds only durable,
            # snapshot-covered writes; arrival effects run after commit.
            if not character.move_to(start_room, quiet=True, move_hooks=False):
                raise CharacterCreationError("start room refused the character")
            character.home = start_room
            from world.rules.map_knowledge import record_arrival

            record_arrival(character)
            transaction.on_commit(
                lambda: _run_start_arrival_effects(character, start_room, origin)
            )
            if write_observer:
                write_observer("start_location")
```

Why hook-free: the review found that the hook chain writes state that neither the
attribute snapshot nor `restore_activation_placement` covers (the entered-archetypes
attribute in its own savepoint, the scene-art ensure request, encounter activation). It
also sends a look that cannot be recalled and registers an alignment fact while the
client is still in creation mode. Inside the transaction, the hook-free move keeps only
three writes: location, `home` and `map_knowledge`. All three are restored on rollback,
and the rollback mirrors the forward move exactly. `transaction.on_commit` registered
inside `activate_draft`'s outer atomic fires only when the outer block commits, so a
rolled-back activation runs no arrival effects at all.

New private helper in `character_creation.py`:

```python
def _run_start_arrival_effects(character: Any, room: Any, origin: Any) -> None:
    """Run the arrival effects of a committed start-room placement.

    They are the effects a hooks-enabled move would have run: the room's
    receive hook (scene entry and art ensure), arrival lore, encounter
    dispatch and the auto look. Each step is best-effort: activation has
    already committed, so a failure is logged and never raised.
    """
```

The body runs these four steps in order. Each step sits in its own
`try/except Exception as error`, which calls
`log_warn("character_start_arrival_effect_failed", exc=error, context={"char": character.key, "step": <step>})`:
1. `room.at_object_receive(character, origin, move_type="teleport")`, step `"receive"`;
2. `observe_arrival_lore(character, room)` from `world.quests.room_observation`, step
   `"lore"`;
3. `activate_for_move(character)` from `world.quests.encounter_dispatch`, step
   `"encounters"`;
4. `character.msg(text=(character.at_look(room), {"type": "look"}))`, step `"look"`.

No alignment fact is published, because the webclient adapter's full snapshot replaces
every panel. Telnet players get the room look from step 4.
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
    hook-free ``move_to`` (the mirror of the hook-free forward move) returns the
    character even into a room whose entry hook refuses character arrivals (the
    虛境 birth room); ``home`` is re-read from the rolled-back row and applied
    in memory only.
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

### D8. Decided: 虛境 becomes a backstage holding room; the batch has five changes

The owner approved this: 虛境 only holds creation-pending shells. The 虛境-to-city
bridging exits, the `CITY_GATE_REGISTRY` bridging sync and the first-gate `home`
re-anchor are removed. For the one-engineer-day size, the work is split into five
changes:
1. `subrace-start-locations`: the registry, the adoption closure, the resolver and the
   kit row. It changes no behavior.
2. `subrace-start-settlements` (this change): activation placement plus the stub sweep
   over the activation tests.
3. `entrance-probe-fixtures`: moves the test probes off the gate registry. It changes no
   behavior and has no dependency.
4. `retire-limbo-city-gates`: the game-side removal (bootstrap, registry view,
   re-anchor, static-reference family, gate tests, specs).
5. `drop-settlement-city-gate-field`: the schema, the map editor, the synthesis tools
   and the strip of one key from each of the 338 settlement documents. 334 of them hold
   an empty key and 4 hold a populated row.

This change alone is a complete, shippable behavior: no player walks out of 虛境 any more.

## Risks / Trade-offs

- [Every existing activation test now needs a start room.] Mitigation: one stub (D6),
  added to each module listed in tasks.md. Placement behavior is tested only in the
  dedicated tests.
- [Creation browser runtimes now materialize 15 extra settlements.] Accepted. This is
  limited to runtimes with `ELOSERN_BROWSER_CREATION=1`, and no timing gate is added.
- [The post-commit arrival effects can fail after a committed activation.] Accepted and
  logged. The character is already correctly placed and homed. The effects are the same
  best-effort class as the lore reveals that already run after commit.
- [The post-commit look reaches the webclient alongside the full snapshot.] Accepted.
  The snapshot replaces all panels.
