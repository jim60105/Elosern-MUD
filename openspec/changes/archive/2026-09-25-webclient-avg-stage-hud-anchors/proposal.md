## Why

The AVG stage design (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §4, §5.1, §5.2) names the stage's top islands by what they hold:
- `vitals` under the place card
- `map` at the top-right, carrying the minimap with the objective tracker as one line beneath it

After C4a (`webclient-avg-stage-shell`) and C4b (`webclient-avg-place-card-top-bar`) the islands still use the generic `hud-left` / `hud-right` anchors. The objective tracker is still a separate bottom-right card that lists up to three rows with deadlines, shows in every mode, and shares the right column's lower half with the island stack. The party strip still draws full cells (name, numerals, bond) beneath the vitals. The design shows the objective in exploration only, as one line, and the party as compact avatars. This change finishes the stage-shell slice. The project is unreleased, so the old anchor names and the multi-row tracker layout are deleted, not aliased.

## What Changes

- **BREAKING (internal)**: `components/HudFrame.vue`:
  - renames `hud-left` to `vitals` (`data-anchor="vitals"`, testid `anchor-vitals`, slot `vitals`) and `hud-right` to `map` (`data-anchor="map"`, testid `anchor-map`, slot `map`), keeping the C4a / C4b geometry
  - hides the whole `map` anchor in creation mode
  - hides the objective line outside exploration with `display:none` on `data-elosern-mode`
  - deletes the `objectives` slot
- `components/AppShell.vue`:
  - forwards `vitals` / `map` instead of `panel-left` / `panel-right`
  - drops the `objectives` pass-through
  - `HIDDEN_BY_MODE.creation` names `[data-anchor='vitals']` and `[data-anchor='map']`
  - `HIDDEN_BY_MODE` for `combat` and `dialogue` adds nothing, because the objective line has no tab stop
- `AppClient.vue` fills `#vitals` with `StatusPanel` and `PartyStrip`. It fills `#map` with `LocalMap`, `ObjectiveTracker` (moved out of the deleted `#objectives` slot), `ParticipantFrame` (combat), and `TitleBallotMenu`, in that order.
- **BREAKING (internal)**: `components/ObjectiveTracker.vue` becomes one fixed-height line and is no longer absolutely positioned. It renders:
  - the `目標` label
  - the first row's stage box, `objective_line` (ellipsis, full text as accessible text and `title`), and progress or reward slot
  - a `+N` count of further rows

  The multi-row list, the `N 追蹤` count, and the deadline line leave the stage. The quest drawer already shows every row and `deadline_line` (`QuestLog.vue` `quest-log__quest-deadline`).
- **BREAKING (internal)**: `components/PartyStrip.vue` renders compact cells:
  - kept: avatar, HP hairline, and the combat token as an avatar badge
  - removed from visible text: the name, the HP numerals, and the bond; they stay in the existing `aria-label`, which is also used as `title`
  - deleted: the `+ 邀請` padding cells (`party-strip__empty-slot`) and `emptyCount`

  The header `同伴 N / 4` stays. Invites live in the party drawer.
- `ParticipantFrame` stays an island in the `map` anchor (the minimap is hidden in combat). `actor-right` stays empty for C10 / C13. `TitleBallotMenu` stays in the `map` anchor, below the objective line.
- Short viewports (`max-height: 820px`) compact the `vitals` stack so it fits its anchor at 1280x720 (design D6): a 56px place card, a new `--stage-inset-y` gutter token, one-row gauges, and smaller condition chips.
- `styles/app-shell.css` renames every `hud-left` / `hud-right` selector to `vitals` / `map`, and drops `.obj` from the menu-open filter (the tracker is now inside an anchor, which the filter already covers). `HudFrame.vue` drops `.obj` from its own menu-open rule.
- Spec deltas: the stage, visibility, island-stack, minimap-convention, party, objective, participant-frame, and reference-surface requirements move to the new anchors. The `webclient-local-map` minimap requirement stops naming `hud-right`.
- No OOB schema, presenter, server, store, or persistence change. No component is added or deleted, so the manifest is unchanged.

Out of scope:
- The vitals fade is owned by `webclient-motion-layer` (C11).
- The dialogue host's portrait in `actor-right` is owned by `webclient-dialogue-stage` (C10). The foe standing portraits and their beat animation are owned by `webclient-combat-beat-playback` (C13).
- Collapsing the command line is owned by C5.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-contextual-hud`:
  - MODIFIED "The WebClient renders a full-bleed cinematic stage with anchored HUD surfaces", on C4b: `place` / `vitals` / `map`.
  - MODIFIED "Surface visibility is gated by the committed game mode", on C4b: the objective line is exploration-only, and the island anchors are hidden in creation.
  - MODIFIED "The HUD island stack renders as bounded floating islands, not column cards", on C3: the `vitals` and `map` anchors and their island order.
  - MODIFIED "The minimap island states only its own drawing convention", on C1: the `map` anchor above the objective line; the place card owns the place name.
  - MODIFIED "The party quickbar island presents the committed party only", on C3: compact cells, no invite padding.
  - MODIFIED "The objective tracker island presents the committed objectives only": one line under the minimap, exploration only.
  - MODIFIED "The combat participant frame presents the session's participants and their portraits": in the `map` anchor, never a portrait anchor.
  - MODIFIED "The reference surfaces have no permanently visible home and are reached from the top navigation or the dock", on C4a: its right-anchor scenario names `map`.
- `webclient-local-map`: MODIFIED "The browser minimap renders states without relying on color alone", on C2: two scenario bodies name the `map` anchor instead of `hud-right`; no rule changes.

## Impact

- Edited components:
  - `web/webclient-app/components/HudFrame.vue`, `AppShell.vue`, `ObjectiveTracker.vue`, `PartyStrip.vue`
  - short-viewport compaction (design D6): `VitalsTrack.vue`, `ConditionChips.vue`, `styles/tokens.css` (`--stage-inset-y`)
  - comments only: `ParticipantFrame.vue`, `StatusPanel.vue`
  - `web/webclient-app/AppClient.vue`, `styles/app-shell.css`
- Edited stories: `stories/Overlays/ObjectiveTracker.stories.js`, `stories/Overlays/PartyStrip.stories.js`, `stories/Core/HudFrame.stories.js`, `stories/Core/AppShell.stories.js` (the new `PopulatedHud` and `CombatHud` player stories), `stories/World/MapLattice.stories.js` (comment).
- Vitest:
  - `tests/overlays/objective_tracker.test.js`, `tests/overlays/objective_tracker_integration.test.js`, `tests/data/party_strip.test.js`
  - `tests/hud_frame.test.js`, `tests/app.test.js`, `tests/data/status_panel.test.js`
  - `tests/world/local_map.test.js`, anchor attributes only, if any survive C1
- Browser tests:
  - `web/tests/browser/test_browser_contextual_hud_anchors.py`, `test_browser_layout.py`, `test_browser_contextual_hud_drawers.py`, `test_browser_shell_surfaces.py`, `test_browser_contextual_hud_stage.py`, `test_browser_combat_menu.py`, `test_browser_local_map_lattice.py`, `test_browser_local_map_geometry.py`
  - `.github/browser-shards.json`
- Spec traceability: no requirement is renamed, removed, or added, so every existing annotation stays valid. The new behaviours are covered by the existing objective-tracker and party-strip node-suite evidence tests and by browser cases added under the existing IDs.
- Dependencies:
  - Archive order C1 → C2 → C3 → C4a → C4b → C4c (this change).
  - This change's blocks are written on C4b (stage, visibility), C4a (reference surfaces), C3 (island stack, party), C1 (minimap convention), and C2 (`webclient-local-map` minimap), plus the main spec for the objective and participant requirements. It must be archived after all five.
  - C5, C8, and C10 build on these anchor names.
