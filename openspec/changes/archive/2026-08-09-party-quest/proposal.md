# party-quest

## Why

Companions follow (`party-follow`) and fight (`party-combat`), but quests still treat them as
strangers: the DEFEAT planner explicitly grants "no ordinary kill credit" to companion actions,
and completing a quest rewards nothing to the people who fought beside the player. This change
makes companionship meaningful in the quest loop: companion kills and co-presence count toward the
player's objectives, and every then-in-party companion earns +2 affinity at turn-in — the
`quest_completion` source `affinity-system` already exempted from the daily cap.

## What Changes

- **Companion kills advance the player's DEFEAT objectives.** The DEFEAT event-effect planner
  gains a companion rule: when a bound companion — binding valid in both directions, not knocked
  out, on an active battlefield — defeats a matching monster, the quest owner's active DEFEAT
  stage advances through the same pre-commit planner (same aggregation, cap, and one-transition
  rules; decisions without a battlefield or a valid binding fail closed). Unbound or mismatched
  entities still grant no credit.
- **Companion co-presence counts for location and escort arrival.** REACH and ESCORT arrival
  advances when the player arrives and at least one bound companion is present in the destination
  room; the follow flow re-runs the arrival observation after companions complete their moves so
  first-arrival co-presence is visible (the one-transition rule keeps it idempotent). ESCORT
  keeps its protected-entity alive-and-present requirement; no companion-alone arrival entry point
  is added.
- **Turn-in rewards the party.** Reward settlement (`world/rules/guild.py::turn_in_quest`) commits,
  in the same atomic transaction as wallet/inventory/merit/acquire/claim, +2 affinity
  (`quest_completion`) for every companion in the player's party at turn-in, through the
  sole-writer affinity API; a failed write restores the per-NPC affinity surfaces and their
  in-process caches alongside the reward surfaces. Companions have no quest log of their own —
  "共同任務" means assisting the player's quests.
- **No new commands, menus, or command-docs changes.**

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `party-system`: The membership capability gains the quest-assistance requirement — companion
  contributions to the player's objectives and the +2 turn-in affinity per then-in-party
  companion.
- `quest-progress-tracking`: The DEFEAT planner requirement changes (bound-companion kills count
  for the quest owner, replacing the blanket "no companion credit" rule) and the room-arrival
  requirement changes (companion co-presence satisfies REACH/ESCORT arrival).
- `quest-reward-settlement`: The atomic payout requirement changes — the turn-in transaction gains
  the per-companion affinity surface.

## Impact

- **New code**: `world/rules/tests/` quest-party integration tests; party-side helper reads in
  `world/rules/party.py` (then-in-party companions at turn-in, bound-companion-of check).
- **Modified**: the quest event-effect planner and room-arrival observation in `world/quests/`,
  the reward settlement in `world/rules/guild.py::turn_in_quest()`, the affinity writer
  call sites, and the three delta specs.
- **Dependencies**: `party-core` (binding), `party-follow` (co-location), `party-combat`
  (knockout state — a knocked-out companion's kill credit is excluded by the same alive rules),
  `quest-progress-tracking`, `quest-reward-settlement`, `affinity-system` (the
  `quest_completion` source).
- **Out of scope**: per-companion quest logs, companion-side rewards (XP/items/merit),
  quest-delegation or auto-accept for companions, decrease events, cap breaks.
