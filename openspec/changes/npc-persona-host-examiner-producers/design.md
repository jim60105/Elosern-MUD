## Context

See proposal.md for motivation. `validate_place_registry` enforces an all-or-nothing host group (`HOST_IDENTITY_FIELDS`); the foundation added an optional, validated-when-set `host_profile_key`. `world/rules/guild_config/_hosts.py` derives the service-host roster from places; `sync_service_content` creates or reuses hosts by component `service_id` inside the startup transaction and never renames or retitles a reused host. `_spawn_opponent` builds a plain `NPC` inside `start_guild_exam`'s atomic block with a delete-compensation `except`. The guild content slice added a required `GuildRank.examiner_profile_key`.

## Goals / Non-Goals

**Goals:** every new service host and exam opponent carries a valid card from its authored profile at creation; missing references fail at load; no instance is ever overwritten by routine sync.

**Non-Goals:** existing instances without a card (cutover), voice routing, editor, imports, companions, scene occupants.

## Decisions

### D1. The profile key joins the host group

`host_profile_key` is appended to `HOST_IDENTITY_FIELDS`. The partial-host error lists it like any other missing field, so a hosted place without a profile fails load naming the place, and the foundation's hostless-with-key rejection still applies. Alternative rejected: a separate "hosted places must have a profile" pass — duplicating the group logic is exactly what the single group predicate exists to prevent.

### D2. Initialize on creation only

`_sync_service_host` calls `initialize_npc_persona(host, profile.card, {"kind": "profile", "profile": key})` only in the `host is None` creation branch, after race/sex/title are set and before the commit-bound creation event. A reused host is never passed to the initializer: sync is not a repair path, and an existing host without a card belongs to the cutover's exclusive replacement. The roster row (`ServiceHostRow`) gains `profile_key`, resolved from the place once at roster derivation; `sync_service_content` fails closed (before any write) if a roster row's profile does not resolve, naming the service. Alternative rejected: calling the initializer on every sync (it would no-op for marked hosts but would silently initialize unmarked pre-cutover hosts outside the cutover's single transaction).

### D3. Exam opponents initialize inside the compensation

`_spawn_opponent` resolves `NPC_PROFILE_REGISTRY[rank.examiner_profile_key]` and initializes after `npc_title` is set and before the occupancy suffix check, inside the existing `try`; any failure deletes the opponent and re-raises, and `start_guild_exam`'s transaction rolls back the record and session. Each spawn is a fresh instance with its own version 1 (an edit to one opponent never affects later spawns).

### D4. Events

`guild_service_host_created` and `guild_exam_opponent_created` gain `profile` (the key); the initializer's own `npc_persona_initialized` event follows the foundation contract. Catalog rows are updated in §4.2.

## Risks / Trade-offs

- [Synthetic test places across the suite author hosts without a profile] → add a shared synthetic profile fixture in the test-data kit or file-local fixtures and update those places; `rg "PlaceDefinition\(" --glob "*/tests/*"` enumerates them.
- [A retained developer database has hosts without cards until the cutover lands] → expected and harmless: dialogue still uses the authored tables; the editor reports such hosts as unavailable.
