## Context

See proposal.md (Why). C1–C5, C6a (`webclient-message-pages`), C6b (`webclient-message-window-component`), and C6c (`webclient-message-window-swap`) are assumed archived first. State after them, taken from those changes' designs and from the code:

- `components/MessageWindow.vue` (C6b) is mounted in `#band-message` by `AppShell.vue` (C6c).
  - Props: `lines`, `marks`, `mode`, `dialogue`, `artPanel`, `fontScale`, `pageFit`.
  - Reader state (C6b D3): `responseKey`, `pageIndex`, and `anchorOffset`, the response offset of the first character on screen. A re-page sets `pageIndex = pageIndexForOffset(pages, anchorOffset)`.
  - It has one "page shown" moment. There the live region (`message-live`) receives the page's text, with fragments deduplicated by `${seq}:${start}` (C6b D5).
  - The marker `message-page-marker` reads `▼` / `■`. The page surface `message-page` takes Enter/Space only when it is the event target (C6b D4).
  - The dialogue variant is unpaged (C6b D6).
- C6a's shapes (`lib/message_pages.js`):
  - A page is `{ blocks: [fragment], oversize }`.
  - A fragment is `{ kind, seq, mapArt, first, tokens, start, end }`, with `start` / `end` as response offsets. A `text` token counts its code points, and a `break` counts 1.
  - Offsets may skip a dropped leading break at a cut, so a page's units are the sum of its fragments' `end − start`, not `last.end − first.start`.
  - `paginate` cuts inside spans by closing the open spans and re-opening shallow copies (C6a D4).
  - `narrativeBlockNodes(fragment, key)` (`lib/narrative_line_nodes.js`) renders a fragment through `renderNarrativeTokens` (`components/narrative-renderer.js`).
- Preferences (`stores/elosern/preferences.js` `applyPreferences`):
  - `prefs = { fontScale, text2html, reducedMotion, colorblind }`. `reducedMotion` is `null | "on" | "off"`, and it is stored as an optional boolean.
  - `applyPresentationPreferences` writes `--prose-scale`, `data-reduced-motion`, and `data-colorblind` on `<html>`.
  - `persistPresentationPreferences` reloads the wrapper and saves it. `loadPresentationPreferences` validates each key.
  - `stores/elosern/view.js` publishes `fontScale`, `textToHtml`, `reducedMotion`, and `colorblind`. `AppClient.vue` binds them into `SettingsOverlay` (`@scale-change`, `@reduced-motion-change`, …).
- The layout store is the UMD `web/static/webclient/js/elosern/layout_store.js`, wrapped by `web/webclient-app/lib/layout_store.js`.
  - `CURRENT_LAYOUT_VERSION = 1`. `PREFERENCE_TYPES` supports only `"boolean"` and `"number"`, and the number case is special-cased for `fontScale`.
  - `createStore` defaults `migrations` to `{ 1: identity }`. `read()` resets a wrapper whose version has no migration.
  - H5 added `reducedMotion` and `colorblind` without a bump.
  - The snapshot envelope's `layout_version` (`web/webclient/presentation/protocol.py`, `protocol/envelope.js`) is a separate server field, and this change does not touch it.
- `composables/use-overlays.js` computes `openSurfaces` (full log, creation, the HUD drawer, the HUD overlay), and `AppClient` already passes it to `AppShell` as `open-surfaces`.
- Motion: `styles/tokens.css` shortens the `--motion-*` tokens to 1ms under `@media (prefers-reduced-motion: reduce)` when `html` lacks `data-reduced-motion="off"`, and under `html[data-reduced-motion="on"]`. No script reads the media query today.
- `webclient-options-surface` is the suggestions-card capability (its Purpose names the dock's suggestions section), not the settings surface. The settings rules live in `webclient-contextual-hud` "Narrative prose scale is a client-local preference the settings surface owns" and in `webclient-component-showcase` "The full overlays are complete…". This change's settings requirement therefore goes to `webclient-contextual-hud`, not to the capability that design §14 names.

## Goals / Non-Goals

**Goals:**
- Pages type in without re-layout, span-correct, and at a bounded render cost.
- Every existing reading guarantee holds with typing: announce once, key scope, flush, re-page, and mount.
- Two persisted preferences, and reduced motion wins over them.

**Non-Goals:**
- Typing the dialogue line (C10).
- A general presentation queue, `motionLevel`, and transitions (C11). The typewriter clock here is local to the window. C11 may absorb it as the queue's page step.

## Decisions

### D1. Reveal by hiding the unrevealed tail, not by truncating
The page is always rendered at its full, measured content. At a typed count `n`:
- Each fragment before the typing position renders as today.
- Each fragment after it renders with the class `unrevealed` on its line `div`.
- The fragment holding the position is split with `splitTokensAt(tokens, k)`:
  - The head renders through `renderNarrativeTokens` as before.
  - The tail renders through the same function inside `span.narrative-unrevealed` (`aria-hidden="true"`).
- `.narrative-unrevealed` and `.narrative-line.unrevealed` are `visibility: hidden`. A `sys` line's `◈` marker is a `::before`, so it stays hidden with its `unrevealed` line and appears with the first revealed character.

Why this approach:
- *Correctness.* `visibility: hidden` keeps the layout, so every glyph sits where the measurer (C6b D2) put it. No Latin word jumps lines as it completes, and the fully shown page is exactly the page that paging measured.
- *Markup.* The split re-opens the same `open` tokens (C6a D4), so a coloured span's visible head and hidden tail carry the same classes and style. Only the pipeline's own token kinds are rendered. The wrapper span is client chrome with a fixed class, never built from server markup. The tokenizer does not run again: `splitTokensAt` works on the stored tokens.
- *Performance.* A page holds at most about 250 characters (6 lines × 42). The typed count changes at most `cps` times per second (≤ 90), and each change patches one fragment's two children. No measuring runs during typing.

Alternatives:
- *Truncating the tokens to `n`* (render only the revealed prefix). Rejected. Wrapping changes as a Latin word grows, which makes the text jump. The page's height also grows, so its geometry no longer matches the measured page.
- *Wrapping every character in a span and toggling a class.* Rejected. It puts about 250 extra elements on each page and changes the DOM that screen readers and the browser tests read, for no gain over one split per frame.
- *CSS `clip-path` per fragment.* Rejected. A wrapped fragment spans several line boxes, and a single clip rectangle cannot reveal "the first line plus part of the second" without measuring the line boxes on every frame.
- *The CSS Custom Highlight API* (`::highlight` with `color: transparent`). Rejected. Background-coloured `bgcolor-*` spans would still paint, the text would stay in the accessibility tree, and it would add a browser floor.

### D2. Reveal units and map art
The lib counts reveal units exactly as C6a counts offsets: one per code point, and one per `break`. A page's units are `Σ (fragment.end − fragment.start)`.
- `fragmentReveal(page, n)` walks the fragments and gives each a revealed count in `[0, len]`.
- `snapUnits(page, n)`: a map-art fragment is all or nothing. When `n` lands inside one, it moves to that fragment's end, so box-drawing art never appears half drawn.
- `offsetAtUnits` / `unitsAtOffset` convert through the fragment walk, so gaps from dropped breaks do not shift the position.

### D3. One clock: `use-typewriter.js`
`useTypewriter({ units, snap, cps, held })` runs one `requestAnimationFrame` loop while it has work.
- `elapsed += min(frameDelta, 100)`. A hidden tab gets no frames, and the clamp stops a long gap from counting on return.
- The typed count is `snap(min(units, start + floor(elapsed × rate / 1000)))`, where `rate` is `cps()` sampled once at `start()`. Re-reading `cps` every frame would rescale the whole elapsed time on a mid-page speed change and could hide characters already shown. With `rate = Infinity` (instant), the count is `units` on the first call, with no frame.
- The composable exposes:
  - `typed` (a ref) and `typing` (a computed)
  - `start(fromUnits)`, `complete()`, and `stop()`
  - `armAdvance(ms, onDue)` and `disarmAdvance()`. The advance countdown uses the same clamped elapsed time, and it does not accumulate while `held()` is true.
- `stop()` and unmount cancel the frame.

*Why rAF and not `setInterval`:* frames stop in a hidden tab, so neither typing nor the auto-advance wait runs in the background. The same clock serves both, so they cannot drift. Vitest fakes `requestAnimationFrame` and `performance` with `vi.useFakeTimers({ toFake: [...] })`.

### D4. Rates, defaults, and reduced motion
- `TEXT_SPEED_CPS = { slow: 20, normal: 45, fast: 90 }`, and `instant` gives `Infinity`.
  - `normal` is the design's ≈45.
  - `slow` is under half of it, so a full 252-character page takes about 12.6s, the slow end of common visual-novel defaults.
  - `fast` is double, so a full page takes about 2.8s.
- `use-reduced-motion.js`: `useReducedMotion(override)` returns a computed boolean.
  - `"on"` gives `true`, and `"off"` gives `false`.
  - `null` follows `matchMedia("(prefers-reduced-motion: reduce)").matches`, through a `change` listener removed on unmount.
  - With no `matchMedia` (jsdom without a mock), it gives `false`.

  This mirrors the CSS rule in `styles/tokens.css` exactly, so the stylesheet and the typewriter never disagree.
- The effective speed is `instant` while reduced motion is effective. A switch to `instant` or into reduced motion calls `complete()` on the typing page. Any other speed change applies from the next `start()`, so the page on screen never changes pace mid-line.
- C11 replaces `reducedMotion` with `motionLevel`, and `use-reduced-motion.js` goes with it.

### D5. Integration with C6b's reader state
Every transition from C6b D3 keeps its trigger. What it does to the typewriter:

| Moment | Typewriter |
|---|---|
| A page starts to show (new response page 1, or an advance) | Announce the page's text once (C6b D5 unchanged), then `start(0)` |
| Mount (and reconnect remount) | `typed = units` (complete), with no announcement |
| Pending mark or new response (flush) | `complete()` on the old page, then `disarmAdvance()`. The previous response's last page shows complete. The new response's page 1 then `start(0)`s |
| Lines appended to the page on screen | The page's `units` grow. If it was complete, `start(oldUnits)` resumes. C6b's appended-fragment announcement is unchanged |
| Re-page (box, `fontScale`, fonts ready) | Anchor = typing position (D6) |
| Click / Enter / Space | If `typing`, `complete()`. Otherwise advance (C6b) |
| Fonts not ready | The unpaged first block is shown whole. Typing starts when paging does, from page 1 unit 0, for a response that arrived after the window mounted. The window remembers the response on screen at its first fonts-not-ready pass; when paging first runs, a different response opens on page 1 and types, and the mount's own response settles on its last page as a mount does |

The marker's `v-if` adds `!typing`. The root gains `data-typing`. The hidden `第 N／M 頁` description is unchanged.

*Why the announcement stays at page start:* design §6.3 asks for the full text once, when the page is shown. Announcing at completion would delay speech by up to 12s at `slow`, and per-character updates would flood the polite queue. The page surface is not live, and unrevealed text is `aria-hidden`, so a screen-reader user browsing the surface hears only what is visible. The live region has already spoken the whole page.

### D6. The re-page anchor is the typing position
C6b anchored to the first character on screen, because instant pages show everything at once. With typing, the reader's frontier is the typing position, as the coordinator notes on C6 ask:
- While typing: `anchor = offsetAtUnits(page, typed)`, the next character to reveal.
- When complete: `anchor = offsetAtUnits(page, units) − 1`, the last character shown. The page end is exclusive, and anchoring there would land on the next page and skip what the reader was reading.

The anchor is read from the page on screen at the start of each re-page, before the new pages replace it. It is a local value of that pass, not a variable updated only when a page is set. After re-paging, `pageIndex = pageIndexForOffset(pages, anchor)`, and the window `start`s at `unitsAtOffset(newPage, anchor)` while typing, or `unitsAtOffset(newPage, anchor + 1)` when complete (so an anchor on a break dropped at the new cut resumes at the next page's start). The complete-page rule also covers lines appended to the page on screen: the resume point is the old unit count, so the new lines type. Text before the anchor on the new page shows at once, and the rest types. This implements design §6.2's "the first character they had not yet seen". Text before the anchor that falls onto an earlier page is not shown again. The window has no back step, so it stays readable in the full log. That is the same trade C6b made.

### D7. Auto-advance
- The window arms `armAdvance(autoAdvanceDelayMs(page), advance)` whenever all of these hold:
  - `autoAdvance` is on
  - the variant is paged
  - `!typing`
  - a next page exists
  - `autoAdvanceAllowed(page)`: the page is not `oversize` and holds no `mapArt` fragment
- It disarms on any other state.
- Re-evaluating on "a next page appears" gives the "later of the two moments" rule in the spec.
- `held` is `openSurfaces.length > 0`, bound by `AppShell`. It pauses the countdown, so opening the log or a drawer never pages away unseen text.
- `1200 + 60 × units`: 100 characters wait 7.2s, and a full 252-character page waits 16.3s.

Decisions the design doc left open:
- **Auto-advance stops at the last page** of a response. The next response starts from its own action, and advancing past `■` has no target.
- **Map and oversize pages never auto-advance.** An oversize page needs scrolling, and a map needs study that the character formula does not model.
- **The wait pauses under open surfaces**, as above.

### D8. A new action cancels typing
C6b's flush (the pending mark, or a new `responseKey`) now also completes and stops typing and disarms auto-advance. This is design §9.2's "a new player action flushes … to their end state", applied locally before C11 introduces the queue. Nothing is lost: the pages remain in the full log.

### D9. The dialogue variant does not type
C6b D6 renders the reply, the residual lines, and the pick rows together in a scroll region, with no reading controls. Typing the reply there would:
- show live choices beside a reply the player has not seen yet
- have no complete-gesture, because clicks and Enter are deliberately not intercepted in the variant
- still need the one-announcement rule for a line that is not a page

C10 pages the dialogue line and moves the choices so that they appear after the last page. The typewriter then applies through the ordinary paged path with no extra work. The dialogue-mode fallback with the panel unavailable is a normal paged view, so it types.

### D10. Preferences and the layout store
- `prefs.textSpeed = "normal"` and `prefs.autoAdvance = false`.
  - `setTextSpeed(value)` ignores anything outside `TEXT_SPEEDS`. `setAutoAdvance(on)` coerces to a boolean.
  - Both call `applyPresentationPreferences` (which publishes the view; neither writes a document attribute, because the window reads them as props) and `persistPresentationPreferences`, which now writes both keys.
- `loadPresentationPreferences` accepts `textSpeed` only when it is in `TEXT_SPEEDS`, and `autoAdvance` only when it is a boolean.
- `view.js` publishes `textSpeed` and `autoAdvance`. `stores/elosern.js` exports both setters.
- `TEXT_SPEEDS` is exported from `lib/message_reveal.js`, and the store imports it from there. The UMD layout store cannot import ESM, so it carries its own copy in `PREFERENCE_ENUMS.textSpeed`. A node test asserts that the two lists are equal.
- Layout store:
  - `CURRENT_LAYOUT_VERSION = 2`.
  - `PREFERENCE_TYPES` gains `textSpeed: "enum"` and `autoAdvance: "boolean"`. `normalizePreferences` accepts an enum value only when it is in `PREFERENCE_ENUMS[key]`.
  - `defaultWrapper().preferences` gains `textSpeed: "normal"` and `autoAdvance: false`.
  - `createStore`'s default `migrations` becomes `{}`.

  *Why bump although the keys are additive:* the coordinator asked for it, and the version now names the wrapper's schema, which gains a new value type. Zero users means no migration is written. A version-1 wrapper resets to the default, which the spec pins. The 2048-byte cap is unaffected: two short keys.
- Settings UI (`SettingsOverlay.vue`, 閱讀設定 section):
  - A `文字速度` row with four `affbtn` buttons (`慢`, `標準`, `快`, `瞬間`), testids `settings-overlay-text-speed-{slow,normal,fast,instant}`, `aria-pressed`, and the `.on` class as the non-colour indicator the scale buttons already use. Its description is `逐字顯示訊息的速度；減少動態效果開啟時一律立即顯示。`.
  - A `自動翻頁` checkbox row, testid `settings-overlay-auto-advance`, with the description `每頁顯示完畢後稍候自動翻頁；回應的最後一頁不會自動翻過。`.
  - Props `textSpeed` and `autoAdvance`. Emits `text-speed-change` and `auto-advance-change`.
- The component-showcase "full overlays" requirement lists the four existing settings as the ones the overlay SHALL expose. The list does not exclude more, and its token rule reads per listed setting, so it is not modified. The contextual-hud settings requirement, which says "every other setting the surface offers … applied to the document's presentation tokens", is modified to say "applied to the presentation it governs". Its stale "narrative caption's lines" also becomes the message window's page text.

### D11. Tests and browser determinism
- **Vitest.**
  - `tests/message_reveal.test.js`: units with breaks and dropped-break gaps, `fragmentReveal`, map-art snap, offset round-trips, delay and allowed rules. It also checks that the markup of `splitTokensAt` head + tail equals the unsplit markup, for nested spans and `degraded` text.
  - `tests/message_window_typing.test.js` uses a code-point `pageFit` and fake rAF. It covers:
    - typing at each speed, and the marker absent while typing
    - click and Enter completing, then advancing, with a key repeat ignored
    - flush completing typing
    - the re-page anchor while typing and when complete
    - one announcement per page, none per character
    - reduced motion through an override, and through a mocked `matchMedia` with `null`
    - auto-advance timing, stopping at the last page, pausing on `held`, and skipping map and oversize pages
    - the dialogue variant not typing
  - The existing `tests/message_window.test.js` (C6b) mounts with `textSpeed: "instant"` in its shared helper, so its instant-page assertions stay valid. Its prose-scale case now expects the page holding the last character shown (D6), not the first character on screen. `tests/full_log_overlay.test.js` mounts the window with `textSpeed: "instant"` too, because it reads page 2's text right after a click.
  - `tests/store/reading_preferences.test.js` covers the preference slice.
  - `tests/overlays/settings_overlay.test.js` covers the new controls.
- **Browser.** Default-speed typing would make DOM text assertions depend on timing. `browser_helpers.wait_for_page_shown(page)` waits for `[data-testid="message-window"][data-typing="false"]`.
  - Every C6c assertion that reads `inner_text()` or visibility on `message-page` calls the helper first (`test_browser_shell_narrative.py`). Chromium's `innerText` skips `visibility: hidden` text, while `textContent` keeps it, so the `textContent`-based err-line reads in `test_browser_exploration_actions.py` need nothing.
  - The C6c paging journeys (the shared `_append_multipage_response` helpers of `test_browser_input_narrative.py` and `test_browser_shell_command_line.py`) assert paging, not typing, so the helper pins the text speed to `instant` through the store before it appends, as the "A click advances the page" scenario does. Typing is covered by the new journeys below.
  - Assertions on classes and element presence need nothing, because hidden text stays in the DOM.
  - New journeys in `test_browser_input_narrative.py`:
    - `test_message_page_types_and_completes` at 1920×1080: marker absent while typing, Enter completes, Enter advances, rendered line boxes unchanged between typing and complete
    - `test_reduced_motion_pages_are_instant`: `page.emulate_media(reduced_motion="reduce")`
    - `test_reading_preferences_persist`: select `快` and `自動翻頁`, reload, and check the wrapper holds `textSpeed: "fast"`, `autoAdvance: true`, and `layout_version: 2`, with no `ui_action` sent

### D12. Spec strategy, traceability, and archive order
| Requirement | Written on |
|---|---|
| input-narrative "The message window's reading controls advance pages and a new action flushes unread pages" | C6c `webclient-message-window-swap` (ADDED there) |
| contextual-hud "The message window presents the current response one page at a time in the band's message region" | C6c (ADDED there) |
| contextual-hud "Narrative prose scale is a client-local preference the settings surface owns" | main spec (no series change touches it) |
| desktop-shell "Browser persistence is versioned and presentation-only" | main spec (no series change touches it) |

- Every scenario title of each MODIFIED block is kept, so no annotation moves. One scenario is added to reading controls, and one to persistence.
- New IDs:
  - `webclient-input-narrative::a-page-types-in-at-the-reader-s-text-speed-and-auto-advance-is-opt-in`, covered by `test_message_window_typing_vitest_evidence_passes` in `test_node_suite_evidence.py` and by the typing browser journeys
  - `webclient-contextual-hud::text-speed-and-auto-advance-are-client-local-reading-preferences-the-settings-surface-owns`, covered by `test_reading_preferences_persist`

  Confirm both slugs with `uv run --locked python -m tools.spec_traceability list` after syncing.
- `openspec validate` reports that the two C6c-based blocks cannot apply until C6c is archived. That is expected.
- **Archive order: C6a → C6b → C6c → C7 (this change).** If C6c's reading-controls or message-window text changes before archive, re-sync this change's blocks, keeping only its own edits (typing, marker timing, anchor, announcement moment). C10 later modifies the reading-controls and typing requirements on this change's text.

## Risks / Trade-offs

- [Typing slows every browser test that reads page text] → The `data-typing` wait, or an Enter to complete, is added only where text or visibility is asserted. Store-backed waits (C6a) are unaffected.
- [Hidden text can still be selected and copied] → A drag selection over unrevealed text copies it. This is harmless, since the text is committed and in the log, and a selection-ending click never advances (C6b D4).
- [Re-rendering a fragment every tick] → The cost is bounded by `cps` (≤ 90/s) and only the split fragment changes. Vue's keyed children keep the other fragments' vnodes stable.
- [A version-1 wrapper resets the player's prose scale once] → Zero users. The reset is the documented behaviour, pinned by a scenario.
- [The budget is tight] → The work is about 8 hours: lib and composables (2.5h), window integration (2h), preferences, store, and settings (1.5h), browser (1.5h), specs and gates (0.5h). The browser suite changes are waits added only where text is asserted, not rewrites.

## Migration Plan

None. A stored version-1 wrapper resets to the version-2 default on first load. Nothing else is persisted.
