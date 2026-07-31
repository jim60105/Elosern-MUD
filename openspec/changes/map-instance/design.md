## Context

This is roadmap item #14 (design doc §11, Phase 3 "World space"), the last change in Phase 3,
depending on change 12 (`map-anchor-grid`) and, as of this change's own amendment to the design
document (below), change 13 (`map-wilderness`) as well. Change 12 is committed to this repository
but **not yet implemented** — `typeclasses/rooms.py` is still the stock `Room(ObjectParent,
DefaultRoom): pass`, `world/prototypes.py` is still the commented-out tutorial stub, and no
`world/maps/` package exists yet anywhere in the repository (confirmed by direct inspection).
Everything this design says about `GridRoom`/`AnchorRoom`/`SceneArchetypeMixin` describes change 12's
and change 13's own frozen designs for them, which this change builds on without altering their
observable contracts, except for the one deliberate, disclosed extension to change 11's
`_STAGE_ORDER` (D-3).

**The roadmap's dependency graph has been amended to match this design's real prerequisite.** The
roadmap originally listed change 14 as depending only on change 12, treating 13 (`map-wilderness`) and
14 as siblings that merely share change 12 as a common dependency. That was inaccurate: change 13
introduced `typeclasses/rooms.py::SceneArchetypeMixin` specifically so that every future room
typeclass outside the `xyzgrid` hierarchy — its own `TerrainRoom`, and explicitly `InstanceRoom` by
name, per change 13's own design.md D-2 — would have one shared `scene_archetype` seam instead of a
third, independently drifting one. This change adopts that recommendation rather than re-litigating
it: it is a strictly better outcome for change 22 (`art-queue`), which will otherwise have to read
`scene_archetype` off two or three unrelated attribute declarations. Design doc §11's Phase 3 table
has been amended (row 14's `Depends on` cell, `12` → `12, 13`, dated 2026-08-01, recorded inline in
the design document itself) to reflect this as a real, first-class dependency rather than an implicit
one a reader would have to discover by reading this design's own Context section. **Practical
consequence unchanged**: if change 13 has not yet landed when this change is implemented, the
implementer must add `SceneArchetypeMixin` to `typeclasses/rooms.py` first — it is a five-line,
fully-specified class (see change 13's own `scene-archetype-mixin` capability), not a decision this
change needs to make.

**What already exists for this change to build on, unmodified:**
- Change 12's design: `GridRoom(SceneArchetypeMixin, XYZRoom)` / `AnchorRoom(GridRoom)`, and its own
  explicit, reasoned decision *not* to forward-declare `InstanceRoom`: "a stub would be a fake
  implementation, not a seam ... change 14 adds it fresh, with no seam from this change to build on
  beyond `GridRoom` itself."
- Change 13's design: `SceneArchetypeMixin` (a plain mixin carrying `scene_archetype: str | None`,
  unvalidated), adopted by both `GridRoom` (retrofitted) and `TerrainRoom` (new).
- Change 11 (`world-clock`, archived, implemented): `world/rules/clock.py`'s settlement-stage machine
  — a fixed `_STAGE_ORDER` tuple, `register_event_source(kind, source)` as "the only sanctioned way to
  attach a boundary-crossing event query," `ScheduledEvent` (frozen, JSON-safe), and
  `AdvanceSource`. Four world-event kinds (`caravan_arrivals`, `shop_hours`, `quest_deadlines`,
  `npc_schedules`) are already declared in `_STAGE_ORDER` but **none has a registered source yet** —
  every one of them is still an inert, no-op seam in the shipped codebase today. This change is the
  **first real consumer** of `register_event_source()`.
- Design doc §4: "Map · instance layer | `evennia.prototypes.spawner.spawn()` — this is core Evennia,
  not a contrib module ... Use directly. `spawn(*prototypes, caller=None, **kwargs)` on SceneBuilder
  output." §7.2: `SceneBuilder` (change 21, depends on this change) "emits a prototype dict for
  `spawner.spawn()`... The anti-hallucination rule: the LLM never chooses numbers... `prototype_parent`
  must come from a whitelist."

**What genuinely does not exist yet, and is out of this change's scope by roadmap design.** Change 15
(`quest-runtime`) has not built any quest entity or stage-progression model — this change offers it a
location primitive and a pin API, but invents no quest data model of its own. Change 21
(`scene-builder`) has not built the requirements-to-prototype pipeline or its own whitelist validation
logic — this change supplies the prototype whitelist's *storage location* and *one entry*, not
change 21's LLM-facing validation.

## Goals / Non-Goals

**Goals:**
- Define `InstanceRoom` — base class, why it carries no coordinate, and what that implies for
  navigation, `return_appearance`, and map rendering (D-1).
- Define the attach idiom connecting an instance room to the rest of the world, consistent with (but
  simpler than) change 12's Limbo bridge and change 13's wilderness gateway (D-2).
- Give TTL a concrete storage location and a justified, tested position in change 11's fixed
  settlement-stage order (D-3).
- Give design doc D3's "named instance rooms the player interacted with are promoted to permanent" two
  precise, testable operational predicates and one concrete promotion outcome, not a deferral (D-4,
  D-5).
- Specify reclamation's behavior — not silence — when a due room is occupied, holds player-dropped
  items, is pinned by an active quest, or holds an NPC (D-6).
- Leave a whitelist seam for change 21 without inventing its content (D-7).
- Give change 15 a concrete, minimal contract: spawn a location, pin it, done (D-8).
- Verify every Evennia API this design leans on against the installed 6.1.0 package by actually
  running it, not by reading a docstring (Verification section).

**Non-Goals:**
- **No sample instance-room content.** Unlike change 12's sample city or change 13's gateway, the
  roadmap slot for this change ("Instance TTL reclamation, promotion of named rooms") is the mechanism
  itself. Change 21 is the first real content producer; this change's own tests use synthetic,
  test-local prototypes.
- **No multi-room instance dungeons.** Each `spawn_instance_room()` call creates exactly one
  `InstanceRoom`, connected to its `origin_room` by exactly one `Exit` pair. Internal instance-to-
  instance topology (a dungeon with several connected instance rooms) is not addressed — no roadmap
  item through change 21 asks for it, and design doc §7.1's own `location_req` schema names a single
  `archetype`/`anchor_near` pair per stage, not a topology.
- **No nested instances.** `origin_room` is assumed to be a `GridRoom`/`AnchorRoom`/`TerrainRoom` (the
  room the player was standing in when a scene triggered, per §7.2: "Triggered when the player
  actually arrives"), not another `InstanceRoom`. This change does not forbid it structurally, but
  builds and tests nothing for it.
- **No quest data model.** `pin_instance_room()`/`unpin_instance_room()` are reason-keyed, generic
  reference holders with no knowledge of what a "quest" or "stage" is — change 15 owns that.
- **No `SceneArchetype` registry, validation, or art enqueue** (change 22). `scene_archetype` remains
  an attribute seam only, exactly as changes 12/13 left it.
- **No travel-shortcut, search, or "list known instance rooms" command.** A promoted room remains
  reachable only through the specific exit that was created for it — this change adds no discovery
  mechanism beyond that. A legitimate follow-on UX concern, not this roadmap slot's job.
- No backward-compatibility, migration, or deprecation handling — the project is unreleased with zero
  users.

## Decisions

### D-1. `InstanceRoom(SceneArchetypeMixin, DefaultRoom)` — no coordinate, ordinary exit-graph
navigation, stock `return_appearance`, and deliberate absence from every map rendering.

```python
# typeclasses/rooms.py
class InstanceRoom(SceneArchetypeMixin, DefaultRoom):
    """A room on the Instance layer (design doc D3) -- ephemeral, TTL-bounded, spawned through
    core evennia.prototypes.spawner.spawn(), never through xyzgrid. Carries no (x, y, z) of any
    kind; reachability is a plain Evennia exit-graph fact, identical to how Limbo itself works."""

    expire_tick: int | None = AttributeProperty(default=None)   # None = promoted, TTL disabled
    named: bool = AttributeProperty(default=False)
    interacted: bool = AttributeProperty(default=False)
    pin_reasons: list[str] = AttributeProperty(default=list)
    owned_entities: list = AttributeProperty(default=list)       # entities despawned on reclaim (D-6)
    origin_room = AttributeProperty(default=None)                # the room this instance hangs off

    def at_object_receive(self, obj, source_location, move_type="move", **kwargs):
        super().at_object_receive(obj, source_location, move_type=move_type, **kwargs)
        from typeclasses.characters import PlayerCharacter
        if isinstance(obj, PlayerCharacter):
            self.db.interacted = True

    def at_object_delete(self):
        if not super().at_object_delete():
            return False
        if self.db.pin_reasons:
            return False
        from typeclasses.characters import PlayerCharacter
        if any(isinstance(occupant, PlayerCharacter) for occupant in self.contents):
            return False
        return True
```

**Blocking-defect correction (rubber-duck review, recorded here rather than silently fixed).** An
earlier draft of this class gated `at_object_delete()` (and, symmetrically, `reclaim_due_instances()`'s
own occupancy check in D-6) on "any `LivingEntity` present," reasoning it was "strictly safer" than
gating on `PlayerCharacter` alone. That reasoning was safe against destroying an occupied room, but
wrong about what the design actually needs: design doc §7.1/§7.2 has `SceneBuilder` spawn `npc_req`
NPCs directly into a quest stage's instance room, so an NPC's presence is the **normal**, intended
state of a quest scene — not an edge case. Gating occupancy on "any `LivingEntity`" meant a room's
quest-spawned NPC, left behind after its stage completed and unpinned, would defer reclamation on
every single future `advance()` call **forever**, since D-3's own "due stays true forever once past"
property gives it no other way to resolve. This made the change's headline feature non-functional for
the exact content it exists to serve, and no test in the original draft could have caught it, because
this change's own Non-Goals correctly authors no sample NPC content. **Corrected**: occupancy now
gates on `PlayerCharacter` specifically — the real hazard (a live player silently relocated by
`clear_contents()`, verified in Verification) — and non-player entities are handled by D-6's own
despawn/relocate rule instead of blocking reclamation indefinitely.

**Why `DefaultRoom`, not `XYZRoom` or `WildernessRoom`.** Design doc §4 is explicit and was verified
directly (not merely re-quoted): "Map · instance layer | `evennia.prototypes.spawner.spawn()` — this
is core Evennia, not a contrib module ... Use directly." `spawner.spawn()` (verified below,
Verification section) creates plain, typeclass-driven objects with no coordinate concept whatsoever —
there is no `xyz` argument, no map registration, nothing analogous to `XYZGrid.add_maps()`. Giving
`InstanceRoom` a coordinate would mean either (a) inventing a fictitious placement on an existing
`xyzgrid`/wilderness map it does not actually occupy, which is worse than no coordinate (a lie a future
reader could trust), or (b) building an entirely new coordinate space with no consumer — neither
roadmap item 14 nor design doc D3 asks for either. `DefaultRoom` (the same base every stock `Room` and,
transitively, every other room typeclass in this project ultimately descends from) is the correct,
minimal base.

**Why not the project's stock `Room(ObjectParent, DefaultRoom)`, and why no `ObjectParent`.**
Consistency with the two precedents already set: `GridRoom(SceneArchetypeMixin, XYZRoom)` and
`TerrainRoom(SceneArchetypeMixin, WildernessRoom)` both skip `ObjectParent` entirely rather than
routing through the stock `Room` class. `ObjectParent` (`typeclasses/objects.py`) is, as of this
change, an empty mixin — a docstring and nothing else, verified by direct inspection — so this choice
has zero behavioral consequence today. It is an *inherited* risk (an `ObjectParent` method added by
some future change would silently not reach `GridRoom`, `TerrainRoom`, or now `InstanceRoom`), not a
new one this change introduces; fixing it retroactively for all three room types is out of this
change's scope, but adopting the fourth, different pattern (routing `InstanceRoom` through `Room`
while `GridRoom`/`TerrainRoom` bypass it) would make the inconsistency worse, not better.

**Consequences for navigation.** An `InstanceRoom` has no ASCII map, no shortest-path computation, no
`map`/`goto` command support (those come from `XYZGridCmdSet`, installed by change 12 and scoped to
`XYZRoom`-backed space only) — it is reached exclusively by walking through the specific `Exit`
`spawn_instance_room()` creates for it (D-2). This is not a limitation grafted on top of a
coordinate-capable class; it is the same navigation model Limbo itself already uses today, and the
same model the stock `Room` typeclass has always had.

**Consequences for `return_appearance`.** `InstanceRoom` overrides neither `return_appearance` nor
`get_display_desc` — it inherits `DefaultRoom`'s stock implementation unchanged, identically to how
`GridRoom`/`TerrainRoom` do not customize map-specific display beyond what `XYZRoom`/`WildernessRoom`
already provide for themselves. `scene_archetype` (from `SceneArchetypeMixin`) remains pure data for
change 22 to eventually read; nothing in this change makes it affect the room's text description.

**Consequences for map rendering.** An `InstanceRoom` never appears on the `xyzgrid` ASCII map or the
wilderness minimap, by construction — it belongs to neither system. This is the concrete, accepted
cost of D3's own framing ("cheap where it doesn't matter"): instance content is exactly the content
that does *not* need to be discoverable on a world map, because it is reached by walking through a
specific, narratively-motivated doorway, not by navigating coordinates.

### D-2. The attach idiom: one ordinary, ungated bidirectional `Exit` pair — simpler than either prior
layer's idiom, because `InstanceRoom` needs no coordinate-aware exit subclass.

Change 12 established "bridge into a layer with an authored, idempotent exit" (Limbo → grid, one
plain `Exit` pair, idempotent because it is re-created identically at every server start from static
map data). Change 13 established "gateway-exit-pair" (grid ↔ wilderness, requiring
`WildernessGateExit`/`WildernessReturnExit` — full `at_traverse` overrides — because entering and
leaving the wilderness involves coordinate computation `move_to()` cannot express). The instance
layer's own idiom is the third variant, and it is the simplest of the three:

```python
# world/maps/instance.py
def spawn_instance_room(
    origin_room, prototype, *, exit_key, return_key, ttl_seconds=None, named=False, caller=None,
) -> "InstanceRoom":
    if isinstance(origin_room, InstanceRoom):
        raise ValueError(
            "origin_room must not itself be an InstanceRoom -- nested instances are not "
            "supported (see design.md Fix 2 / Risks)"
        )
    _validate_prototype_parent(prototype)                      # D-7
    spawned = spawn(prototype, caller=caller)                  # verified: always returns a list
    if not spawned:
        # spawner.spawn() has an internal `if not prot: continue` branch that can in principle
        # return a shorter list than the input prototype count. Unreachable for a prototype that
        # has already passed _validate_prototype_parent(), but a validated prototype dict is not
        # a formal guarantee spawn() itself makes -- fail loudly rather than raising an opaque
        # IndexError on `[0]` if this branch is ever somehow reached.
        raise RuntimeError("spawner.spawn() returned no object for a validated instance prototype")
    room = spawned[0]
    room.db.expire_tick = get_world_clock().tick + (
        ttl_seconds if ttl_seconds is not None else INSTANCE_YAML["default_ttl_seconds"]
    )
    room.db.named = named
    room.db.origin_room = origin_room
    Exit.create(key=exit_key, location=origin_room, destination=room)
    Exit.create(key=return_key, location=room, destination=origin_room)
    return room
```

**Why `spawn_instance_room()` rejects an `InstanceRoom` as `origin_room` (Fix 2, rubber-duck review).**
Evennia's `delete()` (verified in Verification) removes both every exit located inside the room being
deleted and every exit anywhere whose `destination` is that room. If a *promoted* room's own
`origin_room` were itself an `InstanceRoom` that later gets reclaimed (deleted), both halves of the
promoted room's own attach-exit pair would be destroyed along with it — the promoted room would
survive (its `expire_tick is None` exempts it from the reclamation query entirely, per D-9's query),
but become permanently unreachable, since nothing else in the game would still hold an exit leading to
it. A room that is permanent but unreachable silently violates D3's "promoted to permanent," which
plainly implies still reachable. This is not a hypothetical this change can dismiss: Non-Goals already
disclose that nested/chained instances are untested, but §7.1's `stages` array is a natural place for
a future multi-stage quest to chain a second instance room off wherever the player is currently
standing — including, potentially, an instance room from an earlier stage. Rather than leave that
failure mode to be discovered much later as silent, hard-to-diagnose unreachability, `spawn_instance_
room()` now raises `ValueError` immediately, at the one call site that could create the condition, so
a future violation fails loudly at spawn time.

**Why a plain `Exit`, not a subclass.** Unlike the grid↔wilderness gateway, moving between an origin
room and an instance room is *not* a coordinate computation — it is exactly what Evennia's own
`DefaultExit.at_traverse` already does (`move_to(self.destination)`). There is nothing to override.
This is the same reasoning change 12's own Limbo bridge already used ("using the xyzgrid contrib's own
documented non-grid-to-grid bridging idiom"), generalized: whenever neither side of a connection needs
coordinate math, a plain `Exit` pair is correct and sufficient, and reaching for a subclass would be
inventing structure with no behavior to carry.

**Why no idempotency mechanism, unlike `sync_grid()`/`sync_wilderness()`.** Both prior layers'
attach functions are called at every server start and must not duplicate an exit that already exists
from a previous boot, because they provision *declared, static* content. `spawn_instance_room()` is
called at runtime, once per instance the game actually creates — there is no "re-run at boot" case to
guard against, because nothing calls it at boot. Each call is, by construction, a single creation
event. This is stated explicitly because a reader familiar with changes 12/13's idempotency discipline
might otherwise expect (and miss the absence of) the same guard here; its absence is correct, not an
oversight.

### D-3. TTL lives as an absolute `WorldClock` tick on the room itself; reclamation is a new,
final settlement stage — position justified with a concrete existence-differs proof, not merely
asserted.

**Storage: `InstanceRoom.db.expire_tick: int | None`**, an absolute tick (not a duration), set once at
spawn time to `get_world_clock().tick + ttl_seconds`. Storing an absolute tick rather than a remaining
duration means "is this room due" is a single comparison (`expire_tick <= end_tick`) with no need to
track elapsed time separately — the same reason `WorldClock` itself stores one absolute `tick` rather
than a set of independently-ticking timers (world-clock's own `spec.md`: "`WorldClock` SHALL provide
... a single persisted field, `tick: int`").

**Why not a repeating `Script`.** Verified directly (see Verification section): a `DefaultScript`'s
`interval`/`at_repeat` mechanism is driven by Twisted's `LoopingCall`, a real-wall-clock timer — it
fires according to server uptime, not `WorldClock.tick`. Design doc D4 states "the world advances only
on player action" and world-clock's own archived spec is emphatic on this point ("Real time passing
does not regenerate or expire game state"). A repeating Script would silently violate both: an
instance room would decay while the player is offline and no game time has passed, and would *not*
decay across a long in-game time-skip if the server happened to be restarted in between. TTL must be
computed by the same mechanism every other timed thing in this project already uses:
`WorldClock.advance()`'s settlement stages.

**Registration: a new boundary stage, `"instance_reclamation"`, appended to the end of
`world/rules/clock.py::_STAGE_ORDER`.** `_settle_boundary_stages()` already iterates
`_STAGE_ORDER[5:]` and looks up `_EVENT_SOURCES.get(kind)` for each — the exact, already-built,
already-generic mechanism `register_event_source()` exists for. This change is its first real
consumer; the four existing kinds (`caravan_arrivals`, `shop_hours`, `quest_deadlines`,
`npc_schedules`) have no registered source anywhere in the shipped codebase today (verified by
reading `world/rules/clock.py` directly — `_EVENT_SOURCES` starts empty and nothing populates it).
Adding `"instance_reclamation"` to the tuple is the only edit `_settle_boundary_stages()` itself
needs; the loop already handles an arbitrary-length tail.

**Position: last, after `npc_schedules` — because reclaiming before the stages that can *release* a
room's hold produces a strictly worse observable outcome within the same `advance()` call, not merely
a "different but equally valid" order.** Consider a room that is due for TTL, currently pinned by an
active quest stage (D-6/D-8), and whose owning quest's deadline comes due in the same settlement
window. Change 15 (quest-runtime, not yet built, but its contract is fixed by this change — D-8) will
naturally call `unpin_instance_room()` from within its own registered `quest_deadlines` source when a
deadline resolves.

- **Correct order (`quest_deadlines` before `instance_reclamation`, as declared):** the deadline
  resolves and unpins the room; `instance_reclamation` then runs, finds the room due and unpinned, and
  reclaims (or promotes) it — all within the *same* `advance()` call.
- **Transposed order (`instance_reclamation` before `quest_deadlines`):** `instance_reclamation` runs
  first, finds the room still pinned, and defers it; `quest_deadlines` then unpins it — one call too
  late. The room **still exists** after this `advance()` call and requires a second, unrelated
  `advance()` call before it is ever reclaimed.

This is an existence-differs proof, in the same spirit as world-clock's own `gauge_regen`-before-
`buff_ticks` proof (which showed a differing final `hp` value, not merely "ticked in a different
order") — the two orders produce an observably different world state after one identical `advance()`
call, not just a documented-but-inert reordering.

**`npc_schedules` specifically has no equivalent arithmetic counter-example, and this is now stated
rather than implied.** An earlier draft of this reasoning argued "an NPC that vacates an instance room
as part of its own schedule resolution should be able to make that same room reclaimable within the
same settlement pass" — but that argument was retired by D-6's own blocking-defect correction: NPC
presence no longer blocks reclamation at all (only `PlayerCharacter` does), so an NPC vacating a room
is no longer a precondition for anything `instance_reclamation` checks. `instance_reclamation`'s
position after `npc_schedules` is retained on the weaker, purely structural "last, so nothing after it
could still need the room" reasoning alone — the identical, explicitly acknowledged posture the
`settlement-stage-order` delta spec's own added scenario already takes for `caravan_arrivals`/
`shop_hours` (both still unregistered, no-op seams with no proof of their own either). The one
concrete, tested position claim this design makes is `instance_reclamation` after `quest_deadlines`
specifically, per the pin-release proof above; placing it after `npc_schedules` too costs nothing
(there is no argument for placing it *before* `npc_schedules` either) and keeps it as the single, final
stage, so it is retained without being overclaimed as independently proven.

### D-4. "Named" and "interacted" — two independent, persisted booleans, each set by a distinct,
testable event; never inferred from a string or a registry lookup.

```python
# named: set once, by the caller of spawn_instance_room(), never inferred
room.db.named = named   # explicit keyword argument, default False

# interacted: set at most once, by InstanceRoom.at_object_receive(), the first time a
# PlayerCharacter (not any LivingEntity) enters
```

**Why "named" is caller-declared rather than derived from `key` or `scene_archetype`.** An
inference rule ("named" = key differs from some generic default string, or "named" = has a
non-`None` `scene_archetype`) is exactly the kind of stringly-typed magic this project's registries
otherwise avoid, and it would silently break the moment change 21's `SceneBuilder` starts giving
every instance a real, LLM-authored key regardless of narrative importance — at that point *every*
room would look "named" by a key-based heuristic, defeating the predicate's purpose. An explicit,
required-by-the-caller boolean is the only version of "named" that stays meaningful once change 21
exists: the caller (today, this change's own tests; later, `SceneBuilder`'s own emitted requirement,
per design doc §7.1's `location_req`) is the only party that actually knows whether a location is
narratively disposable scenery or a place worth remembering.

**Why "interacted" is presence-based, not action-based.** A stricter predicate ("interacted" = the
player fought, spoke to an NPC, or picked something up here) would require this change to hook into
`ActionResolver`/combat/dialogue — none of which exist for instance-room content yet (dialogue is
change 19; combat already exists but has no notion of "this room" as a quest-relevant fact). Presence
(`at_object_receive` firing for a `PlayerCharacter`) is the simplest predicate that is still genuinely
meaningful — a scene the player never entered obviously was not interacted with — and it composes for
free with the existing Evennia hook every other move-triggered behavior in this project already uses
(change 13's own gateway exits call `at_pre_move`/announce/`at_post_move`, the identical hook family).
A future change is free to make "interacted" stricter without breaking this change's own contract,
since nothing outside `InstanceRoom` reads *how* `interacted` became `True`, only that it did.

**Why two separate booleans, not one combined "promotable" flag.** `named` is a spawn-time fact,
`interacted` is a runtime fact discovered later, possibly never — collapsing them into one field would
make it impossible to tell, from a room's state alone, whether a still-`False` combined flag meant
"not narratively important" or "important but nobody's been there yet." Keeping them separate makes
both a testable, independently-inspectable predicate, exactly as the task's own framing asked for.

### D-5. Promotion means exactly one thing: `expire_tick` is set to `None`, and nothing else changes.
The room stays an `InstanceRoom`, forever reachable through the identical `Exit` `spawn_instance_room()`
already created.

Of the three options considered — (1) stay `InstanceRoom` with TTL disabled, (2) migrate to the grid
layer, (3) some third representation — option (2) was rejected outright, not merely deprioritized:
`xyzgrid` maps are static, declared `XYMAP_DATA` structures registered once via `XYZGrid.add_maps()`
(verified by change 12's own D-4/D-5 research) — there is no supported "insert one more coordinate
into an already-spawned map at runtime" operation, and inventing one would mean assigning a promoted
room a coordinate that has no relationship to anything around it (which direction from which existing
grid room would even lead to it?). Manufacturing a fake spatial relationship for a room that has no
real one is worse than admitting it has none.

**Option (1), adopted.** Promotion is the routing outcome inside `reclaim_due_instances()` (D-6) when a
due room has no `PlayerCharacter` present, is unpinned, and is both `named` and `interacted`:

```python
room.db.expire_tick = None   # the entire promotion operation
```

No new typeclass, no data migration, no exit change. **Consequences, stated concretely rather than
deferred:**
- **Navigation**: identical to before promotion — the room is still reached exclusively through the
  same `Exit` from the same `origin_room`. "How does a player find it again" has a direct answer: the
  same doorway that led there the first time, which — because promotion by definition never deletes
  the room or its exits — is still there. This is the load-bearing reason D-2's attach idiom creates a
  *permanent*, ordinary `Exit`, not a temporary or instance-scoped one: the exit's own lifetime was
  never tied to the room's TTL in the first place, only the room's `expire_tick` was, so promotion
  requires touching nothing exit-related at all.
- **Discoverability at scale**: not solved by this change (Non-Goals) — a player who forgets which
  origin room led to a promoted instance has no search/list command to fall back on. This is an
  accepted, explicitly named gap, not a silent one; a future change (plausibly alongside `art-queue`'s
  or `webclient-panel`'s own UI work) can add a "known places" journal without touching this change's
  own data model, since `named`/`interacted`/`expire_tick is None` already gives it everything it
  would need to query for.
- **Map rendering**: unaffected — a promoted room still never appears on any `xyzgrid`/wilderness map,
  for the identical reason an un-promoted one doesn't (D-1). Promotion changes *permanence*, not
  *layer membership*.
- **NPCs already in the room**: unaffected — promotion is a `reclaim_due_instances()` routing branch
  distinct from the reclaim branch, and only the reclaim branch calls `_clear_non_player_entities()`
  (D-6). A promoted room's quest-spawned NPC, if any, simply stays exactly where it was, forever, the
  same "nothing else changes" posture promotion already applies to the room and its exits.

### D-6. Reclamation safety: four named hazards, four specified (not silent) behaviors, one
defense-in-depth mechanism verified to actually work — corrected by rubber-duck review to actually
resolve, not merely defer forever, the hazard the design exists to serve.

**Blocking defect, corrected.** An earlier draft of this decision deferred reclamation whenever *any*
`LivingEntity` — including an `NPC` — was present, reasoning this was "strictly safer." It is safe
against deleting an occupied room, but it is not correct: design doc §7.1 has `ScenarioDirector` emit
`npc_req` per quest stage (its own worked example is a "frightened civilian"), and §7.2 has
`SceneBuilder` spawn those NPCs into the `location_req` instance room — an instance room containing an
NPC is the **normal**, intended state of a quest scene, not an edge case. The sequence that broke: a
quest stage pins the room, spawns its NPC, completes, and calls `unpin_instance_room()`; the NPC is
still standing there; the old occupancy check blocked reclamation on the NPC's presence alone; and
because there is no NPC despawn mechanism anywhere in the shipped codebase (nor does any landed or
roadmapped change build one), the room would defer on every `advance()` call **for the rest of the
game's life**, per D-3's own "due stays true forever once past" property. This change's own Non-Goals
correctly authors no sample NPC content, so no test in the original draft could have caught it — the
same failure shape as this phase's two prior changes: a test that exercises the implemented path
rather than the claimed goal. **Corrected below.**

`reclaim_due_instances(start_tick, end_tick)` is `world/maps/instance.py`'s registered source for the
new stage. For every `InstanceRoom` with `expire_tick is not None and expire_tick <= end_tick`
(queried via `InstanceRoom.objects.all()`, filtered in Python — D-9 on why, and its accepted cost):

```python
def reclaim_due_instances(start_tick, end_tick):
    events = []
    for room in InstanceRoom.objects.all():
        expire_tick = room.db.expire_tick
        if expire_tick is None or expire_tick > end_tick:
            continue
        blocking_player = any(isinstance(o, PlayerCharacter) for o in room.contents)
        if room.db.pin_reasons or blocking_player:
            events.append(ScheduledEvent("instance_reclaim_deferred", end_tick, {"room": room.key}))
            continue
        if room.db.named and room.db.interacted:
            room.db.expire_tick = None
            events.append(ScheduledEvent("instance_promoted", end_tick, {"room": room.key}))
            continue
        _clear_non_player_entities(room)
        if room.delete():
            events.append(ScheduledEvent("instance_reclaimed", end_tick, {"room": room.key}))
        else:
            events.append(ScheduledEvent("instance_reclaim_deferred", end_tick, {"room": room.key}))
    return events


def register_owned_entity(room, entity) -> None:
    """Registered by whoever spawns `entity` into `room` -- see D-8. Registered entities are
    despawned (deleted), not relocated, when their room reclaims."""
    owned = room.db.owned_entities or []
    if entity not in owned:
        owned.append(entity)
        room.db.owned_entities = owned


def _clear_non_player_entities(room) -> None:
    """Called immediately before a reclaim (never a promote) deletes `room`. By this point the
    caller has already confirmed no PlayerCharacter is present, so every LivingEntity remaining
    is an NPC or Monster: despawn (delete) it if it was registered via register_owned_entity(),
    otherwise relocate it to settings.DEFAULT_HOME -- the identical non-destructive fallback
    Evennia's own clear_contents() already applies to items (D-6's hazard 2), applied here to
    creatures this change did not spawn and therefore does not own."""
    owned = {obj for obj in (room.db.owned_entities or []) if obj and obj.pk}
    for entity in list(room.contents):
        if not isinstance(entity, LivingEntity):
            continue
        if entity in owned:
            entity.delete()
        else:
            _relocate_to_default_home(entity)
    room.db.owned_entities = []
```

`_relocate_to_default_home(entity)` resolves `settings.DEFAULT_HOME` (`"#N"`) to the actual object via
`ObjectDB.objects.get(id=int(settings.DEFAULT_HOME.lstrip("#")))` and calls `entity.move_to(that
object, quiet=True)` — the identical lookup pattern `DefaultObject.clear_contents()` itself already
uses (read directly, Verification section), not a new convention this change invents.

Each hazard, addressed explicitly:

1. **TTL expires while a player is standing in the room.** The occupancy check is now scoped to
   `PlayerCharacter` specifically — this is the real hazard: a live player silently relocated by
   `clear_contents()` (verified in Verification) if `delete()` were ever called on their room out from
   under them. **Specified behavior: deferred, not deleted.** The room stays exactly as it was;
   `reclaim_due_instances()` re-checks it on every future `advance()` call (the "due" condition,
   `expire_tick <= end_tick`, stays true forever once past — there is no separate "pending"
   bookkeeping to go stale), so the room is reclaimed or promoted the first settlement pass after the
   player leaves.
2. **The room holds player-owned items.** Verified directly (see Verification section):
   `DefaultObject.delete()`'s own `clear_contents()` does **not** destroy contained items — it moves
   each to its `.home`, and for an item whose `.home` is the room being deleted (the common case for
   something dropped there), Evennia's own code redirects it to `settings.DEFAULT_HOME` instead of
   leaving it dangling. **Specified behavior: items survive reclamation, relocated rather than
   destroyed** — this is Evennia's own stock behavior, not a new mechanism this change builds, and it
   was verified rather than assumed because "items are moved, not destroyed" is exactly the kind of
   claim a plausible-looking but unverified call sequence could get backwards.
3. **An active quest still references it.** Change 15 does not exist yet, so this change cannot check
   "is a quest active" directly — and must not invent quest-runtime's own data model to do so. The
   `pin_reasons: list[str]` seam (D-8) is the generic answer: any reason string in the list blocks
   reclamation, checked identically to player occupancy. **Specified behavior: deferred while
   pinned**, regardless of what put the pin there.
4. **An NPC the player has a relationship with is inside — now resolved, not merely deferred forever.**
   An NPC's presence alone no longer blocks reclamation (the corrected rule above). Instead:
   - **Registered (spawned deliberately for this scene via `register_owned_entity()`)** → despawned
     (`entity.delete()`) as part of reclaiming the room — a quest-spawned "frightened civilian" is
     throwaway content whose lifetime is meant to match its scene's, exactly like the room itself.
   - **Unregistered (present for any other reason — a wandering monster, an NPC this change's own
     `register_owned_entity()` seam was never called for)** → relocated to `settings.DEFAULT_HOME`,
     never deleted. This is deliberately the *same* non-destructive policy already verified for items
     (hazard 2), applied uniformly to creatures this change does not know it owns, so the room's
     contents policy has one rule, not one for objects and a different one for creatures.
   Whether a *relationship* specifically exists is still not modeled by this change (no
   `RelationHandler` consumer here) — it does not need to be, because neither outcome (despawn a
   scene's own throwaway NPC, or relocate an NPC this change doesn't recognize) destroys anything a
   relationship could be attached to without at least relocating it first.

**Defense-in-depth, verified, and now consistent with the corrected occupancy rule.**
`InstanceRoom.at_object_delete()` (D-1) re-checks pins and `PlayerCharacter` presence and returns
`False` — verified directly (Verification section) to actually abort `DefaultObject.delete()`, not
merely document an intention — independently of `reclaim_due_instances()`'s own pre-delete check. By
the time `reclaim_due_instances()` calls `room.delete()`, `_clear_non_player_entities()` has already
emptied the room of every `LivingEntity`, so the safety net and the normal path agree; and even a
stray direct `room.delete()` call elsewhere in the codebase that skips `_clear_non_player_entities()`
entirely still cannot lose an NPC to silent destruction, because Evennia's own `clear_contents()`
(verified, hazard 2's mechanism) relocates any remaining occupant — including a `LivingEntity` — to
`DEFAULT_HOME` rather than destroying it. The only entity a bypassing direct `.delete()` call could
fail to *despawn* correctly is a registered, owned one (it would be relocated instead of deleted) —
a strictly safer failure mode than the alternative, not a new hazard.

### D-7. The change-21 seam: a one-entry, explicit whitelist tuple — not a registry with validation
logic, since none is needed yet.

```python
# world/maps/instance.py
INSTANCE_PROTOTYPE_WHITELIST: tuple[str, ...] = ("instance_room",)

def _validate_prototype_parent(prototype: dict) -> None:
    parent = prototype.get("prototype_parent")
    if parent not in INSTANCE_PROTOTYPE_WHITELIST:
        raise ValueError(
            f"prototype_parent {parent!r} is not in INSTANCE_PROTOTYPE_WHITELIST"
        )
```

`world/prototypes.py::INSTANCE_ROOM = {"typeclass": "typeclasses.rooms.InstanceRoom", "desc": "..."}`
— per Evennia's own module-prototype loading rule (verified directly, Verification section: without an
explicit `"prototype_key"`, the module-level variable name is lowercased and used instead), this
resolves to `prototype_key = "instance_room"` automatically, with no explicit key needed — matching
`GRID_ROOM`/`ANCHOR_ROOM` → `"grid_room"`/`"anchor_room"`'s already-established convention from change
12. Because `settings.PROTOTYPE_MODULES` already defaults to `["world.prototypes"]` (verified against
`evennia/settings_default.py`), and change 12 adds no entry that removes it, **this change requires no
settings.py edit at all** for the whitelist to resolve.

**Why this satisfies §7.2's anti-hallucination rule without inventing change 21.** The rule is
"`prototype_parent` must come from a whitelist" — this change builds the whitelist's storage location
and its enforcement point (`_validate_prototype_parent()`, called unconditionally inside
`spawn_instance_room()`, so there is no path to spawning an instance room that bypasses it), and
populates it with the one entry this change itself needs. Change 21 extends
`INSTANCE_PROTOTYPE_WHITELIST` with whatever additional `prototype_parent` values its own archetype
system needs (for example, per-archetype prototype parents distinguishing a "forest path" instance
from a "dungeon chamber" instance) — a data addition to an already-open tuple, exactly the "declare a
keyed registry/whitelist, populate later" idiom `ANCHOR_PLACEMENT_REGISTRY` and
`WILDERNESS_ENTRY_REGISTRY` already established twice. This change does not decide, and does not need
to decide, what those future entries will be.

### D-8. The change-15 contract: two functions and four readable fields, nothing else.

Change 15 (`quest-runtime`) depends on this change specifically because quest stages need somewhere to
happen — design doc §7.1's own `ScenarioDirector` output example already names `"location_req": {
"layer": "instance", "archetype": "forest_path", "anchor_near": "…", "scene_sentence": "…" }` for a
`reach_location` stage objective. This change's contract to change 15 is deliberately small:

- **`spawn_instance_room(origin_room, prototype, *, exit_key, return_key, ttl_seconds=None,
  named=False, caller=None) -> InstanceRoom`** — the location for a quest stage. `named=True` is the
  quest author's own call (a notable dungeon boss chamber vs. throwaway travel scenery); this change
  makes no attempt to guess narrative importance on the quest system's behalf.
- **`pin_instance_room(room, reason: str)` / `unpin_instance_room(room, reason: str)`** — called when
  a stage begins using a room and when it stops (completion, failure, or player abandonment). Reasons
  are free-form strings scoped entirely to the caller (this change never inspects their content beyond
  membership), so a quest-runtime pin reason like `f"quest:{quest_id}:stage:{stage_index}"` and any
  future, unrelated subsystem's own pin reason cannot collide in a way that causes one to
  accidentally release the other's hold — `unpin_instance_room()` removes only the exact reason string
  passed in.
- **`register_owned_entity(room, entity)`** — **whoever calls `spawner.spawn()` to create an NPC (or
  any entity) meant to live only for that instance room's own scene must call this immediately after
  spawning it.** Per design doc §7.2, that is change 21 (`scene-builder`), not change 15 directly —
  `SceneBuilder` is what actually spawns `ScenarioDirector`'s `npc_req` into the room `location_req`
  names. Quest-runtime's own role is triggering that spawn (by asking for a stage's location and NPCs
  to exist) and, if it ever spawns an entity directly itself, registering that entity the same way. An
  entity never registered here is not destroyed when its room reclaims — it is relocated to
  `settings.DEFAULT_HOME` instead (D-6, hazard 4) — so forgetting to call this is a leak, not a data
  loss, but it is still each spawner's own responsibility to call it, since this change has no way to
  infer which entities in a room it is safe to despawn versus merely passing through.
- **Four readable fields**: `room.db.expire_tick`, `.db.named`, `.db.interacted`, `.db.pin_reasons` —
  available for quest-runtime to introspect (for example, to warn a player narratively that an
  unpinned, unpromoted location "feels like it won't last") without this change needing to anticipate
  that specific use.

This is intentionally the entire contract. Quest-runtime's own stage-progression model, deadline
tracking, and reward settlement are its own charter, not this change's.

### D-9. Query mechanism for due rooms: `InstanceRoom.objects.all()`, filtered in Python — verified to
actually filter by typeclass, and one real pitfall recorded so it is not rediscovered.

Verified directly (Verification section): `MyTypeclass.objects.all()` (the same idiom change 12's own
`GridRoom.objects.filter_xyz` already relies on for its underlying manager) returns only objects whose
typeclass matches `MyTypeclass` exactly — not every `Object` in the database. This is the query
`reclaim_due_instances()` uses, then filters `expire_tick`/occupancy/pins in ordinary Python, exactly
mirroring change 12's own D-5 "accept the cost at the current, small scale" posture rather than
building an indexed query no current content needs.

**A pitfall found and rejected, recorded so it is not repeated**: `evennia.utils.search.search_object`
looks like the more idiomatic search entry point and accepts a `typeclass=` keyword, but its first
positional argument, `searchdata`, is *not* optional the way its docstring's phrasing ("`None`
(default) returns all objects") might suggest for this call shape — passing `search_object(None,
typeclass=...)` was verified to return an **empty** result, not "everything of that typeclass." The
`.objects.all()` idiom, not `search_object`, is the correct, verified mechanism for "give me every
room of this type."

**Accepted, unsolved cost**: every `advance()` call touches every `InstanceRoom` row, including
already-promoted ones (`expire_tick is None`) that will never again need reclaiming. Over a long game
this list only grows. Named in Risks/Trade-offs, not solved here — matching change 12's own D-5
precedent for the identical class of "accept now, revisit if it ever actually matters" cost.

**TTL default arithmetic (`world/rules/rulebook/instance.yaml::default_ttl_seconds`)**: 4 in-game
days, `4 * hours_per_day * seconds_per_hour = 4 * 24 * 3600 = 345,600` — a clean multiple of the
calendar constants already in `clock.yaml`, auditable at a glance. Chosen to comfortably exceed design
doc §7.1's own example quest failure deadline (`"deadline_hours": 72` = 259,200 s) by roughly a third,
so an unpinned, forgotten quest location's TTL default does not race a typical quest deadline —
though D-6's pin mechanism, not this default, is what actually guarantees safety; the default is a
reasonable starting policy, not the safety net.

## Risks / Trade-offs

- **[Risk] `InstanceRoom.objects.all()` scans every instance room, including permanently-promoted
  ones, on every single `advance()` call.** → **Mitigation**: none added here (Non-Goal, D-9); accepted
  at the current, single-player, TTL-bounded scale, matching change 12's own D-5 precedent for
  accepting a linear-scan cost until it is a demonstrated problem. **Note (rubber-duck review):** an
  earlier draft of this design also had NPC-occupied due rooms deferred *forever* (the D-6 blocking
  defect, now corrected), which would have made this scan's growth genuinely unbounded — every
  quest-spawned scene with an NPC left behind would have accumulated as a permanent, never-resolving
  entry. With that defect fixed, this risk reverts to exactly the bounded magnitude D-9 already
  accepted: the scan's steady-state size is driven by rooms still-in-progress (player currently
  present) plus deliberately promoted rooms (a comparatively rare, intentional outcome), not by an
  ever-growing population of scenes nobody could ever finish. The growth this bullet originally named
  was a consequence of that now-fixed defect, not an independent risk of the query mechanism itself.
- **[Risk] A promoted room whose `origin_room` is itself later-reclaimed `InstanceRoom` becomes
  permanent but unreachable.** Evennia's `delete()` removes every exit inside the deleted room and
  every exit anywhere pointing at it (verified, Verification section); a promoted room's `expire_tick
  is None` exempts it from ever being revisited by `reclaim_due_instances()`, so nothing would ever
  re-attach it once its `origin_room` (if that origin were itself an instance room) is gone. → **Fixed,
  not merely mitigated (Fix 2, rubber-duck review)**: `spawn_instance_room()` now raises `ValueError`
  when `origin_room` is an `InstanceRoom`, so the precondition for this failure mode can never be
  created in the first place (D-2). Nested/chained instance topologies remain a Non-Goal this change
  does not otherwise support, but the specific silent-unreachability consequence is now structurally
  impossible rather than merely undocumented.
- **[Risk, fixed at the source] The roadmap's formal dependency graph originally understated this
  design's real prerequisite on change 13's `SceneArchetypeMixin`.** → **Resolved, not merely
  mitigated**: design doc §11's Phase 3 table (row 14) has been amended in place (`12` → `12, 13`,
  Fix 3 / rubber-duck review), so the architectural source of truth itself now states the real
  dependency — this is no longer a gap a reader has to discover only by reading this change's own
  Context section. The implementation-time fallback (add the five-line mixin directly if 13 has
  somehow not landed first despite the corrected dependency) remains named in Context as a defensive
  note, not because the roadmap is still wrong.
- **[Trade-off] `named` is entirely caller-declared, with no fallback heuristic.** A caller that
  forgets to pass `named=True` for a location that should have been promotable simply won't be —
  silently, from that caller's point of view. → **Accepted**: the alternative (inferring importance
  from `key` or `scene_archetype`) was rejected in D-4 as unstable under change 21's own future
  behavior; an explicit, caller-owned decision is the only version of this predicate that stays
  meaningful once `SceneBuilder` exists.
- **[Trade-off] `interacted` is presence-only, not action-based.** A player who steps into a room and
  immediately leaves without doing anything narratively meaningful still flips `interacted` to `True`.
  → **Accepted**: D-4's own reasoning — the stricter predicate has no consumer to hook into yet
  (dialogue/combat-in-instance-rooms are later changes), and presence is still a genuine, non-trivial
  fact ("the player was here"), not an arbitrary default.
- **[Risk] A promoted room has no discovery mechanism beyond the one exit that already leads to it.**
  → **Mitigation**: none added here (Non-Goal, D-5); the data (`named`, `interacted`, `expire_tick is
  None`) needed to build one later already exists, so a future change can add it without touching this
  change's model.
- **[Risk] `pin_reasons` is a plain list with no owner registry — a caller could in principle pin with
  a reason string another subsystem also happens to use, colliding silently.** → **Mitigation**: not
  solved here; the contract (D-8) recommends namespaced reason strings (`"quest:<id>:stage:<n>"`) as
  convention, not enforcement, since no second real consumer exists yet to design a stronger contract
  against.

## Verification

Everything below was checked against the installed `evennia==6.1.0` package in this project's own
`uv`-managed environment, via a scratch `EvenniaTest`-based probe
(`tmp/probe_instance/test_probe.py`, left in place — not part of the shipped suite), run with
`uv run --locked evennia test --settings settings.py tmp.probe_instance`. All eleven probe tests pass
(nine from the original round, two added for the rubber-duck-review fix below).

- **`evennia.prototypes.spawner.spawn(*prototypes, caller=None, **kwargs)`** — confirmed by direct
  call: always returns a **list**, one entry per prototype argument, even for a single prototype dict
  (`spawn(one_dict)[0]` is the pattern this design's own `spawn_instance_room()` uses). `caller` is
  confirmed optional for a prototype with no `$`-protfuncs. A spawned room's `.location` is `None` by
  default, exactly like any other `DefaultRoom` — confirming `InstanceRoom` needs no special handling
  to end up "nowhere" the way every other room already is.
- **`prototype_parent` chaining** — confirmed by spawning a child prototype (`prototype_parent:
  "probe_room_parent"`) against a `prototype_parents={...}` dict supplied directly to `spawn()`: the
  child correctly inherited an Attribute (`desc`) declared only on the parent, confirming the same
  inheritance mechanism `GRID_ROOM`/`ANCHOR_ROOM`'s `"prototype_parent": "xyz_room"` chaining (change
  12) already relies on works identically for a plain, non-`xyzgrid` prototype tree.
- **Module-prototype key inference** — confirmed by reading `evennia/prototypes/prototypes.py::
  load_module_prototypes()` directly: without an explicit `PROTOTYPE_LIST` in a prototype module, every
  global-level dict becomes a prototype, and if it has no `"prototype_key"` of its own, "the variable
  name will be used" (lowercased) — confirming `INSTANCE_ROOM = {...}` resolves to `prototype_key =
  "instance_room"` with no extra field needed, exactly matching `GRID_ROOM`/`ANCHOR_ROOM`'s already-
  shipped-design convention.
- **`PROTOTYPE_MODULES` default** — confirmed by reading `evennia/settings_default.py` directly:
  `PROTOTYPE_MODULES = ["world.prototypes"]`, unconditionally present with no settings edit needed by
  this change.
- **`DefaultObject.delete()` and contained items** — confirmed by direct test: deleting a room
  containing a dropped item does **not** destroy the item (it still exists in `ObjectDB` afterward,
  under a different, non-`None` location) — `clear_contents()` relocates rather than destroys,
  verified rather than assumed.
- **`DefaultObject.delete()` and exits, both directions** — confirmed by direct test: deleting a room
  removes both (a) any exit anywhere in the database whose `destination` is that room (`clear_exits()`'s
  `ObjectDB.objects.filter(db_destination=self)` branch) and (b) every exit *located inside* the room
  being deleted, regardless of where that exit itself points. Together these two facts are exactly what
  makes `InstanceRoom.delete()` alone sufficient to clean up an entire `spawn_instance_room()` attach
  pair with no additional exit-deletion code in this change.
- **`DefaultObject.delete()` on an occupied room is dangerous, confirmed rather than assumed** —
  deleting a room containing a live character does **not** raise or refuse; it silently relocates the
  character (via the same `clear_contents()` path items take). This is the concrete, verified fact that
  justifies D-6's occupancy check running *before* any `delete()` call is ever attempted, rather than
  trusting Evennia's own deletion path to be safe by default.
- **`at_object_delete()` returning `False` aborts deletion** — confirmed by direct test: a room
  subclass whose `at_object_delete()` returns `False` while a `db.pinned` flag is set survives a
  `.delete()` call entirely (the object, and its `pk`, still exist afterward); once the flag is
  cleared, an identical `.delete()` call succeeds. This is the exact mechanism D-1's/D-6's
  defense-in-depth override relies on, verified to actually work rather than merely documented as
  Evennia's stated intent.
- **`MyTypeclass.objects.all()` filters by typeclass, not globally** — confirmed by direct test:
  spawning two rooms of two different typeclasses and querying each typeclass's own `.objects.all()`
  returns exactly the matching subset, never the other. `evennia.utils.search.search_object(None,
  typeclass=...)` was also tried and confirmed to return an **empty** result for this call shape — a
  real pitfall, recorded in D-9 so a future implementer does not rediscover it the hard way.
- **`DefaultScript`'s repeat timing is wall-clock, not game-tick, and a non-repeating Script never
  fires `at_repeat`** — confirmed by direct test (a `Script` created with `interval=0, repeats=0` never
  invokes an overridden `at_repeat()`), and by reading `evennia/scripts/scripts.py` directly: the
  underlying `ExtendedLoopingCall` wraps Twisted's real-time `LoopingCall`, with no game-tick awareness
  anywhere in its scheduling path. This is the direct confirmation for D-3's core claim: TTL cannot
  correctly be a repeating Script, and must be a `WorldClock`-settlement-stage computation instead.
  (One test-authoring detail recorded so it is not mistaken for a defect: `create_script(...,
  interval=0)` reads back as `db_interval == -1`, not literal `0` — an internal storage sentinel with
  no bearing on this design, since what matters, and what was independently confirmed, is that the
  timing component never starts either way.)

- **`_relocate_to_default_home()`'s DEFAULT_HOME-lookup-plus-`move_to()` pattern actually works,
  verified directly (rubber-duck-review fix)** — confirmed by direct test: resolving
  `settings.DEFAULT_HOME` via `ObjectDB.objects.get(id=int(settings.DEFAULT_HOME.lstrip("#")))` and
  calling `entity.move_to(default_home, quiet=True)` moves an NPC-typed character out of a room
  without destroying it (it still exists afterward, at the resolved default-home location, no longer
  among the room's `contents`) — the same lookup `DefaultObject.clear_contents()` performs internally,
  now confirmed to work identically when called explicitly, outside of a `delete()` flow, which is how
  `_clear_non_player_entities()` actually uses it (D-6).
- **The despawn-then-delete sequence itself, verified end-to-end** — confirmed by direct test:
  clearing every `LivingEntity` from a room first (deleting an "owned" one, relocating an "unowned"
  one via the helper above) and only then calling `.delete()` on the room succeeds cleanly, with the
  owned entity actually gone from the database afterward and the unowned one surviving, relocated —
  the exact sequence D-6's corrected `reclaim_due_instances()` relies on.

This supersedes nothing in design doc §4's "Use directly" call on `evennia.prototypes.spawner.spawn`
— it is the call-signature-level addendum that call did not need to go to, in the same spirit as
changes 12 and 13's own verification sections.
