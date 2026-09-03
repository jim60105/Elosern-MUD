# scene-builder — delta

## ADDED Requirements

### Requirement: The occupant spawn path backfills a missing display name deterministically through the namegen rule layer
`world/quests/scene_builder.py` SHALL guarantee every spawned scene NPC carries a display name:
after the characterization seam has applied any authored `display_name`, the NPC spawn path SHALL
check `npc.db.display_name` and, only when it is `None` (an LLM blueprint that left the field empty,
a generic role-based occupant with no characterization, or a position past the carried
characterization list), roll a name through the read-only
`world.rules.namegen.roll_name_for_race(race_key, sex, Random(zlib.crc32(f"{definition.key}:{stage_index}:{role}".encode())))`
and write it to `npc.db.display_name`. `race_key` and `sex` SHALL be read from the spawned prototype
(the `npc.race` / `npc.sex` attribute values, `None` when absent or empty so the rule layer falls
back to its race-bound random pack and random pool). The seed coordinates `definition_key` and
`stage_index` SHALL be threaded explicitly from the materialization entry point through the occupant
spawn path. An authored display name — from the LLM or from the hand-written template pool (for
example 黑鬍) — SHALL NEVER be overwritten, and the template pool SHALL require no change. Spawning
the same definition's same stage and role SHALL always produce the same backfilled name. Monster
occupants SHALL NOT receive namegen names.

#### Scenario: A nameless occupant is backfilled and replays identically
- **WHEN** an instance stage materializes an NPC whose characterization carries no `display_name`
  and the same definition is later materialized again for the same stage index and role
- **THEN** both spawned NPCs carry the identical rolled display name equal to what
  `roll_name_for_race` produces for the crc32 seed `f"{definition.key}:{stage_index}:{role}"`

#### Scenario: An authored display name is never overwritten
- **WHEN** a characterization carries `display_name` (an LLM-filled name or the template pool's
  黑鬍) and the occupant materializes
- **THEN** `npc.db.display_name` equals the authored text exactly, no roll is performed for that
  occupant, and no backfill event is emitted

#### Scenario: A generic role-based occupant still gets a name
- **WHEN** an occupant with no characterization entry materializes
- **THEN** its `npc.db.display_name` is a composed name from the namegen rule layer, resolved from
  the prototype's race (its tier's `race_key` mapping) or the race-bound random pack when the race
  is unavailable, and from the prototype's `sex` value

#### Scenario: Backfill reaches every instance NPC through one seam
- **WHEN** the repository-wide deterministic-path scans run and the spawn code is inspected
- **THEN** the backfill calls only the pure `world.rules.namegen` functions with a call-site-built
  `Random`, imports no `world.ai` module, and the existing atomic rollback behavior is unchanged —
  a rolled-back materialization leaves no named occupant behind

### Requirement: Every display-name backfill emits an observability info event
The scene-builder backfill seam SHALL emit one `world.observability` `log_info` event with the
event id `npc_name_fallback` (snake_case, named-import facade) each time it writes a rolled name,
through `transaction.on_commit` scheduling, with a context dict carrying the quest identity, the
slot coordinates, and the result (`quest`, `definition_key`, `stage`, `role`, `name`). The event
SHALL be a plain logger write — never a state write — and SHALL NOT be emitted for an occupant
whose authored display name was applied, nor for a materialization whose transaction rolls back.

#### Scenario: A backfilled NPC logs exactly one named event
- **WHEN** an NPC is backfilled during materialization
- **THEN** exactly one `npc_name_fallback` info event is logged whose context names the quest,
  definition key, stage index, role, and the rolled `name` of the backfilled slot

#### Scenario: An authored-name occupant logs no backfill event
- **WHEN** an occupant keeps its authored `display_name`
- **THEN** no `npc_name_fallback` event is emitted for it

#### Scenario: A rolled-back materialization logs no backfill event
- **WHEN** a materialization that backfilled a name fails and rolls its transaction back
- **THEN** the scheduled `npc_name_fallback` callback never runs and the log holds no event for
  that slot
