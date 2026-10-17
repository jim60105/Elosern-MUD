# Design: Main navigation and window hotkeys

## Context

See proposal.md. `DesktopNavigation.vue` maps server-provided items (`character`, `quests`, `inventory`, `bag`) to labelled controls with glyph-count widths and packs them against a fixed-width region; `nav-tools.js` is the single tool model; the prototype `MainNavPrototype.vue` shows the approved bar with and without possession.

## Goals / Non-Goals

**Goals:** the approved bar and hotkeys with unchanged placement stability and tooltip behaviour.

**Non-Goals:** exploration protocol changes, restyling other windows.

## Decisions

- **隊伍 entry** is client-mapped from the committed `party` panel availability (available in exploration and combat); 任務/地圖 keep their existing sources and mode gating.
- **Region width** recomputed for three labelled entries (`GLYPHS` table) so 工具 and 設定 positions stay within 1px across modes.
- **Hotkeys** registered once on `document` keydown (non-capturing), ignoring events with modifiers, from `input`/`textarea`/`select`/contenteditable targets, while a `QuestionCard` or confirmation is open, or during IME composition; each key calls the same opener path as its control so focus restoration works.
- **Possession** changes nothing in the bar (no "you" marker).

## Risks / Trade-offs

- [Conflicts with dock digit/arrow keys] → Letters only; the dock uses digits, arrows, Enter, Space, Escape.

## Migration Plan

Pre-release clean cutover; revert the implementation commit.

## Verification and documentation ownership

Vitest: bar order per mode, absent entries without placeholders, tool order, 隊伍 last-tab opening, hotkeys open the right tab, guards for inputs/IME/modifiers/modals, M inert in combat, possession-identical bar. Node geometry test for 1px stability at the three viewports; stories with and without possession; one browser method for P/B hotkeys; `docs/game/commands.md` web-client paragraph and AGENTS.md. `tools.contract_gate`.
