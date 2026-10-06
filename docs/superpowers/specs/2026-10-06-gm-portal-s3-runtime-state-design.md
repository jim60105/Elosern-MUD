# GM Portal S3 Design: Runtime State Inspection

- Date: 2026-10-06
- Status: Approved design
- Parent: `docs/superpowers/specs/2026-10-06-gm-portal-design.md` (sub-project S3)
- Depends on: S1 (portal skeleton), S2 (transcript and `call_id` links)

S3 adds read-only inspection of the game's persistent runtime state to the
`/gm/` portal: accounts, characters, NPCs, monsters, rooms, quest records,
narrative records, and art assets. Nothing in S3 writes state.

## 1. Approach

Each entity gets a curated summary view plus a generic raw-data tab.

- Curated views reuse the existing read models so the numbers match what the
  game shows: `world/rules/status_query/` (traits, breakdowns, gauges,
  conditions, sexual state), `world/rules/displayed_stats.py`,
  `world/rules/title_view.py`, `world/rules/lineage_query.py`, and the
  narrative query helpers. `web/gm/` never re-implements rule calculations.
- The raw-data tab lists every Attribute, tag, and component on any Evennia
  object, so fields without a curated view are still visible.

## 2. Read layer: `web/gm/readers/`

- One module per entity kind: `accounts.py`, `characters.py`, `npcs.py`,
  `monsters.py`, `rooms.py`, `quests.py`, `narrative.py`, `art.py`, plus
  `raw.py` for the generic object dump and `search.py`.
- Each reader returns JSON-serialisable dicts. Readers never write.
- Attribute access must not autocreate. Readers read `AttributeProperty`
  values whose descriptor autocreates on access through
  `attributes.get(..., default=...)` (or an equivalent non-creating path)
  rather than the descriptor. The implementation plan enumerates every
  autocreating property the readers touch.

### Raw-data tab (all Evennia objects)

- `attributes.all()` (key, category, JSON-converted value), tags with
  categories, components, typeclass path, location, `db_date_created`.
- Object references render as `{"$ref": "#123", "typeclass": "…", "key": "…"}`.
- Unconvertible values render as
  `{"$unserializable": "<type name>", "repr": "<repr truncated to 200 chars>"}`.

## 3. Navigation

```
執行期狀態
├ 搜尋 (name / #dbref / source_id / quest id / call_id)
├ 帳號        ├ 房間
├ 玩家角色    ├ 任務 (runtime records, generated quests)
├ NPC         ├ 敘事 (events, threads, letters, dreams, director decisions,
├ 魔物        │        scheduled beats, authoring drafts and requests)
              └ 美術資產
```

- Every list uses the S1 `cursor`/`limit` envelope with filters (for example
  NPCs by location, monsters by species and region, memories by category,
  tier, and availability).
- Every identifier renders as a link: a character page links to its quests,
  memories, letters, room, party members, and possession partner; a memory's
  `source_id` links to its source event; any `call_id` opens the S2 payload
  drawer.
- Global search: `#123` jumps to that object; other text matches object key,
  quest id, then `source_id`, in that order.

## 4. Entity views

Every entity page has a 概要 (curated) tab and a 原始資料 (raw) tab. The
curated content:

| Entity | Summary content | Sources |
| --- | --- | --- |
| Account | name, permissions, created, last login, live sessions, owned characters | Evennia `Account`, `world/rules/account_roster.py` |
| Player character | identity (race, subrace, sex, age, apparent age); true traits and `disguised_stats` side by side, the latter labelled 僅顯示用; per-trait breakdown (base → skills → equipment → conditions); gauges; conditions and buffs; skills and lineage; equipment and inventory; wallet as integer copper with a derived gold/silver/copper display; guild rank and merit; titles; affinity; party and possession; sexual state; current room | `status_query`, `displayed_stats`, `title_view`, `lineage_query`, `affinity`, `party`, `possession` |
| NPC | everything a player character shows, plus title, profession, service components (shop, guild counter), persona card (seven sections and version), schedule (today's plan and current slot), dialogue key; 記憶 tab and 對話 tab (§5) | `npc_persona`, `npc_schedules`, `dialogue`, narrative models |
| Monster | species, variant, threat tier, numeric source (approved profile or interim), owning site or ambient placement, loot table, behaviour profile | `monster_individual`, `monster_behaviour`, `world/maps/monster_sites.py` |
| Room | coordinates and map, place kind, exits, occupants grouped by kind, instance ownership and lifetime | `world/maps/` |
| Quest record | definition key, issuer, status and stage, progress counters, bound targets, deadline, rewards, failure reason, owning character; generated quests also show the stored payload | `quest_log`, `world/quests/runtime.py`, `GeneratedQuestStore` |
| Narrative | events (content, participants, location, visibility); story threads (status, links, revisions); letters (exchanges, state, reply work); dreams (sessions and exchanges); director decisions and scheduled beats; authoring drafts and creative requests | `world/narrative/models.py` |
| Art asset | subject key, status, prompt summary, `source_hash`, generated time, failure reason; thumbnail through the existing `/art/` route when a file exists | `ArtAssetRecord`, gallery |

`disguised_stats` never replaces true traits in any view; both are always
shown and labelled.

## 5. NPC narrative tabs

### 記憶

- `MemoryRecord` list filtered by tier, availability, category, and knowledge
  scope, showing content, salience, confidence, subjects, `source_id` (linked),
  and effective tier/availability.
- Expanding a record shows its full `MemoryRevision` history (availability,
  tier, decay metadata, supersedes).
- **Recall preview.** Input: query text (≤ 2000 characters), optional thread,
  include-superseded and include-inactive toggles. The server calls
  `world/narrative/recall.py` `fast_recall(owner_id=<npc>,
  requester_id=<npc>, ...)`, which is read-only, and returns the core,
  working, and lexical selections with BM25 scores, plus the owner's current
  memory generation.
- **Recent context snapshots.** The newest 10 `NarrativeContextSnapshot` rows
  with sections, token accounting, and truncated or rejected sources, linked
  to the S2 transcript when a `trace_id` or `call_id` is present.

### Out of scope: full dialogue prompt preview

`world/narrative/dialogue.py` `build_dialogue_context()` has side effects: it
settles pending correspondence projections, may create a dialogue epoch,
persists a context snapshot, and appends a frame. A full prompt preview would
require splitting it into a pure assembly phase and a commit phase on the live
dialogue path. S3 does not do this. The actual prompt sent for any past turn is
already visible through the snapshot list and the S2 transcript. A later
change may extract the pure phase if a preview is needed.

### 對話

Dialogue epochs and frames grouped by player.

## 6. API

| Route | Purpose |
| --- | --- |
| `GET /gm/api/state/<kind>?cursor=&limit=&<filters>` | List |
| `GET /gm/api/state/<kind>/<id>` | Curated summary |
| `GET /gm/api/state/object/<dbref>/raw` | Raw data for any Evennia object |
| `GET /gm/api/state/search?q=` | Global search |
| `POST /gm/api/state/npc/<dbref>/recall` | Recall preview; POST for long query bodies, writes nothing |

- `limit` defaults to 50, maximum 200. Lists return summary fields only.
- Sorting and filtering use indexed fields (narrative `tick`, `owner_id`,
  `category`, ...) and, for Evennia objects, `db_typeclass_path` and tags.

## 7. Error handling

- Each summary section is computed independently. A section that fails (for
  example a `StatusQueryError` on corrupt data) returns its error code and
  message in its slot; the rest of the page renders. Such failures are
  evidence the operator wants to see.
- Unknown object: `404` `object_not_found`. Wrong kind for the route: `404`
  `kind_mismatch`. Recall query too long: `400` `query_too_long`.

## 8. Frontend

- New shared components: `GmEntityLink` (renders any identifier as a route
  link), `GmJsonTree` (collapsible; shared by the raw tab and the S2 payload
  drawer; renders `$ref` as links and `$unserializable` distinctly),
  `GmFilterBar`, `GmPager`.
- Entity page layout: name and identifiers on top, `.ui-tabs` below
  (概要, 原始資料, plus entity-specific tabs).
- Runtime state pages do not auto-poll; a manual refresh control is shown.

## 9. Tests

- One `EvenniaTest` module per reader with fixed fixtures (character, NPC,
  monster, quest, narrative records) asserting output shape.
- Read-only contract, two layers:
  - AST scan of `web/gm/readers/`: no `.save()`, `.create()`, `.delete()`,
    `.update()`, no assignment to `.db.*` or Attribute properties, no import
    of known writer functions.
  - Runtime check: reading every entity kind leaves Attribute counts and the
    row counts of every narrative table unchanged.
- `disguised_stats`: true and displayed traits are emitted separately and
  never merged.
- Recall preview: results equal a direct `fast_recall` call and no rows are
  written.
- Vitest: `GmEntityLink` routing, `GmJsonTree` rendering of `$ref` and
  `$unserializable`. Storybook stories for new components.
- New Python test modules registered in `.github/evennia-shards.json`.
