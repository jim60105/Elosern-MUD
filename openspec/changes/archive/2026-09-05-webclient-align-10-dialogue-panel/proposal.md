# Proposal: webclient-align-10-dialogue-panel

## Why

The rubber-duck critique split `webclient-align-07-dialogue-session` in two: the
session-state contract (helpers, deterministic writer, clear seams — invisible on its
own) and the protocol-visible dialogue panel + mode + client mirror. This change owns
the second half: the `dialogue` panel schema, `MODES` extension, coordinator
mode-resolution, oob-protocol mirror, and the wire that makes change 07's session
state observable.

## What Changes

- `MODES` gains `"dialogue"`; registry gains the `dialogue` panel (schema v1,
  unavailable form `("dialogue_unavailable", "對話目前無法顯示")`) with host triple,
  `bond_stage | null`, `line`, `choices[{keyword_id,label}]`; exact-key validator.
- Coordinator mode resolution: creation > combat > dialogue-session-live > exploration;
  the exploration panel keeps flowing while dialogue is live.
- The change-07 adapter hook's result reaches the wire: the session records the NPC
  and settled line before the existing snapshot publish.
- oob-protocol snapshot shape mirror updated for the new mode and panel.
- exploration-menu delta scenario: the next committed presentation carries mode
  dialogue with the available dialogue panel.

## Capabilities

### New Capabilities

- `webclient-dialogue-session`: panel shape, validator, availability forms, mode
  resolution, clear-to-unavailable (panel/mode requirements; the session-state
  requirement is ADDED by change 07 and chained-MODIFIED here).

### Modified Capabilities

- `webclient-oob-protocol`: snapshot mode list + panel allowlist mirror.
- `webclient-exploration-menu`: the scripted-reply scenario gains the
  mode-carrying presentation consequence (chained on 07's hook requirement).

## Impact

- Depends on `webclient-align-07-dialogue-session-state` (session helpers/writer).
- `world/webclient` protocol `MODES`, registry, new `web/webclient/presentation/dialogue.py`,
  coordinator, oob mirror tests, Node-gate mirror fixtures.
- Change 08 (`webclient-align-08-dialogue-surface`) depends on THIS change, not 07.
