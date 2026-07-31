## Context

`rulebook/clock.yaml::command_defaults.move: 30` has existed since change 11 (`world-clock`,
archived, implemented) as declared-but-unconsumed data. Change 12 (`map-anchor-grid`, committed, not
implemented) explicitly declined to wire it (its own design.md D-8 Non-Goal: "No movement command
wiring to `WorldClock`"). Change 13 (`map-wilderness`, committed, not implemented) wired its own,
separate `wilderness_move: 9000` cost for wilderness steps, and its own design.md D-8 recorded, by
scanning the rest of the roadmap (items 14-23), that no future change is scoped to wire `move: 30`
either — "a permanent gap by omission." The project owner has asked for a small, inserted roadmap
change to close it.

**The central fact that shapes this whole design**: there are three unrelated exit lineages in this
project, not one.

1. `typeclasses/exits.py::Exit(ObjectParent, DefaultExit)` — the project's own class, currently
   `pass`. Used directly by change 12 for the Limbo↔grid bridge (D-7 of that change) and by change 14
   for every `spawn_instance_room()` origin/return exit pair (D-2 of that change).
2. `evennia.contrib.grid.xyzgrid.xyzroom.XYZExit` — used **directly**, with no project subclass, for
   all twelve of the sample city's intra-city exits (change 12 design doc §4: "Use directly").
3. Change 13's own `WildernessGateExit`/`WildernessReturnExit` — full `at_traverse` overrides on top
   of the wilderness contrib, which **already** charges `wilderness_move` inline, in two places, in a
   change that has not shipped yet.

A narrow "wire `move: 30` onto the grid exits only" would leave lineages 1-3 with three independent
answers to "does walking cost time," one of which (3) already exists as a bespoke, unshared
mechanism. Since change 13 is committed but **unimplemented**, folding its bespoke wiring into a
single shared mechanism now is close to free — there is no shipped behavior to preserve, only a
design document and a delta spec to bring into line before the code is ever written. This design
does that: **unify**, not narrow — see D-1 for the full trade-off.

**What already exists for this change to build on:**
- `world/rules/clock.py::get_world_clock()`, `WorldClock.advance(seconds, source, entities)`,
  `AdvanceSource` (`COMMAND`/`COMBAT`/`SKIP`) — change 11, archived, implemented, unmodified by this
  change.
- `commands/action.py::CmdCast`'s own established call shape: `get_world_clock().advance(result.
  time_cost_seconds, AdvanceSource.COMMAND, [self.caller])` on success only — the precedent this
  change's own `charge_movement()` mirrors exactly.
- `typeclasses/characters.py::PlayerCharacter(LivingEntity)` and `typeclasses/npcs.py::NPC(
  LivingEntity)` — both exist today; `Character(PlayerCharacter)` is `settings.BASE_CHARACTER_
  TYPECLASS`'s default target (confirmed by reading `evennia/settings_default.py` and this project's
  own `settings.py`, which does not override it), so `EvenniaTest`'s own `char1`/`char2` fixtures are
  already `PlayerCharacter` instances.
- `world/rules/disengage.py::_handle_disengage()` — the already-implemented `flee` skill. Read
  directly: it only ever calls `battlefield.fled.add(str(actor.key))`; it never calls `move_to()` or
  touches any `Exit`. Combat and room-exit movement are structurally disjoint in this codebase today.
- Changes 12/13/14's own designs, read in full (`openspec/changes/map-anchor-grid/`, `map-wilderness/
  `, `map-instance/`). All three are committed, none implemented.
- The archived `openspec/specs/world-clock/spec.md`, which today states `move`/`converse` are
  "declared as rulebook data only" and that "this change [11] SHALL NOT add a `move` or `converse`
  Evennia command" — still true after this change, since no bespoke `move` command is added; ordinary
  exit-traversal commands (auto-generated per exit by Evennia itself) are what carry the cost.

## Goals / Non-Goals

**Goals:**
- Wire `move: 30` to real, successful movement across every exit lineage that represents "a character
  walked somewhere," without inventing a second cost mechanism alongside change 13's.
- Fold change 13's own `wilderness_move` wiring into the same shared mechanism, since it is
  unimplemented and the fold is nearly free now and only gets more expensive later.
- Verify every claim against the installed Evennia 6.1.0 by running real code, not by reading
  docstrings — see the Verification section.
- Recommend an accurate roadmap name and position, given the change's real dependencies.

**Non-Goals:**
- **`converse: 60` remains unwired.** No roadmap item, including this one, is scoped to build a
  `converse` mechanic. Left exactly as inert as change 11 and change 13 left it.
- **No travel-shortcut, auto-walk, or movement-blocking (combat-lock) command.** Change 13's own Fix 5
  already noted that no `at_pre_move` veto exists anywhere in the codebase today, and this change does
  not add one — it only guarantees that *if* a future change adds one, a vetoed move correctly charges
  nothing (D-6).
- **No change to `settings.START_LOCATION`, no interior rooms, no second anchor's placement.** Not
  this change's concern; unaffected by movement-cost wiring.
- **No edit to change 12's own artifacts.** Change 12 is read-only for this design; the sample city's
  exit-typeclass wiring is expressed as a `MODIFIED sample-city-altoria` delta spec inside this
  change's own `specs/` directory, resolved against real code once change 12 is implemented — see D-9.
- No backward-compatibility, migration, or deprecation handling — the project is unreleased with zero
  users.

## Decisions

### D-1. Unify, not narrow — folding change 13's bespoke wiring into one shared mechanism now, while
it is still free to do.

**Alternative considered: narrow.** Wire only `CostedXYZExit`/`Exit` (lineages 1 and 2), leave change
13's `WildernessGateExit`/`WildernessReturnExit` exactly as designed (their own inline
`get_world_clock().advance()` calls). This is strictly less work today. **Rejected**, for two reasons:
1. **Drift risk.** Two independently-maintained "did this successful traversal cost time" mechanisms,
   reading the same `CLOCK_YAML["command_defaults"]` structure and calling the same
   `get_world_clock().advance()` signature, is exactly the shape of duplication that silently diverges
   the first time either one needs a behavior change (a `PlayerCharacter` gate, say — see D-8, which
   this design adds and which change 13's own inline calls do **not** currently have).
2. **Change 13 is uniquely cheap to fold right now.** It is committed but not implemented — there is
   no shipped code to migrate, no regression risk from changing already-running behavior, only a
   design document and a delta spec to bring into agreement with the unified shape before an
   implementer ever writes the first line of `WildernessGateExit`. This will never be this cheap
   again; once change 13 ships, folding it in becomes a real migration.

**Precedent already set by this exact phase.** Change 13 hit the identical "three unrelated typeclass
lineages need one behavior" shape for `scene_archetype` (`GridRoom`, `TerrainRoom`, and — by name —
a future `InstanceRoom`) and solved it with `SceneArchetypeMixin`, a shared mixin adopted by every
room type that needs the seam, rather than three independently-declared attributes. `MovementCostMixin`
(D-2) is the same idiom applied to exits instead of rooms — this project has already chosen this
resolution once, for a structurally identical problem, in the same phase.

**Consequence for change 13.** Its `wilderness-gateway` capability is not deleted or replaced —
`WildernessGateExit`/`WildernessReturnExit` and their routing logic (D-6 of change 13's own design)
are entirely unmodified by this change's *design*. What changes is the real, already-implemented
`typeclasses/exits.py` code, once this change is implemented: this change's own task group 5 edits
the two lines inside `WildernessGateExit`/`WildernessReturnExit` that call
`get_world_clock().advance(WILDERNESS_MOVE_SECONDS, AdvanceSource.COMMAND, [traversing_object])`,
replacing them with `charge_movement(traversing_object, "wilderness_move")`. That edit happens **in
`typeclasses/exits.py`, by this change, at this change's own implementation time** — change 13 is
implemented first, in roadmap order, and its own `design.md` is deliberately left showing the
original inline calls unedited, since change 13's implementer must be able to build it without
importing a `world.rules.movement` module that does not exist until this change lands (see the
amendment notes this change adds to `map-wilderness/design.md` D-6/D-8, and D-9 below). Observable
behavior (cost, success-only condition, `AdvanceSource.COMMAND`) is bit-for-bit identical before and
after this change's edit; see D-9 for how the *contract* change (not the prose change) is expressed
as an OpenSpec artifact.

### D-2. The hook: `at_post_traverse`, not `at_traverse`'s return value and not
`LivingEntity.at_post_move()` — verified against the installed Evennia 6.1.0, not assumed.

**`at_traverse`'s own return value cannot be used.** Read directly from `evennia/objects/objects.py`:

```python
# DefaultExit.at_traverse (evennia/objects/objects.py:3721)
def at_traverse(self, traversing_object, target_location, **kwargs):
    source_location = traversing_object.location
    if traversing_object.move_to(target_location, move_type="traverse", exit_obj=self):
        self.at_post_traverse(traversing_object, source_location)
    else:
        ...
    # no return statement in either branch
```

There is no `return` statement anywhere in this method — it implicitly returns `None` whether the
move succeeds or fails. Confirmed with a live `EvenniaTest` probe (`tmp/probe_movement_clock/
test_probe.py::test_at_traverse_returns_none_both_branches`): calling `at_traverse` on a plain `Exit`
and on one with `destination=None` both return `None`. A mixin that wraps `at_traverse` and inspects
`result = super().at_traverse(...)` would therefore **never** charge, on either a plain `Exit` or
`XYZExit` (which does not override `at_traverse` either — confirmed by reading `evennia/contrib/grid/
xyzgrid/xyzroom.py` directly, no `at_traverse` or `at_post_traverse` override exists there).

**`at_post_traverse` is the correct hook.** `DefaultExit.at_traverse`'s own success branch calls
`self.at_post_traverse(traversing_object, source_location)` — and only that branch. Since this call is
an ordinary attribute lookup on `self`, not a `super()` call inside `at_traverse`, a mixin placed
before the base class in MRO that overrides `at_post_traverse` is invoked correctly regardless of
which class in the MRO actually defines `at_traverse` itself. Confirmed directly: `MovementCostMixin.
at_post_traverse` fires exactly once per successful traversal, for a plain `Exit` subclass, a
`DefaultExit`-subclass stand-in that (like `XYZExit`) does not override `at_traverse`, and the real
`XYZExit` itself (D-3).

**`LivingEntity.at_post_move()` was considered and rejected — it fires for too much, and (crucially)
does not reliably fire for too little either, so no `move_type`-based filter can rescue it.** Two
facts, both verified directly, drive this:

1. `DefaultObject.move_to()`'s `quiet` and `move_hooks` parameters are independent. `quiet=True` only
   suppresses `announce_move_from`/`announce_move_to` (the player-visible text); `at_pre_move`,
   `at_object_leave`, `at_object_receive`, and `at_post_move` are gated by `move_hooks` (default
   `True`), not `quiet`. Confirmed by reading `move_to()`'s source and by a live probe
   (`test_quiet_move_to_still_fires_at_post_move`): a `move_to(quiet=True)` call still invokes
   `at_post_move` exactly once. Change 14's own `_relocate_to_default_home(entity)` calls exactly this
   shape — `entity.move_to(default_home, quiet=True)` — during instance-room reclamation, a process
   that runs *inside* `WorldClock.advance()`'s own `_settle_boundary_stages()`. Hooking
   `at_post_move()` generically would make this relocation call `get_world_clock().advance()` again,
   **reentrantly, from inside an already-running `advance()` call** — corrupting the settlement pass
   in progress, not merely mischarging a `move: 30`. This alone rules the hook out.
2. Even setting reentrancy aside, `move_type` cannot discriminate reliably. `DefaultExit.at_traverse`
   passes `move_type="traverse"` into `move_to()`, and `CmdTeleport`/`CmdXYZTeleport` both pass
   `move_type="teleport"` (confirmed: `evennia/commands/default/building.py:1133`, `caller.move_to(
   new_room, move_type="teleport")`; `evennia/contrib/grid/xyzgrid/commands.py:571`, `caller.move_to(
   target, quiet=True)` — the xyzgrid teleport command does not even set `move_type`, defaulting to
   `"move"`). But the **stock `WildernessExit.at_traverse`** (change 13's own model, and the
   `super().at_traverse()` fallback every ordinary wilderness step actually takes) calls
   `traversing_object.at_pre_move(None)` and `traversing_object.at_post_move(None)` **directly**, with
   no `move_type` argument at all — defaulting to `"move"`, the exact same default a generic
   relocation (`_relocate_to_default_home`'s `move_to(quiet=True)`, `CmdXYZTeleport`'s own
   `move_to(target, quiet=True)`) also gets. A `move_type == "traverse"` filter on `at_post_move`
   would silently **exclude ordinary wilderness steps** (which never reach `move_to()` at all — the
   wilderness contrib relocates via a raw `obj.location = room` assignment in
   `WildernessScript.move_obj()`, confirmed by reading `evennia/contrib/grid/wilderness/wilderness.py`
   directly) while still being unable to exclude every backend relocation, since both share the same
   default `move_type`.

`at_traverse`/`at_post_traverse`, by contrast, excludes every non-exit relocation **structurally**,
not by inspecting an argument that turns out not to discriminate reliably: teleports, `spawner.spawn()`
(confirmed by reading `evennia/prototypes/spawner.py` directly — no `move_to()` call anywhere in it;
a spawned object's `.location` starts `None`, exactly like any other fresh `DefaultObject`), and
`_relocate_to_default_home()` never invoke any `Exit`'s `at_traverse` at all, so `at_post_traverse`
cannot fire for them regardless of arguments. Confirmed directly:
`test_teleport_style_move_to_never_charges` and `test_relocate_to_default_home_style_move_never_
charges` both assert zero clock advance for exactly these call shapes.

### D-3. `MovementCostMixin` composes correctly with the real `XYZExit`, verified against the
installed contrib, not a stand-in.

```python
# typeclasses/exits.py
class MovementCostMixin:
    """Charges WorldClock for a successful, player-driven exit traversal. Hooks
    at_post_traverse -- see design.md D-2 for why, not at_traverse's own return value."""

    movement_cost_key: str = "move"

    def at_post_traverse(self, traversing_object, source_location, **kwargs):
        super().at_post_traverse(traversing_object, source_location, **kwargs)
        from world.rules.movement import charge_movement

        charge_movement(traversing_object, self.movement_cost_key)


class Exit(MovementCostMixin, ObjectParent, DefaultExit):
    """Unchanged in every other respect."""


class CostedXYZExit(MovementCostMixin, XYZExit):
    """Every other respect (coordinate tags, .xyz/.xyz_destination, .create()) is inherited
    from XYZExit unchanged; this class adds only the movement-cost hook."""
```

Verified directly, not merely reasoned about MRO in the abstract: `CostedRealXYZExit.create(key=...,
location=room1, destination=room2)` (the actual `evennia.contrib.grid.xyzgrid.xyzroom.XYZExit`
classmethod — `location`/`destination` kwargs bypass the xyz-tag machinery entirely per its own
docstring, so this needs no full grid/scipy path-matrix setup) produces a working exit: traversal
still moves the traversing object to the destination (confirmed via `.location` after the call), and
`get_world_clock().tick` advances by exactly `CLOCK_YAML["command_defaults"]["move"]` — one call, not
zero, not two. `isinstance(exit_obj, XYZExit)` holds. No contrib behavior needed to be reimplemented
or patched.

### D-4. Wiring `CostedXYZExit` into the sample city: one wildcard prototype override, verified
against the real `XYMap.parse()`.

Change 12's sample city spawns its twelve intra-city exits from the `xyzgrid` contrib's own default
`"xyz_exit"` prototype (`typeclass: evennia.contrib.grid.xyzgrid.xyzroom.XYZExit`), applied per-link by
`MapLink.prototype`. Reading `evennia/contrib/grid/xyzgrid/xymap.py::XYMap.parse()` directly shows the
per-link override resolution:

```python
maplink.prototype = flatten_prototype(
    self.prototypes.get(
        node_coord + (direction,),
        self.prototypes.get(("*", "*", "*"), maplink.prototype),
    ),
    no_db=_NO_DB_PROTOTYPES,
)
```

A single `("*", "*", "*")` entry in a map's own `"prototypes"` dict therefore overrides **every**
link's prototype on that map, with no per-coordinate bookkeeping. Verified directly with a real
`XYMap` (a small two-room, one-link map string, not the sample city itself, to avoid needing scipy's
full path-matrix machinery for a two-node graph): a `"prototypes": {("*", "*", "*"): {
"prototype_parent": "xyz_exit", "typeclass": "typeclasses.exits.Exit"}}` entry, after `.parse()`,
resolves both directions' link prototypes to the overridden `typeclass` — confirmed on two
independent links in the parsed map, not just the first one encountered.

**Consequence for change 12.** `world/maps/altoria_capital.py::ALTORIA_CAPITAL_MAP_DATA["prototypes"]`
needs exactly one added entry:
```python
("*", "*", "*"): {"prototype_parent": "xyz_exit", "typeclass": "typeclasses.exits.CostedXYZExit"},
```
Since change 12 is unimplemented, this change cannot edit that file today — it is expressed as a
`MODIFIED sample-city-altoria` delta spec inside this change's own `specs/` directory (D-9), to be
applied against real code once change 12 lands, exactly mirroring how change 13 already expressed its
own `GridRoom` base-class retrofit as a `MODIFIED grid-room-typeclasses` delta rather than a direct
edit to change 12's files.

**The realistic deployment path is a retype of already-existing exits, not a fresh spawn — and that
path does not reliably work within a single running server process, verified directly, not assumed.**
Roadmap order means change 12 is implemented and its sample city's twelve exits already exist as bare
`XYZExit` objects before this change ever adds the wildcard override. `sync_grid()`'s idempotent
`spawn_links()` path does not delete and recreate an exit whose key is unchanged (`differing_keys`,
read directly from `xymap_legend.py::MapNode.spawn_links()`, is computed purely from the symmetric
difference of exit **keys** — "north," "south," etc. — never from typeclass) — it instead falls
through to `spawner.batch_update_objects_with_prototype(prototype, objects=[linkobj], exact=False)`
against the **existing** exit object. Verified directly, with a live probe
(`test_batch_update_retype_does_not_swap_the_already_loaded_instance`), exactly this call shape
against a real, already-`.create()`-d `XYZExit`:
- The underlying DB row's `db_typeclass_path` **is** correctly updated and saved to the new
  `CostedXYZExit` path — confirmed by inspecting `exit_obj.db_typeclass_path` after the call.
- The **already-loaded Python object in the running process is not retyped** —
  `batch_update_objects_with_prototype()` writes the raw field directly; it never calls
  `swap_typeclass()`. `type(exit_obj)` is still `XYZExit` immediately after the "successful" update
  (`changed == 1`), and a traversal through that same in-memory object still does not charge.
- **A fresh query for the same object, in the same process, still returns the old class**, not a
  newly-reconstructed `CostedXYZExit` instance — confirmed by re-fetching via
  `ObjectDB.objects.get(id=...)` immediately after the update and printing the result:
  `same-process re-fetch typeclass = 'XYZExit'` even though `db_typeclass_path` on the row already
  reads the new path. This is Evennia's idmapper object cache returning the same cached Python
  instance for a given primary key within one process, regardless of what the DB row now says —
  consistent with (though not identical in mechanism to) change 12's own D-5 finding about
  `XYZGrid.ndb.grid` staying stale within a process until an explicit reload.

**Consequence, stated plainly rather than left implied.** `evennia reload` (an in-process reload that
preserves the idmapper cache) running `sync_grid()` a second time does **not** reliably retype
already-existing exits for the remainder of that process's life, even though it correctly persists the
new typeclass to the database. A **full process restart** (`evennia stop` then `evennia start`, not
`evennia reload`) does pick up the new `db_typeclass_path`, because a fresh process has no stale
idmapper cache to return instead of re-reading the row — this was not independently re-verified with
an actual stop/start cycle (out of scope for an `EvenniaTest`-based probe), but follows directly from
the confirmed mechanism (the cache, not the DB row, is what is stale).

**Fallback, given this project's zero-user, unreleased posture (matching the reviewer's own
suggestion): discard the dev database rather than rely on the retype path at all.** Since there are no
users and no data worth preserving, the correct operational guidance for implementing this change is:
drop and recreate the SQLite dev database (or run against a fresh volume) so that `sync_grid()` spawns
every exit fresh, as `CostedXYZExit` from the start, via the `Typeclass.create()` branch rather than
the `batch_update_objects_with_prototype()` retype branch. This is the same posture change 12's own
D-5 already established for a different but analogous staleness risk (`XYZGrid.ndb.grid`), and it
avoids depending on a code path this design has now shown does not reliably do what its name implies.
A future project with real users would need a proper migration step (an explicit `evennia py` one-off
that calls `exitobj.swap_typeclass(...)` per exit, or a full stop/start cycle) — out of scope here,
named so a reader does not mistake the absence of one for an oversight.

### D-5. The cost table: `move: 30` covers grid steps, the Limbo bridge, and instance-room doorways;
`wilderness_move: 9000` is unchanged. No third constant is introduced.

| Movement kind | Lineage | Cost key | Value | Wiring |
|---|---|---|---|---|
| Intra-city grid step | `CostedXYZExit` | `move` | 30s | This change (D-3/D-4) |
| Limbo↔grid bridge | `Exit` | `move` | 30s | Free — `Exit` already carries the mixin |
| Instance-room doorway | `Exit` (`spawn_instance_room()`) | `move` | 30s | Free — same reason |
| Wilderness step | `WildernessGateExit`/`WildernessReturnExit` | `wilderness_move` | 9000s | Folded from change 13 (D-1) |

**Why instance-room doorways reuse `move: 30` rather than a new constant.** Design doc §7.1's own
`location_req` schema (`{"layer": "instance", "archetype": "forest_path", "anchor_near": "…"}`) never
states a distance — an instance room is reached through "a specific, narratively-motivated doorway"
(change 14 design.md D-1), which could represent anywhere from an adjoining room to a day's travel,
and no roadmap item through 21 (`scene-builder`, the eventual content producer) supplies one. Inventing
a distance-derived number with no data to derive it from would be exactly the kind of unjustified
constant this project's own conventions reject (design doc §5.1's "simplest correct number, not
apologized for," already cited by both change 12 and 13 for their own arithmetic). `move: 30` — "one
ordinary step through a doorway" — is the simplest defensible number available, and it is the same
number the Limbo bridge (also a single doorway between two conceptually-adjacent spaces) already uses.

**Sanity check between the two live numbers, shown not asserted.** `move: 30` implies roughly
`30 m / 30 s ≈ 3.6 km/h` to `50 m / 30 s = 6 km/h` for a plausible city-block distance (30-50 m) — a
brisk walking pace. `wilderness_move: 9000` was set (change 13 D-5) from an explicit `4 km/h` overland
pace assumption for a 10 km cell. The two numbers were derived independently, by two different
changes, from two different starting facts (an assumed city-block distance vs. a stated continent
area), and land within the same walking-pace order of magnitude (3.6-6 km/h vs. 4 km/h) — they are
mutually defensible side by side, not just individually plausible.

### D-6. Failed traversal charges nothing — structural, not a special case.

Two failure paths, both verified to leave `at_post_traverse` (and therefore `charge_movement()`)
unreached, with no extra guard code required in the mixin:

1. **A locked exit.** `ExitCommand.func` (`evennia/objects/objects.py`) checks
   `self.obj.access(self.caller, "traverse")` **before** calling `self.obj.at_traverse(...)` at all —
   a locked exit's command path never reaches `at_traverse`, let alone `at_post_traverse`. Confirmed
   directly (`test_locked_exit_command_never_calls_at_traverse`): `exit_obj.access(char1, "traverse")`
   is `False` after `locks.add("traverse:false()")`, and the clock is unchanged.
2. **A vetoed `at_pre_move`.** `move_to()` checks `self.at_pre_move(destination, ...)` before
   performing the move; a falsy return aborts the whole call, so `DefaultExit.at_traverse`'s success
   branch (and `at_post_traverse`) never runs. Confirmed directly
   (`test_at_pre_move_veto_charges_nothing`): a stubbed `at_pre_move` returning `False` leaves both the
   traverser's location and the clock unchanged.

No code in `MovementCostMixin` or `charge_movement()` inspects a return value or an error condition to
implement this — it falls out entirely from which hook was chosen (D-2).

### D-7. `AdvanceSource` is always `COMMAND`; movement and combat settlement never overlap.

`charge_movement()` always calls `WorldClock.advance(cost, AdvanceSource.COMMAND, [traversing_object])`
— the identical source `CmdCast` and change 13's own wilderness wiring already use for a successful
player action. No gating on `AdvanceSource.COMBAT` is needed, because movement and combat settlement
are structurally disjoint in this codebase, not merely conventionally kept apart: `world/rules/
disengage.py::_handle_disengage()` (the already-implemented, already-shipped `flee` skill) resolves
entirely through `battlefield.fled.add(str(actor.key))` — read directly, it never calls `move_to()` or
touches any `Exit` object. A fleeing character's location never changes; only their combat-roster
status does. `settle_combat_result()` (combat's own clock settlement, `rounds × 6s`) and
`charge_movement()` (this change) therefore never fire for the same event — there is no path by which
a single flee action could be charged by both, because fleeing is not a movement in this engine's
terms at all.

### D-8. `charge_movement()` only charges when the traverser is a `PlayerCharacter` — forward-looking,
not reactive to an existing bug.

Design doc D4 is explicit: "the world advances only on player action." Nothing in the shipped
codebase today makes an NPC or monster traverse an exit (confirmed: grepping `typeclasses/*.py` and
`world/rules/*.py` for `move_to(`/`at_traverse(` outside doc-comment strings finds no call site), so
this is not an active bug — but a future change (monster wandering, NPC schedules — both named as
unbuilt seams in `typeclasses/npcs.py`/`typeclasses/monsters.py`-equivalents) could add one, and
without this gate it would silently start driving the *global* game clock on its own schedule,
violating D4. `charge_movement()` therefore imports `typeclasses.characters.PlayerCharacter` and
no-ops for anything else, mirroring change 14's own D-6 precedent (gating instance-room reclamation's
occupancy check on `PlayerCharacter` specifically, not `LivingEntity`, for an analogous reason).
Confirmed directly (`test_npc_traversal_does_not_advance_the_clock`): an `NPC`-typeclassed object
traversing a `CostedExit` still moves (the exit itself is unaffected), but the clock does not advance.

`WildernessGateExit`/`WildernessReturnExit` inherit this gate automatically once folded onto
`charge_movement()` (D-1) — change 13's own Non-Goals already state "No monster or NPC population of
the wilderness," so this is currently unreachable there too, but costs nothing to make uniform.

### D-9. The OpenSpec mechanism for change 12 and change 13's capabilities.

Both `sample-city-altoria` (change 12) and `wilderness-gateway` (change 13) exist only inside their
own changes' `specs/` directories today — neither has been archived, so neither capability exists in
`openspec/specs/` yet. Filing a `MODIFIED` delta against a capability that lives only in another
pending change was flagged as a question worth checking, not assuming. Checked directly: change 13's
own `map-wilderness/specs/grid-room-typeclasses/spec.md` is already exactly this shape — a `MODIFIED`
delta against `grid-room-typeclasses`, a capability that exists only inside change 12's own pending
`specs/` directory — and `openspec validate map-wilderness --strict` **passes** today, as does
`openspec validate --all --strict` across the whole repository (both re-run and confirmed as part of
this change, see the Finish section). The `openspec` CLI (v1.6.0) validates a delta spec's own
structure (ADDED/MODIFIED/REMOVED headers, Requirement/Scenario shape) — it does not require the base
capability to already be archived into `openspec/specs/`. This is a real, already-used, already-passing
pattern in this repository, not a novel one this change invents: **a `MODIFIED` delta against a
capability owned by an earlier, dependency-ordered pending change is valid**, on the understanding that
by the time this change is actually implemented, its dependency (change 12 or 13) has already been
archived and the base capability already exists in `openspec/specs/` for the delta to apply against.

**The rule, stated once and applied uniformly to both change 12 and change 13 — corrected from an
earlier draft that applied it only to change 13.** An earlier draft of this section edited change
13's `design.md` directly but left change 12's untouched, reasoning that change 13's own D-8 made a
factual claim this change falsifies while "nothing in change 12's own artifacts makes a claim this
change falsifies." That reasoning was checked too narrowly: change 12's design.md D-4 addendum
states `XYZExit` is "used directly ... this change adds no project-owned `Exit` subclass ... the
contrib class itself is unmodified and remains directly usable elsewhere." Once this change's
`("*", "*", "*")` wildcard override lands (D-4), all twelve of the sample city's links — the only
`xyzgrid` map this project has anywhere in its roadmap — spawn as `CostedXYZExit`, not bare
`XYZExit`. There is no "elsewhere" left where a bare `XYZExit` is actually instantiated. That is the
same shape of staleness D-8 of change 13 had, just phrased differently, and the same corrective rule
applies: **the rule is "any pending, unimplemented change's own prose that this change's own decisions
make factually false gets a direct, in-place edit, regardless of whether that change was named up
front" — not "only the change explicitly named in the task framing gets edited."** Applying that rule
uniformly:
- Change 13's `design.md` (D-5, D-6, D-8, one Non-Goal) is edited directly, in place, because its own
  D-8 claim ("no roadmap item ... is scoped to give it one") is now false.
- Change 12's `design.md` D-4 addendum is likewise edited directly, in place, with a short, dated
  amendment note stating that the "remains directly usable elsewhere" claim no longer holds once this
  change lands, mirroring the amendment already added to change 13's D-8 — see D-4 above for the
  `sample-city-altoria` mechanics this note describes.

Both changes' **formal spec contracts** — `specs/wilderness-gateway/spec.md` (change 13) and
`specs/sample-city-altoria/spec.md` (change 12) — additionally get `MODIFIED`/`ADDED` deltas filed
*inside this change's own `specs/` directory*, never edited in place inside change 12's or change
13's own `specs/` folders. A spec delta, unlike prose in a design document, is the artifact `openspec
archive`/`openspec sync-specs` actually consumes, and the correct way to change a capability's
contract is a delta against it, not a silent in-place rewrite of someone else's already-filed
requirement text — this half of the rule is unchanged from the earlier draft and was already applied
correctly to both changes.

### D-10. Roadmap position and name: `map-movement-clock`, positioned after change 13, not "12b."

The owner's own suggested label, "12b," was offered as an example, not a mandate, and the task that
produced this design explicitly asked whether it was accurate given the change's real dependencies.
It is not: this change depends on change 12 (for `CostedXYZExit`/the sample city's exits) **and**
change 13 (it edits change 13's own `design.md` and files a `MODIFIED wilderness-gateway` delta
folding change 13's bespoke wiring into the shared mechanism — D-1/D-9). A "12b" label would imply a
dependency only on change 12, immediately after it, which understates the real graph.

It does **not** depend on change 14. Instance-room exits inherit the movement cost automatically
once `typeclasses.exits.Exit` carries `MovementCostMixin` (D-5), regardless of whether change 14 has
been implemented yet — `spawn_instance_room()`'s `Exit.create()` call needs no edit, and this
change's own tests exercise the identical mechanism with a synthetic origin/return `Exit` pair rather
than depending on change 14's real code existing (mirroring change 13's own precedent of testing
against stand-in room/exit typeclasses before change 12 had landed).

**Decision: `map-movement-clock`, positioned as roadmap item 13b — after change 13, before change
14.** The `map-` prefix matches changes 12/13/14's own naming convention (this is squarely Phase 3
"World space" content: it closes a gap in how the map layers cost time); the `b`-suffix numbering
matches this project's own established idiom for a small, inserted change with a real dependency on
its immediately preceding sibling (`7b`, `10c`, `10d`, `11b` are all "roadmap-item Nb/Nc/Nd" changes
depending on the item(s) immediately before them, not the phase's first item). Change 14's own
roadmap row (`Depends on: 12, 13`, already amended 2026-08-01) needs no further edit — it does not
depend on 13b, and nothing about its own artifacts changes.

## Risks / Trade-offs

- **[Risk, verified rather than assumed — D-4] Retyping the sample city's already-existing bare
  `XYZExit` instances to `CostedXYZExit` via a second `sync_grid()` run does not take effect for the
  running process's already-cached objects, only for the underlying DB row and any process started
  fresh afterward.** → **Mitigation**: not silently trusted — a live probe confirmed the exact
  mechanism (Evennia's idmapper cache, not the DB row, is what's stale) and this design's own D-4 now
  states the finding plainly rather than claiming the wildcard override retypes unconditionally.
  **Fallback**: discard the dev database and let `sync_grid()` spawn every exit fresh as
  `CostedXYZExit` from the start (this project's zero-user, unreleased posture makes this the correct
  choice rather than building migration tooling for a retype path nothing currently needs to support
  in production).
- **[Risk] A future change that makes an NPC or monster traverse an ordinary exit would need to
  already be aware of the `PlayerCharacter` gate (D-8) to avoid confusion about why the clock does not
  advance for it.** → **Mitigation**: the gate is documented here and inside `charge_movement()`'s own
  docstring; not a design defect (D4 requires exactly this behavior), but worth a future implementer
  reading before assuming any traversal is charged.
- **[Risk] `charge_movement()` centralizes every movement charge into one function; a bug there affects
  all three lineages at once, where three independent bugs would have been more contained but also
  more likely to drift.** → **Accepted**: this is the direct, intended consequence of the unify
  decision (D-1), and the alternative (three independent implementations) is the drift risk D-1 already
  rejected. Mitigated by the shared function being small, pure with respect to its inputs, and covered
  by the verification probe's eleven scenarios (D-2/D-3/D-6/D-7/D-8).
- **[Risk] The `("*", "*", "*")` wildcard prototype override (D-4) affects every link on the sample
  city's map, including any future link added to that same map data by a later content change** — there
  is no per-link opt-out once the wildcard is in place. → **Accepted**: this is the intended behavior
  (every grid exit in the sample city should cost `move: 30`), and a future change wanting a
  differently-costed grid exit would add a more specific `(x, y, direction)` override, which the same
  `XYMap.parse()` resolution order (specific key checked before the wildcard) already supports with no
  further change needed here.
- **[Trade-off] Instance-room doorways and the Limbo bridge reuse `move: 30` with no distance
  justification of their own (D-5), unlike `wilderness_move`'s explicit km/h arithmetic.** →
  **Accepted**: no roadmap item through 21 supplies a distance for instance content, and inventing one
  would be an unjustified number; `move: 30` is the simplest defensible choice available today, and
  callers with unusually short or long in-fiction reasons for a specific instance's distance are free
  to pass a different registered `cost_key` value later (the `movement_cost_key` attribute is per-exit,
  not hardcoded into the mixin itself).

## Verification

Everything below was checked against the installed `evennia==6.1.0` package and this project's own
`world/rules/clock.py`, via `uv run --locked evennia test --settings settings.py
tmp.probe_movement_clock` (`EvenniaTest`-based; a bare `django.setup()` script is insufficient for
`evennia.contrib.grid.xyzgrid.xymap.XYMap.parse()`'s own `flatten_prototype()`/prototype-validation
call path, which needs a real test database — confirmed by hitting `OperationalError: no such table:
scripts_scriptdb` when first tried outside `EvenniaTest`). Twelve tests, all passing:

- `DefaultExit.at_traverse` returns `None` in both the success and failure branch (D-2).
- `MovementCostMixin` hooking `at_post_traverse` charges exactly once on a successful traversal, for a
  plain `Exit` subclass, a `DefaultExit`-subclass stand-in mirroring `XYZExit`'s own lack of
  `at_traverse`/`at_post_traverse` overrides, and — separately — the **real**
  `evennia.contrib.grid.xyzgrid.xyzroom.XYZExit`, created via its own `.create()` classmethod, not a
  stand-in (D-3).
- The `("*", "*", "*")` map-data prototype override resolves every link's typeclass on a real,
  `.parse()`-d `XYMap`, confirmed on two independent links (D-4).
- A locked exit's `ExitCommand`-equivalent access check never reaches `at_traverse` — no charge (D-6).
- An `at_pre_move` veto aborts `move_to()` before `at_post_traverse` fires — no charge (D-6).
- A `move_to(..., move_type="teleport")` call (mirroring `CmdTeleport`) never reaches
  `at_post_traverse` — no charge, because no `Exit` is involved at all (D-2).
- A `move_to(..., quiet=True)` call (mirroring change 14's `_relocate_to_default_home()`) never
  reaches `at_post_traverse` either, for the identical reason — confirmed separately that `quiet=True`
  alone does **not** suppress `at_post_move` (it still fires once), which is exactly why the exclusion
  has to be structural (D-2) rather than relying on `quiet`/`move_type` as a filter.
- An `NPC`-typeclassed traverser moves normally through a `MovementCostMixin`-carrying exit, but the
  clock does not advance — the `PlayerCharacter` gate (D-8) confirmed directly, not merely asserted.
- Retyping an already-`.create()`-d `XYZExit` via `spawner.batch_update_objects_with_prototype()` (the
  exact call `MapNode.spawn_links()`'s idempotent branch makes) correctly updates and saves the DB
  row's `db_typeclass_path`, but does **not** retype the already-loaded Python object in the current
  process, and a same-process re-fetch of the same object still returns the old class — Evennia's
  idmapper cache, not the DB row, is what's stale (D-4).

Probe file: `tmp/probe_movement_clock/test_probe.py` (twelve tests, all passing as of this design;
left in place per instructions, not part of the shipped suite — `tmp/` mirrors change 14's own
`tmp/probe_instance/` precedent for scratch, unshipped verification code).

This supersedes nothing in the top-level design doc's §4 Contrib Reuse Matrix — `XYZExit`'s "Use
directly" call is reconfirmed (a project subclass now exists for the sample city specifically, and the
contrib class itself is unmodified — `CostedXYZExit` is a thin subclass, not a patch to `XYZExit`'s own
code) — in the same spirit as changes 12 and 13's own verification sections. It **does** correct one
narrow, since-superseded claim in change 12's own `design.md` D-4 addendum (not the top-level design
doc): that document's "remains directly usable elsewhere" line was true when change 12 first wrote it
and is no longer true once this change lands — see D-9 above and the matching amendment this change
adds to change 12's own D-4.
