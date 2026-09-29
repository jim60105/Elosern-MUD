## 1. Implement the bounded surface

- [x] 1.1 Replace the tab renderer and update root, category and group frame geometry to one column in both live resolver and remaining consumers; test vertical wrapping and horizontal no-op including recovery root.
- [x] 1.2 Derive detail by current frame and row; test category/group/skill/back transitions and disabled explanations.
- [x] 1.3 Bound the full list ancestry and neutralize count styling; inspect the longest category list above the hint strip.
- [x] 1.4 Set basic-attack initial focus from eligible server candidates only; cover no foe, disabled foe, ally selection, and no automatic dispatch.
- [x] 1.5 Add playback wait/skip presentation without changing locks; exercise beat completion and skip.
- [x] 1.6 Delete obsolete tab component/story/manifest references, update approved AVG design component table and the affected main specs (combat-menu, contextual-hud, pointer-activation, desktop-shell) during application; run focused keyboard/browser paths.

## 2. Verify and document the completed behavior

- [x] 2.1 Run the smallest relevant existing component/logic regression files once after implementation, adding only tests for uncertain boundary behavior; record the actual commands and results.
- [x] 2.2 Launch the actual changed client surface or its isolated story with deterministic data and exercise the design scenarios; record observations, viewports and motion/input states rather than claiming tests alone prove the appearance.
- [x] 2.3 Update affected main specifications and existing design/showcase documentation for the implemented contract, remove obsolete callers/tests rather than adding compatibility aliases, obtain canonical requirement IDs with the traceability tool and annotate only substantive behavior tests.
- [x] 2.4 Run `openspec validate webclient-combat-command-window --strict` and the scoped traceability check after main-spec sync; keep archive/merge work outside this change.

## Verification record

- Node gate: every `web/static/webclient/js/tests/*.test.js` passes under `node --test` (new: one-column root/category/group/single-target geometry, `initialTargetKey` foe-behind-ally, fallback, disabled and non-basic cases).
- Vitest: `pnpm test` — 125 files, 1382 tests pass (new: `tests/store/combat_command_window.test.js`, the `commands` pane kind and detail in `dock_menu_panes.test.js`, the classifier rule in `dock_panes.test.js`, the playback cue in `action_dock.test.js`); `pnpm run showcase-coverage` — 57/57.
- Focused browser methods (each batch one command under ten minutes, after `pnpm run build`): `contextual_hud_combat` (new command-window test, master-detail, forfeit), `contextual_hud_dock` (vertical root list, band region, digits, pane kinds), `combat_menu` (8 methods including the pointer root-row click), `combat_panels` (4), `combat_scales` (3), `combat_skills` (6), `combat_beats` (off and reduced, with the cue), `art` combat journeys (2), `shell_dock` (2), `exploration_dialogue` (1), `input_narrative` motion tokens (2) — all OK.
- Two failures that already existed on master were fixed because they sit on this change's surface: the dock's A7 focus-frame pseudo-element overflowed `#action-dock` by 6px at 1280x720 (its right inset is now 0), and the band-region test still read a CSS top border that A7 replaced with the seam's `::after` edge line (the test and the scenario now name that edge).
- Visual smoke (Storybook, throwaway Chromium): `Core/AppShell/CombatHud` at 1920x1080 and 1280x720 (root, categories, groups, skill, disabled skill, basic-attack target with the ally listed first), `Core/AppShell/CombatParticipantPolish` with a playing round (veil, skip clears it), `Action/ActionDock` `CombatDock` / `CombatDisabledCommand` / `CombatCategories` / `CombatPlayback`.
- Python showcase gates: `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.tests.test_vue_showcase_{action,data,overlays,world}_evidence` — 15 OK once their frozen manifest sets dropped `Action/DockTabBar`.
- Post-implementation review dispositions: the four stale manifest sets fixed (blocking); the playback cue's live region narrowed to its words so the skip button is outside it; basic-attack initial focus is annotated on the art combat journey that opens Attack with the actor listed first; scenario titles that still say "tab" are kept because the strict validator refuses dropping a MODIFIED requirement's scenarios by rename, and their bodies carry the vertical contract; the frame-derived `focusedSkill` fallback keeps reading any skill-list row (category and group keys are `skill-cat-*` / `skill-group-*`, never skill keys); DockMenu's `depth` prop stays as an accepted input its hosts still pass.
