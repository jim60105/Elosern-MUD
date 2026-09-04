# Tasks: webclient-align-09-objective-tracker-ui

## 1. Tracker island

- [ ] 1.1 `ObjectiveTracker.vue` per the draft `.obj` island: `目標 / N 追蹤` header; stage box
  with done check at `stage_progress >= objective_quantity`; `objective_line`; `.pr` slot rule
  (`n/m` when `objective_quantity > 1`, else `+reward_copper` when non-null, else nothing);
  muted deadline line when set; visibility exploration+combat with non-empty rows, hidden when
  empty/unavailable/creation; zero controls/dispatch. Wire in `AppClient.vue`.

## 2. Showcase lockstep

- [ ] 2.1 `component-manifest.json`: `ObjectiveTracker` entry +
  `stories/Overlays/ObjectiveTracker.stories.js` (deterministic offline rows, derived-shape
  binding); `tests/overlays/deferred_surfaces_absent.test.js`: drop the tracker entry,
  `objective-` prefix, `/\bObjectives?\b/` pattern, `DEFERRED_SURFACES` row;
  `npm run showcase-coverage` green.

## 3. Tests + traceability

- [ ] 3.1 Vitest: tracker header/order/done-box boundary/`.pr` slot matrix/deadline
  line/hide-on-empty/no-dispatch. Land `covers_requirement` literal IDs for the tracker-island
  IDs at the archive/sync commit (IDs unknown to the checker before sync; magic-xp P1 precedent).

## 4. Verification

- [ ] 4.1 Focused Vitest labels + `tools.spec_traceability check`.
- [ ] 4.2 Live container check: track from the guild board (change 06) → tracker appears; walk
  out of the hall → tracker persists; progress advances `n/m`; untrack removes the row.

## 5. Chain note

- [ ] 5.1 Apply AFTER webclient-align-06-quest-tracking-contract lands (needs the committed
  `objectives` panel, `tracked` rows, `guild.quest_track`); the showcase delta applies after
  webclient-align-05-party-hud (same deferred-surface requirement chain).
