# Proposal: webclient-align-09-objective-tracker-ui

## Why

The client-side quest-tracker UI was originally scoped inside
`webclient-align-06-quest-tracking-contract`. A rubber-duck critique flagged that
change as mixing two independently shippable contracts: the server tracking
contract (persistent `tracked` flag, `guild.quest_track` action, `objectives`
panel read model) and the bottom-right `.obj` tracker island plus its showcase
registration. This change owns only the client UI so 06 can land as a pure
server-contract change.

## What Changes

- Add the bottom-right `.obj` objective tracker island to the contextual HUD:
  derived client-side from the `objectives` panel rows where
  `tracked && status == in_progress` (first 3), with stage-done checkbox,
  `objective_summary`, `stage_progress` numerals, optional `deadline_line`, head
  `目標 … N 追蹤`, and combat-mode hiding of optional rows. The island renders
  nothing when no tracked quests exist.
- Add 追蹤 / 取消追蹤 toggle buttons to the quest board and quest log rows,
  dispatching `guild.quest_track {quest_id, tracked}`.
- Register the tracker in the component showcase manifest/story and remove the
  `objective-*` deferred-surface entry from
  `tests/overlays/deferred_surfaces_absent.test.js` in the same change.

## Capabilities

- `webclient-contextual-hud` — MODIFIED: the objective-tracker island requirement
  (moved verbatim from 06's delta).
- `webclient-component-showcase` — MODIFIED: manifest/story gains the tracker
  (moved verbatim from 06's delta; applies after 05's showcase chain).

## Impact

- Depends on `webclient-align-06-quest-tracking-contract` landing first
  (committed `objectives` panel + `tracked` rows + `guild.quest_track` action).
- New client files: `ObjectiveTracker.vue` (+ QuestBoard toggle wiring, vitest).
- The `webclient-service-menus` delta that exposes the tracking toggle in the
  quest browser stays with 06 until rebased here.
