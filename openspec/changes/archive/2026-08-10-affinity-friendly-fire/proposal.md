# affinity-friendly-fire

## Why

The affinity writer accepts negative deltas and the party auto-leave recheck hook is built and
tested, but no real decrease event calls it — the hook has no live caller. `engage()` rejects
non-hostile targets, so the only real player-to-NPC damage path is friendly fire on companion NPCs
during the player's combat session; the friendly-fire capbreak design
(`docs/superpowers/specs/2026-08-09-affinity-friendfire-capbreak-design.md`, F1/F2) supplies that
first caller now.

## What Changes

- Adds a deterministic friendly-fire penalty: a player combat action (skill, AREA, or all-target
  shorthand) that damages an ally-side companion NPC reduces that NPC's affinity toward the player
  by 1 per hit (`friendly_fire` source).
- Adds a damage scan after each resolved player action round in the combat session; only damage
  caused by the player's own action counts — companion-vs-companion, enemy behavior, and buff-tick
  damage never penalize. The scan, all penalty writes, and any resulting auto-leave run inside the
  round's transaction boundary (a failure rolls the whole round's affinity effects back), and
  companion membership is snapshotted per round so a mid-round leave never changes that round's
  penalty count.
- Adds `friendly_fire_penalty_per_hit: 1` to `rulebook/affinity.yaml`.
- Negative deltas keep their existing semantics: never reset the daily cap, never restore budget,
  and the auto-leave recheck runs — dropping below 70 ends the companion party with
  `reason="affinity_below_threshold"` and notifies the player.
- A friendly-fire hit on an entity that is not a companion NPC writes nothing and creates no
  negative record.

## Capabilities

### New Capabilities
- `affinity-friendly-fire`: The friendly-fire damage scan and per-hit penalty contract — what
  counts as friendly fire, the per-hit penalty through the sole writer, non-companion no-op, and
  auto-leave integration.

### Modified Capabilities
- `affinity-system`: The sole-writer requirement's closed source set gains `friendly_fire`.

## Impact

- `world/rules/affinity.py`: source set membership; no writer-API shape change.
- `world/rules/combat_session.py`: player-action damage scan against ally-side companion NPCs.
- `world/rules/rulebook/affinity.yaml`: `friendly_fire_penalty_per_hit` (validated by
  `affinity_config.py`).
- `world/rules/party.py`: auto-leave hook unchanged, gains its first real decrease caller.
- No command, WebClient, or data-migration surface changes.
