# affinity-cap-break

## Why

The natural affinity cap of 99 makes the topmost ladder stage (絕對羈絆, floor 100) unreachable:
A3 of the affinity-party design reserves cap breaks for special events, and the ladder spec
already renders values above 99 correctly. The friendly-fire capbreak design
(`docs/superpowers/specs/2026-08-09-affinity-friendfire-capbreak-design.md`, F3) supplies the first
cap-break trigger: a dedicated milestone quest.

## What Changes

- Adds a `cap_breaks` table to `rulebook/affinity.yaml`: `{npc_key | role, quest_key, new_cap}`,
  validated at load (resolvable quest key, exactly one selector, `new_cap` above 99, no duplicate
  quest+selector pairs; a companion matching several entries resolves to the highest `new_cap`).
- Adds `world/rules/affinity.py::raise_affinity_cap(npc, player, new_cap)` as the sole cap writer:
  monotonic (only grows), idempotent, and record-creating (a recordless companion still receives
  the milestone instead of silently losing it).
- Extends the guild-quest turn-in transaction: when the completed `quest_key` matches a
  `cap_breaks` entry, every then-in-party companion matching `npc_key`/role gets its cap raised in
  the same atomic transaction as the reward and the +2 `quest_completion` gain, and the raise is
  applied **before** the +2 gains so a record at the old cap cannot clamp them.
- After a break, values above 99 are reachable and map to the topmost stage exactly as the ladder
  already defines; no player-facing cap display is added.

## Capabilities

### New Capabilities
- `affinity-cap-break`: The milestone cap-break contract — the `cap_breaks` table, the sole cap
  writer, and the turn-in matching rule.

### Modified Capabilities
- `affinity-system`: The record model and sole-writer requirements name `raise_affinity_cap` as
  the sole cap writer alongside `apply_affinity_change` as the sole value writer.
- `quest-reward-settlement`: The atomic turn-in transaction includes the cap-break step for
  matching in-party companions.

## Impact

- `world/rules/affinity.py`: `raise_affinity_cap()`; record model unchanged in shape.
- `world/rules/affinity_config.py`: `cap_breaks` YAML validation (fail closed).
- Quest turn-in path (`world/quests/` / guild reward settlement): calls the rules API, never
  writes affinity itself.
- No command, WebClient, or data-migration surface changes.
