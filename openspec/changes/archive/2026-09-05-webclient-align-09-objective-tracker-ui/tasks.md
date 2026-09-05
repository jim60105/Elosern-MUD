# Tasks: webclient-align-09-objective-tracker-ui

## 1. Store read model & layout shell

- [x] 1.1 `stores/elosern.js`: expose `objectivesAvailable` and `objectivesRows` derived from
  `rs.panels.objectives` in the reducer and store view.
- [x] 1.2 `HudFrame.vue` & `AppShell.vue`: add `#objectives` slot so the tracker mounts as a direct
  child of `.elosern-stage`.

## 2. Tracker island & QuestBoard toggle

- [x] 2.1 `ObjectiveTracker.vue` matching draft `.obj` markup and styling: header `目標` with
  `<span class="n">N 追蹤</span>`; rows with stage checkbox `.bx` (SVG checkmark when
  `stage_progress >= objective_quantity`), `objective_line`, right-aligned `.pr` (`n/m` when
  `objective_quantity > 1`, else `+reward_copper` when non-null, else empty), and muted deadline
  line `.dl` when present; zero controls or dispatch; wire in `AppClient.vue`.
- [x] 2.2 `QuestBoard.vue`: on quest log rows, add 追蹤 / 取消追蹤 button:
  - `in_progress` + `!tracked`: enabled "追蹤", dispatches `guild.quest_track {quest_id, tracked: true}`.
  - `in_progress` + `tracked`: enabled "取消追蹤", dispatches `guild.quest_track {quest_id, tracked: false}`.
  - Non-`in_progress`: disabled "追蹤" button with reason `（非進行中任務無法追蹤）`.
  Wire `@quest_track="onQuestAction"` in `AppClient.vue`.

## 3. Showcase lockstep

- [x] 3.1 `component-manifest.json`: add `Overlays/ObjectiveTracker` to `required` (bump count 43 → 44).
- [x] 3.2 `stories/Overlays/ObjectiveTracker.stories.js`: add deterministic offline stories
  (active objectives, done check, multiple counts, reward tag, deadline line).
- [x] 3.3 `tests/overlays/deferred_surfaces_absent.test.js`: remove `persistent objective tracker`
  from `DEFERRED_SURFACES`, drop `/\bObjectives?\b/i` from `DEFERRED_TITLE_PATTERNS`, drop `objective-`
  prefix, and update required manifest length to 44.

## 4. Tests & verification

- [x] 4.1 Vitest `tests/overlays/objective_tracker.test.js`: test header count, payload order,
  done checkbox boundary, `.pr` slot matrix, deadline line, empty/unavailable hiding, zero dispatch.
- [x] 4.2 Vitest `tests/world/quest_board.test.js`: test tracking toggle rendering, click dispatch,
  and disabled state on completed quests.
- [x] 4.3 Run `npm test`, `npm run showcase-coverage`, and `tools.spec_traceability check`.
- [x] 4.4 Live container check: track from the guild board → tracker appears; walk out of the hall →
  tracker persists; progress advances `n/m`; untrack removes the row.
