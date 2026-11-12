# Design: the met-person record

## Context

- Single-writer rule (root `AGENTS.md`): persistent state is written by the
  deterministic core (`world/rules/` and named packages); presentation is
  read-only.
- Named NPC identity: `world/art/subjects.character_subject_for(entity)`
  returns `ArtSubject(CHARACTER, <stable key>)` only for an explicit named
  `portrait_policy`; `None` for generic/no policy.
- Possession: `actor.db.possessed_by` holds the owner's pk;
  `world/rules/party.bound_owner_of(npc)` resolves the live owner
  (`account_roster.build_account_roster` uses the same pair).
- Places: `typeclasses/rooms.GridRoom.xyz` → `(x, y, z)` where `z` is the map
  key; `world/maps/map_data.SETTLEMENT_GRAPHS` is keyed by settlement map id;
  `TerrainRoom.coordinates` → `(x, y)`;
  `wilderness_provider.region_for_coordinates(x, y)`;
  `InstanceRoom.origin_room` (AttributeProperty, may be `None`).
  `web/webclient/presentation/area_map._settlement_title` finds a settlement's
  anchor display name through `WILDERNESS_ENTRY_REGISTRY` gates whose
  `z_map_key` equals the map key.
- Time: `world/rules/clock.read_world_clock()` → clock with `.tick`, or None.
- Existing record precedent: `world/rules/map_knowledge.record_arrival`
  validates the stored envelope, logs and refuses to overwrite a corrupt one.

## Goals / Non-Goals

**Goals:** writer, reader, place derivation, possession owner.

**Non-Goals:** call sites (`met-person-write-points`); gallery listing
(`gallery-people-category`); any cap on entries (the design accepts growth and
pages by place).

## Decisions

### D1. Storage (verbatim)

Attribute `met_people` on the character (`character.attributes`, category
none), value:

```python
{"schema_version": 1, "seq": <int >= 0>,
 "entries": {<stable_key>: {"npc": <int dbid>, "place": <str | None>,
                            "tick": <int >= 0>, "seq": <int >= 1>}}}
```

`seq` is a per-record counter incremented on every write; an entry's `seq`
is the counter value of its last interaction, so recency ordering is total
and deterministic even when ticks are equal.

### D2. API (verbatim)

```python
PLACE_SETTLEMENT = "settlement"
PLACE_REGION = "region"

@dataclass(frozen=True)
class MetPerson:
    stable_key: str
    npc: Any            # live NPC object
    place: str | None   # "settlement:<map key>" | "region:<region key>" | None
    tick: int
    seq: int

def interaction_place(location) -> str | None
def place_label(place: str) -> str
def record_person_interaction(actor, npc) -> None     # never raises
def met_people(character) -> tuple[MetPerson, ...]    # newest seq first; never raises
```

- `interaction_place`: GridRoom with `z in SETTLEMENT_GRAPHS` →
  `f"settlement:{z}"`; TerrainRoom → `f"region:{region_for_coordinates(x, y)}"`;
  InstanceRoom with a non-None `origin_room` → `interaction_place(origin_room)`
  (one level only, no loop); else `None`.
- `place_label`: settlement → anchor `display_name_zh` found as in
  `_settlement_title` (without the 街道圖 suffix), else the map key; region →
  `regions()[key].display_name_zh`, else the key; unknown prefix → the string.
- `record_person_interaction`:
  1. owner = `bound_owner_of(actor)` when `actor.db.possessed_by` is set
     (skip on mismatch, as the roster does), else `actor`; only a
     `typeclasses.characters.PlayerCharacter` owner is recorded.
  2. subject = `character_subject_for(npc)`; `None` or `ArtSubjectError` →
     return.
  3. Read and validate the envelope; a corrupt value logs
     `met_people_record_corrupt` and returns without writing.
  4. Drop entries whose NPC is gone (D3); increment `seq`; tick =
     `clock.tick` or 0; place = `interaction_place(actor.location)`.
  5. Existing entry: set `npc`, `tick`, `seq`; set `place` only when the new
     place is not None and differs. New entry: create only when place is not
     None (an entry without a place could not be grouped).
  6. Save; emit `met_person_recorded` info with `char`, `npc`, `place`.
  Any exception → `log_warn("met_person_record_failed", exc=...)`.
- `met_people`: tolerant read; resolve all `npc` ids with one
  `ObjectDB.objects.filter(id__in=...)`; keep an entry only when the object
  exists and `character_subject_for(obj).key == stable_key`; sort by `seq`
  descending.

### D3. Vanished entries

"Gone" = the dbid does not resolve or no longer yields the same stable key.
The writer removes them in step 4; reads skip them. No scheduled cleanup.

## Risks / Trade-offs

- [The record grows with every named NPC met] → bounded by named NPCs in the
  world; listing pages by place (`gallery-people-category`).
- [Instance rooms without an origin produce no place] → an NPC first met there
  is not recorded until met somewhere placeable; flagged as a planner
  decision.
