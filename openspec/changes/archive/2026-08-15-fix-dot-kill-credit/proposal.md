## Why

`fire_scorch`, `dark_corrosion`, and `poisoned` rate ticks mutate HP directly
during combat upkeep (`_apply_rate_modifier` in `world/rules/buffs.py:81-96`,
driven by `tick_buffs` from `_end_of_round_upkeep` at
`world/rules/combat.py:546-552`). A lethal tick leaves the foe team non-living,
so `_terminal_outcome` (`world/rules/combat_session.py:990-1018`) returns
victory, but the tick carries no source identity and emits no `target_defeated`
event. The action-local kill-XP staging (`_step6_combat_kill_xp`,
`world/rules/action.py:612-642`) and the quest event-effect planner
(`world/quests/planner.py:26-43`) therefore never credit the kill: the player
permanently loses kill XP, and a quest-bound target can die without completing
its DEFEAT objective (audit finding 2, severity medium).

## What Changes

- Damaging rate buffs (`rate.target == "hp"` with a negative delta: `poisoned`,
  `fire_scorch`, `dark_corrosion`) persist the authoritative caster dbref as
  `source_pk` in the buff cache when applied through the `buff_apply` effect
  handler. The identity is derived from the resolving actor inside the handler,
  never from caller-supplied `buff_kwargs`, so attribution cannot be spoofed.
- `tick_buffs` still applies rate damage (the spec'd plain callable) but also
  returns an ordered tuple of `TickRecord` values (definition key, resolved
  `source_pk` or None, delta, HP before the tick) for every damaging tick that
  actually fires. Callers that ignore the return value (the world-clock
  settlement path) get exactly today's behavior: no events, no credit.
- Combat upkeep becomes an event-producing deterministic boundary: the round's
  upkeep settlement consumes the tick records inside `run_round` and stages —
  in the same combat-round transaction — HP damage (already applied by the
  tick), one `target_defeated` crossing entry per target, EventLog `damage`
  entries, monster kill XP for the attributed lethal source, and quest
  DEFEAT/protected-failure effects through the existing event-effect planners.
- Policy parity with direct damage: simulated (guild-exam) rounds tag upkeep
  defeat entries `simulated` and stage no kill credit; companion
  `nonlethal_keys` floor upkeep damage at 1 HP and mark `knocked_out` instead
  of defeating; unattributed ticks (absent/deleted source) cross HP silently
  with no entries, XP, or quest effects.
- No double counting: a target the applying action already killed never ticks
  (upkeep skips non-living roster members), and the settlement emits exactly
  one defeat entry per target even when several DoTs fire in one tick.

## Capabilities

### New Capabilities

- `combat-upkeep-settlement`: the deterministic boundary that turns damaging
  rate ticks into attributed defeat events, kill XP, and quest effects inside
  the combat-round transaction.

### Modified Capabilities

- `buff-handler-integration`: damaging rate buffs carry validated `source_pk`
  identity; `tick_buffs` returns damaging tick records while keeping its
  apply-on-tick contract.
- `combat-resolution`: per-round upkeep collects damaging tick records and the
  round settles them through the event-producing boundary; `run_round` accepts
  the session's simulated/nonlethal policy flags.
- `magic-level-progression`: combat kill XP is staged for attributed lethal
  upkeep ticks on tiered monsters, once, in the same round commit; unattributed
  and simulated ticks grant nothing.
- `quest-progress-tracking`: DEFEAT progress and protected-entity failure
  consume attributed, non-simulated upkeep-settled defeats with the same
  aggregation, cap, and one-transition rules as action defeats.
- `player-combat-session`: the round-and-settlement atomic unit now includes
  upkeep-settled kill credit; the session threads its simulated/nonlethal
  policy into `run_round` and overwhelm compression.

## Impact

- `world/rules/buffs.py`: `TickRecord`, `tick_buffs` return value, damaging
  buff source caching via `_add_buff`.
- `world/rules/action.py`: `_handle_buff_apply` persists `source_pk` for
  damaging buffs.
- `world/rules/upkeep.py` (new): upkeep tick settlement (entries, kill-XP and
  quest staging, nonlethal floor, simulated tagging) reusing `PendingEffect`,
  `_commit`, the event-effect planners, and `grant_combat_kill_xp`.
- `world/rules/combat.py`: `_end_of_round_upkeep` returns per-entity tick
  records; `run_round` gains `simulated`/`nonlethal_keys` and settles upkeep.
- `world/rules/overwhelm.py`: `resolve_overwhelm` threads the policy flags to
  `run_round`.
- `world/rules/combat_session.py`: `submit_player_action` passes the session
  policy into `run_round`/overwhelm; no change to the outer transaction seam.
- No player commands, command docs, or import schemas change.
