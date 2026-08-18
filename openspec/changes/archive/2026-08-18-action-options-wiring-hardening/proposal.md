## Why

The completed AI action-options feature is safe at dispatch time, but its presentation state can
outlive the situation that produced it. The wiring audit identified five residual seams: stale
ready cards after combat or direct relocation, a duplicated destination node encoder, a
multi-window dismiss race that can replay dismissed cards, an unused choice-point facade method,
and retired pending generations retained until their transport completes.

This change closes those seams without changing canonical game state, the OOB protocol version,
or the deterministic offline fallback.

## What Changes

- Derive the current exploration situation fingerprint through one shared read-only helper and
  make the `context_actions` presenter suppress a session snapshot whose fingerprint is no longer
  current.
- Replace the exit-only action-options room-entry trigger with one post-commit player-location
  observer so ordinary traversal and direct `move_to()` relocations both invalidate and schedule
  options. Add a terminal-combat completion trigger after the action result is published.
- Make a dismiss establish a bounded session-local minimum generation sequence. A chain-owned
  detached predecessor can hand off to one successor after another window's in-flight generation
  settles, so the dismissing session never replays that pre-dismiss generation.
- Remove an emptied retired generation from the pending registry immediately while preserving its
  identity guard, so a completed old Deferred cannot remove a newer generation for the same
  fingerprint.
- Route every destination node calculation through `node_id_for_location()` and remove the
  duplicate encoder in the affordance vocabulary.
- Remove the unused `moveChoicePointToEnd` facade operation. Narrative appends remain the sole
  stream-end relocation owner through `StreamEndBlock.appendNode()`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `action-options-trigger-service`: Add freshness derivation, universal relocation and terminal
  combat triggers, dismiss generation barriers, and immediate retired-pending removal.
- `webclient-context-actions-suggestions`: Hide stale session-backed suggestion states before
  they reach the v5 exploration form.
- `exploration-affordances`: Require the shared node-ID encoder for move destinations as well as
  current locations.
- `webclient-action-choicepoints`: Remove the unused facade move operation while retaining the
  append-owned stream-end ordering contract.

## Impact

Affected areas include `server/option_proposal_service.py`, presentation fingerprint/context and
options modules, player relocation hooks, the dispatcher combat-completion path, exploration
affordances, and the narrative choice-point JavaScript facade. Terminal combat updates every live
watcher of the actor after its action result is sent. The existing `ui_snapshot` and `ui_update`
envelope schema remains version 5; no migration, persistence change, dependency, or new player
command is introduced.
