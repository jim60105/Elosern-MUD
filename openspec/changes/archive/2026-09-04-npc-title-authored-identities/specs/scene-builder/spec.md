# scene-builder delta

## REMOVED Requirements

### Requirement: The occupant spawn path backfills a missing display name deterministically through the namegen rule layer
**Reason**: `display_name` and `title` become required authored identity fields enforced by the
shared characterization validator at the guardrail and compile boundaries, and the spawn-path
revalidation now fails closed (rollback, zero residue) on any occupant reaching it without a valid
authored identity. A production path can no longer reach the backfill seam with a nameless
occupant, so the deterministic namegen backfill contradicts the invariant that every NPC carries
an author-supplied name (design 2026-09-03-npc-identity-titles §3.2). Rolled names survive only as
pre-authoring inspiration (the scenario-director name-inspiration bank), never as a final name the
system writes to an entity.
**Migration**: No replacement behavior is needed — validated blueprints always carry the authored
name, forged ones fail closed. The crc32 slot-seeded spawn-time roll is deleted together with its
call site, imports, and tests; `world.rules.namegen` itself is unchanged and remains the
prompt-time inspiration source. The project has no released users and all existing generated
game data will be regenerated, so no stored blueprint or entity migration is needed.

### Requirement: Every display-name backfill emits an observability info event
**Reason**: The event exists only to trace the spawn-time backfill writes removed by this change;
with the backfill seam deleted there is no write left to trace. Persistent-state boundary tracing
for the authored-identity creation paths is carried by this change's own
`npc-identity-titles` requirements (`guild_service_host_created`, `guild_exam_opponent_created`)
and the scene-builder spawn path's existing commit boundary.
**Migration**: Consumers must not expect `npc_name_fallback` events after this change. The event
id is retired; no replacement event id is introduced.
