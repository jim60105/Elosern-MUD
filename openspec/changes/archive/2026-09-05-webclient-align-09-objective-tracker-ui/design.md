# Design: webclient-align-09-objective-tracker-ui

## Context

Change 06 committed the server-side quest tracking contract:
- The persistent `tracked: bool` field on `QuestRecord` and `world.quests.runtime.set_quest_tracked`.
- The `guild.quest_track` WS service action (payload `{quest_id, tracked: bool}`, cap 3, reject on non-`in_progress` or cap exceeded).
- The `services` presentation panel v4 with `tracked: bool` on guild quest rows.
- The host-independent `objectives` presentation panel (schema v1), disclosing up to 3 `tracked && in_progress` rows with describe-seam prose, stage progress, objective quantity, reward copper, and deadline line.

The client now needs to render this read model per the redesign draft (`docs/design/elosern-redesign/index.html` lines 272–285, 828–833):
1. The bottom-right `.obj` objective tracker island on the cinematic stage.
2. Tracking toggle controls in the guild quest browser (`QuestBoard.vue`).
3. Showcase story and manifest registration, retiring the deferred surface test assertion.

## Goals / Non-Goals

**Goals:**
- Render the `.obj` tracker island from the committed `objectives` panel rows only — no client-mined narrative, no local state invention.
- Match draft markup and CSS: header `目標` with mono-gold count `N 追蹤`; each row with stage checkbox `.bx` (checkmark when `stage_progress >= objective_quantity`), objective line `.txt`, right-aligned mono-gold slot `.pr` (`n/m` when `objective_quantity > 1`, else `+reward_copper` when non-null, else empty), and muted deadline line `.dl` when present.
- Contextual hiding: hidden when `rows` is empty, when the `objectives` panel is unavailable, or in `creation` mode.
- Display-only: the tracker island has zero interaction controls and dispatches nothing.
- Quest log tracking toggle: each quest row in `QuestBoard.vue` renders an action button:
  - `in_progress` + `!tracked`: enabled "追蹤", dispatches `guild.quest_track {quest_id, tracked: true}`.
  - `in_progress` + `tracked`: enabled "取消追蹤", dispatches `guild.quest_track {quest_id, tracked: false}`.
  - Completed or failed: disabled "追蹤" button with stable reason `（非進行中任務無法追蹤）`.
- Lockstep showcase registration: `ObjectiveTracker` component added to `component-manifest.json` (freezing at 44 required components), Storybook story with deterministic offline fixtures, and removal of the tracker from `tests/overlays/deferred_surfaces_absent.test.js`.

**Non-Goals:**
- No server-side changes (completed in change 06).
- No client-side optimistic tracking state: the toggle flips only upon receiving the committed server snapshot.
- No combat-specific hiding of optional rows: the draft's `選修` tag has no backing field on the wire, so the draft's `.mode-combat .obj .opt` rule has nothing to hide (documented deviation).

## Decisions

- **Stage slot for `.obj`:** `ObjectiveTracker` is mounted via an `#objectives` slot in `AppShell.vue` / `HudFrame.vue` as a direct child of `.elosern-stage`. This allows it to use the draft's exact CSS `position: absolute; bottom: calc(var(--dock-h) + 60px); right: 16px; width: 238px; z-index: 4;` without being affected by the top-anchored `[data-anchor="hud-right"]` container's vertical flex layout and `overflow-y: auto`.
- **Store read model:** `stores/elosern.js` exposes `objectivesAvailable` and `objectivesRows`, derived from `rs.panels.objectives`. `AppClient.vue` mounts `ObjectiveTracker` when `store.objectivesAvailable && store.objectivesRows.length > 0 && store.view.mode !== 'creation'`.
- **Done check icon:** Inlines the exact 10×10 SVG checkmark from draft `index.html:830`.
- **QuestBoard tracking toggle:** Added to the quest row actions block beside abandon and turn-in. Emits `quest_track` with `{ action_id: 'guild.quest_track', payload: { quest_id, tracked } }`, wired in `AppClient.vue` to `onQuestAction`.
- **Deferred surface test trim:** `persistent objective tracker` removed from `DEFERRED_SURFACES`, `/\bObjectives?\b/i` removed from `DEFERRED_TITLE_PATTERNS`, `objective-` removed from deferred testid prefixes, and required manifest length bumped from 43 to 44.

## Risks / Trade-offs

- **Draft deviation (選修 tag):** The draft shows `.row.opt` with `<span class="rw">選修</span>` hidden in combat mode. The server quest model does not carry an optional/elective tag, so all committed tracked rows are rendered identically in exploration and combat.
- **Stage slot extension:** Adding `#objectives` to `HudFrame` and `AppShell` touches layout shell components, but keeps the existing 5 named stage anchors (`hud-left`, `hud-right`, `feed`, `dock`, `command-line`) strictly intact and preserves empty-anchor assertions in `app.test.js`.
