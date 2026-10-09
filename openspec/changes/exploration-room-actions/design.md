# Design

## Context

Source of truth: `docs/superpowers/specs/2026-10-10-scene-overview-redesign-design.md` §5, §6, §7, §8. The prototype `ScenePrototype.vue` is the visual reference; the spec wins on behavior. `web/webclient-app/AGENTS.md` governs.

Observed today (after the first two changes):
- The command panel holds the compass, the readout, and `SceneOverview` reduced to the footer chips; the router root is the footer-only overview with `geometry: "sections"`.
- `exploration.wait` and `exploration.suggestions` are pushed router frames; `AppClient.vue` renders the wait frame as the `waiting-screen` block (three `waiting-card` articles, an extra `睡眠並進入夢境協作` button inside the sleep card, which this change replaces with the dream question (D5), `RestForm`), and the suggestions frame as the `cards` dock pane (`OptionCard` rows plus `✕ 清除建議`).
- `onDockActivate` special-cases `explore.wait` to open `RestForm`.
- `PlaceCard.vue` is display-first with no control.

## Goals / Non-Goals

**Goals:**
- Room actions sit on the place card; wait and suggestions are local centred cards; the readout is the single explanation line; the old overview and its router geometry are gone.

**Non-Goals:**
- Any payload, vocabulary, or server change; any change to dialogue, combat, skill dock, or the top navigation bar.

## Decisions

### D1. Local card state, no router frames

A small composable holds `openCard` (`null | "wait" | "suggestions"`) and the opener element. Rows come from `ExplorationMenu.waitItems()` and `suggestionsMenu(suggestions)` (item and payload builders stay), fed through the generalized store submission gate from the previous change. `exploration.wait` and `exploration.suggestions` resolvers, the pushed-frame back-row logic, `waitOpen` / `restFormOpen` coupling to router depth, and the focus-restoration code for them are deleted; the cards close on a committed location change and on any mode change, matching what the router frames did.

### D2. The exploration root is an empty, resolvable menu

The root frame must stay resolvable, because "only an unresolvable ROOT frame degrades in place into the single disabled marker-reason row" (router contract). `exploration.root` resolves to `{items: [], title: "場景"}` with no `geometry`. `dockSource === "exploration.root"` remains the marker for "the exploration dock is live". The router never claims a compass, rail, or place-card key, because those zones handle their keys locally and stop propagation. If an empty root exposes a router assumption (a non-empty root in Escape or digit handling), the fix is in the router with a Node test; no placeholder item is added.

### D3. Place-card buttons

Two real `<button>`s inside `PlaceCard`, each a tab stop, emitting `look-room` and `wait`. The card stays `pointer-events` aware: today it is display-only, so only the buttons receive pointer events. Buttons mount only when `AppClient` passes `actionsEnabled` (mode exploration and exploration panel available). The heading keeps its full accessible name; the button group must not truncate it (ellipsis applies to the visible text only).

### D4. Suggestions card rows

Rows come from the same builder as the old pane, rendered as `ChoiceCard` rows (label, optional second line for `hint`), so `ChoiceCard` gains an optional per-row `hint`. The envelope an activated row dispatches stays the one `OptionCard` builds; extract that mapping into a pure helper both use if `OptionCard` is still used elsewhere (the narrative choice-point), otherwise delete `OptionCard`/`ChoiceCardRow` and their manifest entries with the story evidence. The generating and degraded notes render as non-selectable lines in the card. The dismiss row stays above `✕ 返回` (the redesign does not drop dismiss) and keeps the label 清除建議, but its leading mark is a trash-can glyph in the dock icon vocabulary (an `aria-hidden` SVG, not the ✕ character), so it no longer looks like the adjacent `✕ 返回` (user decision, 2026-10-10).

### D5. Wait card rows

Rows: 等待直到黎明, 睡眠至完全恢復, 休息 N 小時 (opens `RestForm` exactly as today), then `✕ 返回`. Disabled while a mutation is in flight or awaiting revision, with the same reason text as the old controls.

The dream-collaboration variant is no longer a row. Choosing 睡眠至完全恢復 opens a small modal question, 進入夢境協作？, with 是 and 否 buttons and a ✕ close at its top right (user decision, 2026-10-10): 是 dispatches `explore.wait` with `{sleep: true, dream: true}`, 否 dispatches `explore.wait` with `{sleep: true}`, and ✕ (also Escape) cancels the sleep, dispatches nothing, closes the question and returns to the wait card. The server cannot enter the dream after a plain sleep (`CmdSleep` records the start tick before advancing and `enter_after_sleep` consumes it), so the question is asked BEFORE the single request is sent; no protocol change. The modal uses the same card frame as `ChoiceCard` but its own two-button layout, traps focus on 是, and is locked like the other wait rows while a mutation is in flight.

### D6. Readout priority is one pure function

The priority helper from change 1 gains the place-card and pill sources and reaches its final form: flash, then aimed or hovered (compass, rail, place-card button, pill), then idle. Hover and focus on each source set and clear a source slot; leaving one source falls back to the next live slot. The readout also replaces `exploration-detail` as the place where server-authored disabled reasons appear, so the `exploration-detail` element and its `showDetail` rules are removed for exploration.

### D7. Removals and CSS

Remove `SceneOverview.vue`, its story, tests, and manifest entries; the `sections` geometry in `keyboard_router.js` (with its Node tests) and `overviewMenu` once `grep -rn "sections"` shows no remaining user; `waiting-screen`/`waiting-card`/`waiting-back` styles; and `.elosern-root` duplicates in `styles/app-shell.css` for every removed or restyled class (grep first, per AGENTS.md).

### D8. Spec bookkeeping

The two MODIFIED deltas here validate against current main. The previous change's interim root requirement exists in main only after it archives, so the REMOVED block for it is added at apply time (tasks 1.1).

## Risks / Trade-offs

- **Empty router root.** Mitigated by D2 and a Node router test.
- **Suggestions behavior drift.** Row envelopes must stay byte-identical; a Vitest test compares every card kind's emitted intent with the pre-change `OptionCard` output.
- **Tests that reach the old frames.** Many Vitest and browser tests open wait or suggestions through the footer; tasks 4 and 5 list them.
- **Dream question and dismiss row.** Both preserve reachable behavior the redesign text did not mention; the user decided their forms (a yes/no question before sleeping, and a trash-can icon on the dismiss row).
- **Spec text spread.** `webclient-desktop-shell` and `webclient-pointer-activation` name the overview footer, the waiting frame, and the pane host; task 5.2 authors those MODIFIED deltas.

## Open Questions

None.
