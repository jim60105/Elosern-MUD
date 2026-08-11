## Context

`_spawn_opponent` (`world/rules/guild_exams.py:189-219`) always spawns `key=f"guild-examiner-{target_rank}"`. `reconstruct_battlefield` (`world/rules/combat_session.py:347-374`) keys the roster by `str(entity.key)` and raises `DUPLICATE_PARTICIPANT` on a clash; `Battlefield.__post_init__` (`world/rules/combat.py:60-64`) hard-requires `key == str(entity.key)`. `_BATTLEFIELDS` (`world/rules/skip_safety.py:16-26`) registers and pops by `str(entity.key)`. Phase-6 verification showed a full dbref-keyed roster migration would require touching every roster-key consumer plus the `__post_init__` assertion; this change therefore removes the *reachable* collisions without migrating battlefield identity.

## Goals / Non-Goals

**Goals:**
- A legal `guild-examiner-<rank>` player name can never block their own exam.
- Same-key entities can never cross-evict skip-safety registrations.

**Non-Goals:**
- Migrating `Battlefield` roster keys to dbrefs (deferred; display-key identity stays).
- Guaranteeing unique player display names.

## Decisions

**D1 — Unique spawn key with a stable, deterministic suffix.** `guild-examiner-{rank}-{pk}` (the opponent's own dbref) is unique per spawn, deterministic for tests that create objects in order, and keeps the human-readable prefix.

**D2 — Skip-safety keyed by dbref only.** `register_active_battlefield` builds `{str(entity.pk): battlefield for entity in roster.values()}`; `unregister_active_battlefield(entity)` pops `str(entity.pk)`. Lookup in `evaluate_skip_safety` uses the actor's dbref. Display names are no longer read in this module.

**D3 — Roster identity untouched.** `reconstruct_battlefield`, `team_of`, targeting, `nonlethal_keys`, and `roll_initiative` keep operating on display keys, exactly as today.

## Risks / Trade-offs

- **Opponent key changes player-facing output**: the opponent's displayed name gains a numeric suffix; acceptable and only affects the temporary exam opponent.
- **Battlefield collision remains possible** for two same-named *players* in one session — unreachable in single-player (one player per session); documented as out of scope.
