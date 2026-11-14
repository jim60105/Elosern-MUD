# Design

## Context

Design document: `docs/superpowers/specs/2026-11-14-landmark-rites-design.md` §7 (record), §9 (settlement), §13 (errors), §14 (observability). Existing code this change builds on, read on 2026-11-14:

- `world.lore.rites.current()` and the shapes of `world/lore/rites/shape.py` (`landmark-rite-content-model`). `current()` raises `RitesNotLoaded` when nothing is installed.
- `world.lore.map_districts.current().districts` (district key -> declaration with `district_name_zh`, `landmark_name_zh`) and `world.lore.map_districts.landmark_node_ids()` (district key -> canonical node id).
- `world.rules.map_knowledge._derive_node_id(location)` (private; this change adds a public alias).
- `world.rules.party_scope`: `resolve_commander(acting)`, `authorize_member(commander, member_id, PURPOSE_ACT, anchor=acting)`, `present_party_scope(acting)`, `party_in_combat(acting, *members)`, `live_companions(commander)`, `PartyScopeError`.
- `world.rules.time_skip`: `advance_wait(actor, seconds, *, operation_id=None) -> SkipResult` (fields `elapsed_seconds`, `operation_id`), `admit_contact_before_action(actor)`.
- `world.rules.skip_safety.evaluate_skip_safety(actor)`; `world.rules.mental_time.planned_seconds(scope, requested, *, tick)`; `world.rules.clock`: `get_world_clock`, `advance_scope`, `AdvanceSource`, `build_advance_snapshot_registry`, `_snapshot_clock_tick`, `_restore_clock_tick`, `_restore_advance_registry`.
- `world.rules.pleasure.apply_pleasure_gain(entity, gain)`; `entity.sexual.shame` / `.exposure` are clamped ordered-level traits (`.value += n`); `entity.sexual.climax_today`, `entity.sexual.climax_phase.level`.
- `world.rules.dialogue.live_dialogue_session(character)`; `world.rules.fatigue.sleep_blocks_actions(entity)`.
- `world.rules.surfaces`: `attribute_snapshot(obj, key)`, `restore_attribute_best_effort(obj, key, snapshot)`.
- The rollback pattern to copy is the prayer rite in `world/rules/church.py` (the block that builds `build_advance_snapshot_registry`, opens `transaction.atomic()`, and restores the clock tick, the registry and an attribute snapshot in `except Exception`).

## Goals / Non-Goals

**Goals**

- One rules-level owner of the record and of the settlement, callable by a later action adapter and text command.
- A failure anywhere leaves no time, sexual state or record change.

**Non-Goals**

- No action registration, text command, panel, webclient or documentation of commands (`landmark-rite-action`, `landmark-rite-panel`).
- District lighting is unchanged: `lit_district_keys` still reads visited landmarks (`landmark-rite-lighting`).
- No presentation state (`ndb` delivery) and no map-panel publication; the caller owns publication.
- One option produces at most one climax. No loop of several advances.
- No reward: no merit, copper, experience grant, item or quest progress is written by this module (the clock's own experience and milestone rules still run inside the advance).
- If a test shows the lower duration bound (120 seconds) does not end the climax inside the advance, stop and report it. Do not change bounds, add a second advance or call `apply_event` directly.

## Decisions

### D1. Public node read (`world/rules/map_knowledge.py`)

Add `def node_id_for(location: Any) -> str | None:` that returns `_derive_node_id(location)`, and export it in `__all__` if the module has one. Change no existing caller.

### D2. Record module (`world/rules/landmark_rite_record.py`)

```python
RECORD_ATTR = "landmark_rites"
SCHEMA_VERSION = 1

class LandmarkRiteRecordError(ValueError): ...

def empty_record() -> dict: ...                      # {"schema_version": 1, "completed": {}}
def validate_record(value: Any) -> dict: ...         # plain-dict deep copy, or raises
def read_record(owner: Any) -> dict: ...             # missing attribute -> empty_record(); never writes
def completed_district_keys(owner: Any) -> frozenset[str]: ...
def seen_option_keys(owner: Any, district_key: str) -> tuple[str, ...]: ...   # stored order
def with_completion(record: dict, district_key: str, option_key: str, tick: int) -> dict: ...  # pure, returns a new dict
def write_record(owner: Any, record: dict) -> None: ...   # validate_record, then owner.attributes.add(RECORD_ATTR, record)
```

`read_record` reads `owner.attributes.get(RECORD_ATTR)` and converts Evennia saver containers to plain containers with `evennia.utils.dbserialize.deserialize` before validating.

Envelope (design §7.1), each violation raising `LandmarkRiteRecordError`:

- top level is a mapping with exactly `schema_version` and `completed`; `schema_version` is the non-bool integer `1`; `completed` is a mapping;
- each district key is a non-empty string; each district entry is a mapping with exactly `first_tick`, `last_tick`, `count`, `options`;
- `first_tick`, `last_tick` are non-bool integers `>= 0` with `first_tick <= last_tick`; `count` is a non-bool integer `>= 1`;
- `options` is a mapping; each option key is a non-empty string; each option entry is a mapping with exactly `count` (non-bool integer `>= 1`) and `last_tick` (non-bool integer `>= 0`).

`with_completion`: a new district entry is `{first_tick: tick, last_tick: tick, count: 1, options: {option_key: {count: 1, last_tick: tick}}}`. An existing entry increments `count`, sets `last_tick = tick`, keeps `first_tick`, and increments or creates the option entry. Every other district and option entry is copied unchanged, including keys the current content does not declare.

This module imports nothing from `world.lore.rites`; it does not know which keys are declared.

### D3. Settlement module (`world/rules/landmark_rites.py`)

```python
class RiteRefused(Exception):
    code: str
    message: str      # player-facing zh-TW text from REFUSAL_MESSAGES

REFUSAL_MESSAGES: dict[str, str] = {
    "rite_no_landmark": "這裡沒有可以進行儀式的地標。",
    "rite_unknown_option": "這個地標沒有這樣的儀式。",
    "rite_member_unavailable": "這位隊友現在無法進行儀式。",
    "rite_no_watch_scene": "這個儀式只能親自進行。",
    "rite_record_corrupt": "儀式紀錄無法讀取，請聯絡管理者。",
    "rite_unavailable": "現在無法進行儀式。",
    "rite_unsafe": "附近有危險，無法進行儀式。",
    "rite_interrupted": "現在沒有足夠的時間完成儀式。",
}

@dataclass(frozen=True, slots=True)
class RiteSite:
    district_key: str
    district_name: str
    landmark_name: str
    archetype: RiteArchetype

@dataclass(frozen=True, slots=True)
class RitePlan:
    owner: Any          # record owner (PlayerCharacter)
    body: Any           # acting body
    site: RiteSite
    option: RiteOption
    perspective: str    # "self" | "watch"

@dataclass(frozen=True, slots=True)
class RiteResult:
    plan: RitePlan
    scene: Scene        # option.self_scene or option.watch_scene
    tick: int           # world tick after the advance
    elapsed_seconds: int
    first_completion: bool   # the district had no entry before this rite
    climax: bool
    operation_id: str

def record_owner_for(actor: Any) -> Any: ...
def rite_site_for(owner: Any) -> RiteSite | None: ...
def eligible_performers(actor: Any) -> tuple[Any, ...]: ...
def preflight(actor: Any, option_key: str, member_id: int | None = None) -> RitePlan: ...
def perform_rite(actor: Any, option_key: str, member_id: int | None = None, *, operation_id: str | None = None) -> RiteResult: ...
```

`actor` is the controlled character (the body the session drives).

**`record_owner_for(actor)`**: `resolve_commander(actor)`; a `PartyScopeError`, or a commander that is not a `typeclasses.characters.PlayerCharacter`, raises `RiteRefused("rite_unavailable")`.

**`rite_site_for(owner)`**: return `None` at once unless `owner.location` is a `typeclasses.rooms.GridRoom` or `TerrainRoom` (a landmark node is always one of the two). `node = node_id_for(owner.location)`; `None` -> `None`. The district is found through a reverse mapping node id -> district key built from `landmark_node_ids()` once per published district snapshot: keep a module-level pair `(snapshot_object, mapping)` and rebuild only when `map_districts.current()` returns a different object (`is not`), because `landmark_node_ids()` rebuilds a reference index over every settlement node on each call and this function runs on every presentation snapshot. Read `from world.lore import map_districts` and call `map_districts.landmark_node_ids()` and `map_districts.current().districts` through the module (tests patch those two attributes). Find the district whose node id equals `node`; none -> `None`. `world.lore.rites.current().archetype_for(key)`; `RitesNotLoaded` or `None` -> `None`. Return the site with `district_name = declaration.district_name_zh` and `landmark_name = declaration.landmark_name_zh`. Pure read.

**`eligible_performers(actor)`**: the actor first, then each member of `present_party_scope(actor)` other than the actor for which `authorize_member(owner, member.id, PURPOSE_ACT, anchor=actor)` does not raise, in scope order. Pure read.

**`preflight`** (reads only), in this order; the first failure raises `RiteRefused`:

1. `owner = record_owner_for(actor)`; `owner.location is not actor.location` -> `rite_unavailable`.
2. `site = rite_site_for(owner)`; `None` -> `rite_no_landmark`.
3. `option = site.archetype.option(option_key)`; `None` -> `rite_unknown_option`.
4. Body: `member_id is None` or `member_id == actor.id` -> the actor. Otherwise `authorize_member(owner, member_id, PURPOSE_ACT, anchor=actor)`; `PartyScopeError` -> `rite_member_unavailable`. Perspective is `self` exactly when `body is owner`, else `watch` (so a possessed companion acting as the controlled character performs in the `watch` perspective). A body without a `sexual` handler -> `rite_member_unavailable`.
5. Perspective `watch` and `option.watch_scene is None` -> `rite_no_watch_scene`.
6. `read_record(owner)`; `LandmarkRiteRecordError` -> `log_warn("landmark_rite_record_corrupt", exc=error, context={"char": owner.pk, "district": site.district_key})`, then `rite_record_corrupt`.
7. `party_in_combat(actor, body)`, or `live_dialogue_session(owner) is not None`, or `sleep_blocks_actions(actor)` -> `rite_unavailable`.
8. `entities = present_party_scope(actor)`; inside `advance_scope(entities)`, `planned_seconds(entities, option.seconds, tick=<current tick>) != option.seconds` -> `rite_interrupted`. The current tick is `read_world_clock()`'s, or `0` when no clock exists: preflight is a read and must never create the clock singleton (`get_world_clock` would).

**`perform_rite`**:

1. Replay: when `operation_id` is not `None` and the module-level receipt cache holds it, return the cached `RiteResult` and do nothing else. The cache is keyed by the acting body's pk together with the request identity, so a colliding identity from another character replays nothing that character never did; it is an insertion-ordered dict bounded to 256 entries (drop the oldest), written only from an `on_commit` callback.
2. `plan = preflight(...)`.
3. `admit_contact_before_action(actor)`, then `evaluate_skip_safety(actor) is not None` -> `rite_unsafe`. (Admission may start an encounter; that is the existing behaviour of every time-consuming action and is not a rite write.)
4. Build the rollback state before the transaction, exactly as the prayer rite does: `entities = present_party_scope(actor)`, `registry = build_advance_snapshot_registry(clock, option.seconds, AdvanceSource.SKIP, entities, mental_scope=entities)`, `tick_snapshot = _snapshot_clock_tick(clock)`, `record_snapshot = attribute_snapshot(owner, RECORD_ATTR)`. Read `climax_before = body.sexual.climax_today` and `first = site.district_key not in read_record(owner)["completed"]`.
5. Inside one `transaction.atomic()`:
   - `apply_pleasure_gain(body, 100)` then `apply_pleasure_gain(body, 0)`;
   - `body.sexual.shame.value += option.shame`; `body.sexual.exposure.value += option.exposure`;
   - `result = advance_wait(actor, option.seconds)` — never pass the caller's `operation_id`: `advance_wait` records its id in an in-memory ledger that no rollback clears (`world/rules/time_skip.py` `_record`), so a retried id after a rolled-back rite would return the old result without advancing time; `result.elapsed_seconds != option.seconds` -> raise `RiteRefused("rite_interrupted")`;
   - `write_record(owner, with_completion(read_record(owner), site.district_key, option.key, tick))`, `tick` being the world tick after the advance (`int(get_world_clock().tick)`: the enclosing snapshot's clock instance is pre-advance, because `advance_wait` resolves its own);
   - build the `RiteResult` (`climax = body.sexual.climax_today > climax_before`);
   - `transaction.on_commit(...)`: store the receipt and `log_info("landmark_rite_committed", context={"char": owner.pk, "district": ..., "archetype": ..., "option": ..., "body": body.pk, "seconds": option.seconds, "elapsed": result.elapsed_seconds, "climax": climax})`.
6. `except Exception:` restore with `_restore_clock_tick(clock, tick_snapshot)`, `_restore_advance_registry(registry, entities)`, `restore_attribute_best_effort(owner, RECORD_ATTR, record_snapshot)`, then re-raise.
7. Every `RiteRefused` leaving `perform_rite` is logged once before it propagates: `log_info("landmark_rite_refused", context={"char": <owner pk or actor pk>, "district": <district key or "">, "reason": code})`.

The advance is called with the actor, not the body: `present_party_scope` resolves the same present party from either, and the actor is the body whose travel observation and alignment checkpoint the wait owns.

### D4. Observability catalog

Add three rows to §4.2 of `docs/superpowers/specs/2026-09-02-observability-logging-design.md`, in the document's language and table format: `landmark_rite_committed` (`char`、`district`、`archetype`、`option`、`body`、`seconds`、`elapsed`、`climax`), `landmark_rite_refused` (`char`、`district`、`reason`), `landmark_rite_record_corrupt` (`char`、`district`; warn).

### D5. Tests

`world/rules/tests/test_landmark_rite_record.py` — plain `unittest.TestCase` with a stub owner whose `attributes` is a small in-memory object offering `get(key)` and `add(key, value)`:

- round trip of a valid record; a missing attribute reads as the empty record and adds no attribute;
- each envelope violation of D2 raises;
- `with_completion` on an empty record, on an existing district with a new option, and on an existing option: independently known counts and ticks (first at tick 100, repeat at tick 250 gives `count == 2`, `first_tick == 100`, `last_tick == 250`);
- an undeclared district key and option key already in the record survive `with_completion` unchanged; the input dict is not mutated;
- `write_record` refuses an invalid record and leaves the stored value unchanged.

`world/rules/tests/test_landmark_rites.py` — `EvenniaTest`. Fixture: the synthetic grid and the two patches of `typeclasses/tests/test_map_discovery.py` (`world.lore.map_districts.current` and `world.lore.map_districts.landmark_node_ids`, with the synthetic district also carrying `landmark_name_zh`), a synthetic `RiteSnapshot` built in the test and supplied with `world.lore.rites.installed(...)` (one archetype; option `solo` with `watch_scene=None`, option `shared` with a watch scene; durations 120 and 300; distinct shame and exposure steps), and a present companion created the way `world/rules/tests/test_party_time_settlement.py` creates one. Run commits with `self.captureOnCommitCallbacks(execute=True)`. Cover:

- one committed rite: the record gains the district with count 1, the world tick moved by exactly the option's duration, the body's `climax_today` rose by one and its climax phase is no longer 進行中, shame and exposure moved by the declared steps (start them below their maximum), `first_completion` is true, the returned scene is the `self` scene, and one `landmark_rite_committed` event carries the listed context;
- a repeat: counts 2, `first_tick` unchanged, `first_completion` false;
- a companion body on `shared`: the companion's sexual state changed, the player character's did not, the record is on the player character, the scene is the watch scene;
- each refusal code of D3 (one test or `subTest` each), asserting the tick, the record attribute and the body's pleasure, climax phase, shame and exposure are unchanged, and one `landmark_rite_refused` event;
- a corrupt record: `rite_record_corrupt`, the stored value byte-for-byte unchanged, one `landmark_rite_record_corrupt` warning;
- rollback: patch `world.rules.landmark_rites.write_record` to raise after the advance; the tick, the body's pleasure, climax phase, shame, exposure and `climax_today`, and the record are all as before;
- replay: the same `operation_id` twice returns the same result and settles once (tick moved once, count 1);
- retry after rollback: fail the record write once, then call again with the same `operation_id`: the second call commits and the tick moved by exactly one duration in total;
- a possessed companion as the actor with no member named: the delivered scene is the watch scene, and a solo-only option is refused as having no watch scene;
- `rite_site_for` in a plain interior room returns `None` without calling `landmark_node_ids` (patched to raise);
- `eligible_performers`: the actor first, a present companion included, a sleeping or absent companion excluded.

Register both modules in `.github/evennia-shards.json` in the shard that holds `world.rules.tests.test_party_time_settlement`.

## Risks / Trade-offs

- `advance_wait` opens its own nested `transaction.atomic()` and records its own skip receipt; the outer rollback state of D3 step 4 is what restores in-memory surfaces when the rite fails after the advance. The rollback test is the proof.
- Repeatable rites let a player raise sexual state at will. The only cost is time; no reward exists. This is the design's accepted bound.
