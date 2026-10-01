## Why

Service hosts and guild exam opponents are created with no persona at all (`world/rules/guild_economy.py::_sync_service_host`, `world/rules/guild_exams.py::_spawn_opponent`). The approved design (`docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` §5.1, §6.1) requires every production creation path to complete a valid card before the NPC is usable, resolving the complete authored profile at creation and rejecting authored data that lacks one instead of falling back to a generic personality. Once every content slice has filled its rows and the guild slice has named every examiner profile, these two registry-backed producers can be switched over and the reference made mandatory.

## What Changes

- **BREAKING (pre-release):** a place that authors a host must name `host_profile_key`; the key joins the all-or-nothing host group, so a hosted place without it, or a hostless place with it, fails load naming the place.
- The derived service-host roster row carries the profile key, and `_sync_service_host` initializes a newly created host's card from that profile (provenance `profile`) inside the same startup transaction as its creation. A reused host is never re-initialized or overwritten by sync, restart, or registry edits; an existing host that predates cards is left for the cutover.
- `_spawn_opponent` initializes the exam opponent's card from `GuildRank.examiner_profile_key` inside its existing delete-compensation, so a persona failure leaves no opponent and the exam start rolls back.
- The `guild_service_host_created` and `guild_exam_opponent_created` events gain the `profile` key in context (identifier only).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `settlement-place-registry`: ADDED requirement that every host-authoring place names its host profile.
- `place-driven-service-sync`: ADDED requirement that a newly created service host receives its profile card and a reused host is never overwritten.
- `guild-rank-exams`: ADDED requirement that an exam opponent receives its rank examiner's card at spawn, all-or-nothing.

## Impact

- Code: `world/lore/settlements/places.py` (host group), `world/rules/guild_config/_hosts.py` (roster row), `world/rules/guild_economy.py`, `world/rules/guild_exams.py`.
- Tests: `world/lore/tests/test_settlements.py`, `world/rules/tests/test_guild_economy_sync/` (existing package, registered), `world/rules/tests/test_guild_exams.py`, `world/rules/tests/test_guild_config/test_service_host_roster.py`; synthetic place fixtures that author hosts must name a synthetic profile.
- Observability catalog rows for the two extended events.
- No schema, prompt, UI, or migration change; existing instances are the cutover's job.

## Batch:

depends-on: npc-persona-card-foundation
depends-on: npc-persona-profile-registry
depends-on: npc-persona-content-altoria-lower
depends-on: npc-persona-content-altoria-trade
depends-on: npc-persona-content-altoria-guild
depends-on: npc-persona-content-altoria-upper
depends-on: npc-persona-content-ciaran-homes-a
depends-on: npc-persona-content-ciaran-homes-b

Code-conflict notes: second and last editor of `world/lore/settlements/places.py` (after `npc-persona-profile-registry`). Sole editor in this batch of `world/rules/guild_economy.py`, `world/rules/guild_exams.py`, and `world/rules/guild_config/_hosts.py`. Requirements become satisfiable only after all six content slices: making the reference mandatory earlier would fail load on unfilled rows, and no placeholder profile may be added to bridge the gap. Shared append-only files: `.github/evennia-shards.json` (only if a new rules test module is created), the observability catalog. Prerequisite of `npc-persona-roster-cutover`.
