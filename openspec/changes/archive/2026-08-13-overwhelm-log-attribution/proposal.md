## Why

In a player-overwhelming (壓制) battle, the session folds the player's single chosen action into a
bounded compressed resolution and then `compress_event_logs()` deletes every successful `"roll"`
entry from the record. The resulting log can make the player's commanded action appear to hit the
wrong target: casting `基本攻擊` at one's own character renders as
`瑟芮雅 對 瑟芮雅 的攻擊擲出了 44。` immediately followed by
`瑟芮雅 對 哥布林 造成了 120 點傷害。` — the auto basic attack's successful roll line is missing, so
the damage seems to belong to the commanded self-attack. The compressed log also gives the player no
way to tell their commanded action apart from the compression's deterministic auto basic attacks.
Self-targeting damage skills are legal by design (faction constraint `ANY`); the failure is purely in
the log's readability, not in target resolution.

## What Changes

- `compress_event_logs()` stops dropping successful `"roll"` entries. Every attack's roll line is
  preserved in original order, so each damage entry stays visually anchored to its own attack line —
  the same presentation the game already uses for ordinary (uncompressed) rounds.
- The player's commanded action is identified in the compressed record: one `commanded_action`-kind
  entry is prepended to that action's `EventLog`, rendered as `你施展了「基本攻擊」。`, so the reader
  can distinguish the commanded action from the compression's auto basic attacks. The match is
  restricted to the encounter's first-round logs, so a round-1-invalidated command simply yields no
  marker and an auto basic attack can never be mislabeled as the player's choice.
- The session facade passes the selected action's actor key and skill key into the resolver.
  `resolve_overwhelm()` gains two optional keyword arguments whose defaults leave every existing
  direct caller (quest-planning integration, rule tests) byte-identical.
- The aggregate summary entry (`rounds` / `hits` / `total_damage`) is unchanged. Combat math,
  initiative, the auto-attack policy, and the single-writer boundary are untouched. Self-targeting
  damage stays legal — **no validation change**.
- **BREAKING** (internal contract only; the project has no released users, so no migration):
  consumers of compressed logs must no longer rely on successful hit rolls being absent, and the
  output grows by the restored roll lines plus the marker. `test_overwhelm_compression.py` and the
  `event-log-compression` spec update accordingly.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `event-log-compression`: replaces the drop-redundant-hit-rolls rule with full per-attack
  preservation and adds the commanded-action marker requirement.
- `player-combat-session`: the overwhelm branch of the facade forwards the commanded action identity
  (actor key and skill key) to the resolver for log marking.
- `single-shot-resolution`: `resolve_overwhelm()`'s signature is amended with optional log-shaping
  keyword arguments that never affect combat math.

## Impact

- `world/rules/overwhelm.py`: `compress_event_logs()` (no kind-based filtering, commanded-action
  marker, new `commanded_action` entry template) and `resolve_overwhelm()` (optional kwargs
  forwarded to compression).
- `world/rules/combat_session.py`: `submit_player_action()` passes `str(actor.key)` and `skill_key`
  on the player-overwhelming branch.
- `world/skills/registry.py`: read-only `SKILL_REGISTRY` lookup for the skill display label (an
  established import direction — `world/rules/combat.py` already imports it).
- `world/rules/tests/test_overwhelm_compression.py`: rewritten for the new preservation contract;
  new tests for the marker. Other overwhelm, party, friendly-fire, and disengage tests assert on
  damage entries and state, which are unchanged.
- No edits to `event_log.py` dataclasses, combat/targeting validation, the narrator prompt schema
  (entry kinds are opaque strings to it), or the webclient OOB channel (prose never crosses OOB).
