## Why

Combat identity uses the mutable display key: `reconstruct_battlefield` keys the roster by `str(entity.key)` and rejects duplicates, `Battlefield.__post_init__` enforces the same, and the skip-safety registry maps `str(entity.key)`. A player legally named `guild-examiner-E` collides with the deterministically spawned E examiner, blocking that exam forever; same-named monsters block engagement; a same-key object settling elsewhere evicts another combatant's skip-safety registration (audit finding F08).

## What Changes

- Exam opponents receive unique display keys per spawn (e.g. `guild-examiner-<rank>-<pk>`), eliminating the reachable collision with same-named players.
- The skip-safety registry is keyed by immutable dbref instead of display key, so same-name entities can never cross-evict each other's registrations.
- Battlefield roster identity itself stays display-keyed (its consumers depend on it); no display-identity migration is performed in this change.

## Capabilities

### Modified Capabilities

- `guild-rank-exams`: exam opponents use per-spawn unique keys.
- `skip-safety-gate`: battlefield registration is indexed by participant dbref.

## Impact

- `world/rules/guild_exams.py::_spawn_opponent`, `world/rules/skip_safety.py` (`_BATTLEFIELDS`), tests for exam spawn and skip-safety lookup.
