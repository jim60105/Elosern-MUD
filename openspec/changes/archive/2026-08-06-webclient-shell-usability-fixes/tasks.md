## 1. Narrative markup tokenizer (DOM-independent)

- [x] 1.1 Implement `web/static/webclient/js/elosern/narrative_markup.js` following the existing
      UMD wrapper idiom used by `local_map.js` (`module.exports` under Node, `root.Elosern.NarrativeMarkup`
      in the browser) with no `document`/`window` access at load time. Export `tokenize(source)` returning
      a flat, ordered token list of `{ kind: "text", value }`, `{ kind: "break" }`, `{ kind: "open",
      tag: "span", classes: [...], style: { color?, backgroundColor? } }`, and `{ kind: "close", tag:
      "span" }`. Export the bounds `MAX_TOKENS = 4096` and `MAX_DEPTH = 32` and the allowlist constants
      so tests and the renderer read one source of truth.
- [x] 1.2 Implement the accepted grammar exactly: literal text with entity decoding restricted to
      `&amp;`, `&lt;`, `&gt;`, `&quot;`, `&#x27;`, `&#39;`, `&nbsp;`; `<br>` / `<br/>` / `<br />`;
      `<span class="...">` / `</span>` with classes filtered by `/^(?:color-\d{3}|bgcolor-\d{3}|underline|blink)$/`;
      an optional `style` attribute on a span parsed strictly as zero or more of `color: #rrggbb` and
      `background-color: #rrggbb` (any other declaration, shorthand, or value form drops the whole
      attribute); and `<a ...>` / `</a>`, whose attributes are discarded and whose inner content is
      emitted as ordinary text tokens (no anchor token kind exists).
- [x] 1.3 Implement the degradation rule: an unknown tag, an unknown or disallowed attribute (including
      any `on*`), a malformed or unterminated tag, an unbalanced `</span>`, nesting past `MAX_DEPTH`, or
      exceeding `MAX_TOKENS` emits the offending source characters as a `text` token and continues (or,
      at a bound, emits the entire remainder as one `text` token and stops). Nothing is ever dropped
      silently and no non-allowlisted element kind is ever produced.
- [x] 1.4 Write `web/static/webclient/js/tests/narrative_markup.test.js` (Node 24 `node:test`) covering:
      the plain-text and entity cases; every `<br>` spelling; nested and adjacent spans with color,
      bgcolor, underline, and blink classes; truecolor `style` acceptance and rejection of a
      non-hex/shorthand/extra-property style; class filtering that keeps text while dropping the class;
      anchor degradation for the MXP-command, MXP-URL, and auto-linked-URL shapes (asserting no anchor
      token and no reconstructed command); hostile inputs (`<script>`, `<img onerror=...>`,
      `javascript:` URL, quote/entity soup, unbalanced tags, `<span` with no `>`); depth and token
      bounds; and the empty/whitespace-only message.

## 2. ANSI palette generation, contrast floor, and narrative typography

- [x] 2.1 Implement `tools/gen_ansi_palette.py` as a pure generator emitting the 16 ANSI entries, the
      6x6x6 cube on component levels `0x00, 0x5f, 0x87, 0xaf, 0xd7, 0xff`, and the 24-step grayscale
      ramp as `.color-000`..`.color-255` and `.bgcolor-000`..`.bgcolor-255`. Apply the foreground
      contrast floor: while the WCAG contrast ratio against `#171512` (`--elm-ink`) is below 3.0, blend
      10% toward `#ece7db` (`--elm-paper`), for at most 9 steps. Background entries use the raw palette
      value. Output is deterministic and byte-stable.
- [x] 2.2 Generate `web/static/webclient/css/ansi_palette.css` from the generator and commit it. Add the
      `underline` and `blink` rules, with `blink` neutralized to a static dotted underline under
      `@media (prefers-reduced-motion: reduce)`.
- [x] 2.3 Write `web/webclient/tests/test_ansi_palette.py` asserting that regenerating the stylesheet
      reproduces the committed file byte-for-byte, that all 256 foreground and 256 background classes are
      present exactly once, that every foreground entry clears the 3.0 contrast floor, and that the
      reduced-motion block exists.
- [x] 2.4 Load `webclient/css/ansi_palette.css` from `web/templates/webclient/base.html` after
      `webclient.css` and before `elosern.css`, and switch `.elosern-narrative` in
      `web/static/webclient/css/elosern.css` from the serif stack to a monospace-first stack
      (`"DejaVu Sans Mono", "Noto Sans Mono CJK TC", Consolas, monospace` ahead of the CJK proportional
      fallbacks) while keeping `white-space: pre-wrap` on the output lines.

## 3. Narrative rendering and the upstream contract gate

- [x] 3.1 Replace `appendNarrative`'s `setText(line, text)` in
      `web/static/webclient/js/plugins/goldenlayout.js` with a renderer that walks `NarrativeMarkup.tokenize(text)`
      and builds nodes with `createElement`/`createTextNode` only, maintaining an element stack for
      span open/close and applying `element.style.color` / `element.style.backgroundColor` for accepted
      truecolor declarations. Keep the existing `.out` line wrapper, the at-bottom detection, and the
      unread-count behavior byte-for-byte. Do the same for `onPrompt`'s prompt surface, which receives
      the same converted stream.
- [x] 3.2 Load `webclient/js/elosern/narrative_markup.js` in `web/templates/webclient/base.html` before
      `plugins/goldenlayout.js`, and confirm the shell still renders with the module absent by falling
      back to literal text (a defensive path, not a supported mode).
- [x] 3.3 Write `web/webclient/tests/test_narrative_markup_contract.py`: build a fixture corpus covering
      hostile player input (script element, `onerror` attribute, `javascript:` URL, quote/entity soup,
      unbalanced tags, oversized string), every ANSI and xterm-256 foreground/background combination,
      truecolor, blink, underline, tabs, and newlines; pass each through the real
      `evennia.utils.text2html.parse_html`; run the tokenizer over the results via a `node --eval`
      subprocess (mirroring the `test_node_suite_evidence.py` bridge); and assert no token is a
      literal-text fallback caused by an unrecognized element or attribute, and that no token of a kind
      outside the allowlist is produced.
- [x] 3.4 Extend `web/static/webclient/js/tests/ui_contract.test.js`: keep the existing "no `innerHTML`"
      assertion for `goldenlayout.js`, and add assertions that neither the shell plugins nor
      `narrative_markup.js` reference `DOMParser`, `insertAdjacentHTML`, `outerHTML`,
      `createContextualFragment`, `document.write`, or `eval`, and that `narrative_markup.js` contains no
      `document.` reference.
- [x] 3.5 Add a repository test asserting the converted-stream assumption stays bounded: no project code
      under `commands/`, `server/`, `typeclasses/`, `web/`, or `world/` passes `raw` or `client_raw` in a
      `msg()`/`send_text` options mapping, so no narrative output can bypass `parse_html`'s escaping.
      Assert the two client-synthesized notices the stock handler inserts (`connection_close` and the
      reconnect notice) tokenize to a single text token.

## 4. Keyboard router pointer API

- [x] 4.1 Extend `web/static/webclient/js/elosern/keyboard_router.js` with `focusItemByKey(key)`, which
      locates the item with that key in the current frame (list index or grid row/col), sets
      `focusRow`/`focusCol`, emits `focus`, and returns `false` without side effects when the key is not
      in the current frame.
- [x] 4.2 Change `confirm()` to `confirm(options)` accepting `{ source: "keyboard" | "pointer" }`
      (default `"keyboard"`) and export it on the router's public API. A pointer confirm keeps the
      disabled -> `disabled` event, the `mutationInFlight || isAwaitingRevision()` -> `locked` event, and
      the `submit` event unchanged, but neither reads nor writes `repeatGuard`. `press(ENTER)` continues
      to call `confirm()` with the keyboard source, so held-Enter suppression is untouched.
- [x] 4.3 Extend `web/static/webclient/js/tests/keyboard_router.test.js` with: focus-by-key hit and miss;
      pointer confirm on an enabled item emitting exactly one `submit`; pointer confirm on a disabled
      item emitting `disabled` and no `submit`; pointer confirm while `setMutationInFlight(true)` or
      `setAwaitingRevision(n)` emitting `locked`; two consecutive pointer confirms on the same enabled
      item both emitting `submit` (the repeat guard must not apply); and an unchanged held-Enter
      suppression case.

## 5. Shared dock surface and the delegated pointer bridge

- [x] 5.1 Implement `web/static/webclient/js/plugins/dock_surface.js` exposing
      `window.Elosern.DockSurface` with `renderRows(container, items, { focusKey, idPrefix })`. It clears
      the container and renders one `<button type="button">` per item carrying `data-item-key`, a stable
      `id` of `<idPrefix>-<index>`, `tabindex="-1"`, the `focused` class plus the container's
      `aria-activedescendant` for the focused row, and the `disabled` class, `aria-disabled="true"`, and
      the `（無法使用）` label suffix for a disabled row. All text goes through `createTextNode`.
- [x] 5.2 Add `DockSurface.installPointerBridge()`, called once from `elosern_ui.js` init, registering a
      single delegated `click` listener and a single delegated `mousedown` listener on `#action-dock`.
      `mousedown` on a row calls `preventDefault()` and focuses the active row container. `click`
      resolves `event.target.closest("[data-item-key]")` and activates only when `event.detail === 1`
      **and** the resolved row is still connected to the document (`row.isConnected`), then calls
      `keyboard.focusItemByKey(key)` followed by `keyboard.confirm({ source: "pointer" })`. The
      `isConnected` check is what stops a second rapid activation on a *navigation* row — which pushes a
      frame instead of submitting and is therefore not covered by the in-flight mutation lock — from
      double-pushing after the first activation's re-render detached the old rows. The bridge performs no
      submission itself and knows nothing about any specific dock.
- [x] 5.3 Give the row container real composite semantics: `role="listbox"`, `tabindex="0"`, and
      `aria-activedescendant` naming the focused row, with rows carrying `role="option"` and
      `aria-selected`, all managed by `DockSurface`. In `registerActionDock` (`goldenlayout.js`) make
      `#action-dock` keep `tabindex="0"` and forward `focus()` to the mounted row container when one
      exists, so `closeDrawer`'s existing `#action-dock` focus call and the shell's "action dock owns
      focus" contract need no caller changes. Add the matching row/focus CSS in
      `web/static/webclient/css/elosern.css` so `.focused` is visible without relying on `:focus-visible`
      on the row itself.
- [x] 5.4 Write `web/static/webclient/js/tests/dock_surface.test.js` exercising `renderRows` against a
      minimal DOM double (plain objects implementing the element methods used, in the style of the
      existing DOM-free tests) for row attributes, roles, focused/disabled markers, and label suffixing;
      exercising the bridge's activation predicate across `detail === 0`, `1`, `2` and across
      `isConnected` true/false; and asserting the focus-then-confirm call order against a stub router.
      Add an assertion that a router `focus`/`menu-closed` event re-renders rows synchronously, so the
      invariant the stale-row guard backstops is itself covered.

## 6. Dock adoption of the shared surface

- [x] 6.1 Replace `_renderMenuItems` in `web/static/webclient/js/plugins/exploration_dock.js` with a call
      to `DockSurface.renderRows`, preserving `_currentItems()`, the detail-pane hint, and the live
      region. Remove the now-duplicated row markup.
- [x] 6.2 Do the same for `_renderMenuItems` in `web/static/webclient/js/plugins/services_dock.js` and for
      `_renderRootMenu`, `_renderPresetList`, and `_renderConfirmButtons` in
      `web/static/webclient/js/plugins/creation_dock.js`, keeping each dock's existing view logic,
      form handling, and confirmation screens unchanged. The creation dock's text/numeric form fields keep
      their own focus handling and stay outside the row model.
- [x] 6.3 Convert the character dock's `character-row` divs
      (`web/static/webclient/js/plugins/character_dock.js`) to `DockSurface` rows marked as
      non-submitting, so a click moves router focus and updates the detail pane and no row carries an
      action.
- [x] 6.4 Make `web/static/webclient/js/plugins/combat_dock.js` render the router's current frame instead
      of only `panel.root_actions`: keep `pushCombatMenus` as the frame owner, add an `onRouterEvent`
      bridge (wired from `elosern_ui.js` alongside the other docks) that re-renders rows on `focus`,
      `menu-closed`, and `escape-root`, and render skills, target lists, shorthand choices, and the
      forfeit confirmation through `DockSurface.renderRows`. Keep `combat-detail`, the live region,
      `publishFocusForItem`, mode ownership, and teardown unchanged.
- [x] 6.5 Verify by inspection and test that no dock retains its own row-building code, that
      `data-item-key` is the single row identity attribute, and that the previous per-dock attributes
      (`data-exploration-key`, `data-service-key`, `data-creation-key`, `data-preset-key`, `data-action`)
      are removed along with any test selector that used them.

## 7. Plugin keydown contract and the single drawer send path

- [x] 7.1 In `web/static/webclient/js/plugins/elosern_ui.js`, remove
      `document.addEventListener("keydown", routeKeyboard)` and expose `onKeydown: routeKeyboard` on the
      plugin object, returning `true` exactly when the router consumed the event and `false` otherwise
      (including for every key typed inside the drawer field that the drawer does not claim), so
      `history.js` keeps its Shift+Arrow recall. Confirm `elosern_ui.js` remains the last plugin script in
      `base.html`.
- [x] 7.2 Move the single send implementation onto the drawer component in
      `registerCommandDrawer` (`goldenlayout.js`), expose it as `window.Elosern.drawer` with
      `send()`, `open()`, `close(restoreFocus)`, and `isOpen()`, and delete
      `elosern_ui.js::sendDrawerText`, delegating `routeKeyboard`'s Enter/Escape handling and the
      `open-drawer` router event to it. Exactly one listener must handle a given Enter press.
- [x] 7.3 Implement the post-send focus contract: an ordinary text send clears the field, leaves the
      drawer open, and keeps focus in the field; a free-form dialogue send consumed by
      `explorationDock.consumeFreeformText` clears the field, closes the drawer, and focuses
      `#action-dock`; Escape closes without sending, preserves the typed text, and focuses
      `#action-dock`. Update the send button to follow the same contract. Track the field's real focus
      state instead of the statically applied `focused` class.
- [x] 7.4 Release the borrowed-drawer reference so a cancelled dialogue cannot hijack a later command:
      add `explorationDock.clearPendingFreeform()` and call it whenever the drawer closes for any reason
      other than that dock's own successful consume (Escape, mode change, epoch change, dock unmount) and
      whenever a send is routed as ordinary text. Today `_pendingFreeform` is cleared only on a successful
      consume, so a cancelled free-form dialogue silently converts the next unrelated typed command into
      `explore.talk_freeform` speech — a latent defect that the new "drawer stays open for consecutive
      commands" behavior would otherwise make routine.
- [x] 7.5 Update `web/static/webclient/js/tests/ui_contract.test.js` so the drawer assertions target the
      new single owner (no `ui_action` construction on the drawer path, ordinary text still routed through
      `plugin_handler.onSend`), and add an assertion that `elosern_ui.js` no longer binds a bare
      `document` keydown listener outside the documented modal-capture exception.

## 8. Local-map lattice render model

- [x] 8.1 Rewrite `reducePanel` in `web/static/webclient/js/elosern/local_map.js`: delete
      `normalizeLayout` and the `MAX_LAYOUT_X`/`MAX_LAYOUT_Y` pixel caps, split the payload's nodes into
      `nodes` (`current`, `visible_unvisited`, `visible_visited`) and `remembered` (payload order
      preserved, bounded by the payload's own node cap), and compute lattice coordinates over `nodes`
      only as `col = x - minX`, `row = y - minY`, exporting `cols` and `rows`.
- [x] 8.2 Add the bounded fallback: when the computed lattice would exceed `MAX_LATTICE = 64` columns or
      rows, rank-compress instead (distinct sorted `x` values to column indices, distinct sorted `y`
      values to row indices), which cannot exceed the payload's 64-node bound. Both paths are pure and
      deterministic; keep `focusTargets` semantics for remembered nodes and keep `STATE_INDICATORS`
      unchanged.
- [x] 8.3 Rewrite `web/static/webclient/js/tests/local_map.test.js` for the lattice model: distinct
      in-view coordinates map to distinct cells preserving relative order; remembered nodes never appear
      in `nodes` and never influence `cols`/`rows`; a distant remembered node leaves the local spacing
      intact; a sparse payload triggers rank compression and stays within `MAX_LATTICE`; a single-node
      payload yields a 1x1 lattice; and the non-color state indicators are unchanged.

## 9. Local-map renderer, edge layer, and pane containment

- [x] 9.1 Rewrite `renderLocalMap` in `web/static/webclient/js/plugins/goldenlayout.js` to size
      `.local-map-canvas` from `cols`/`rows` and CSS custom properties for cell width and height, and to
      place each node at its cell center. Keep the existing node classes, the `node-action-ready` /
      `node-focusable` behavior, `submitLocalMapMove`, and the `explore.move` payload construction exactly
      as they are.
- [x] 9.2 Replace the bounding-box edge `div`s with one `<svg>` layer created through
      `document.createElementNS`, sized to the canvas, `pointer-events: none`, containing one `<line>` per
      edge between cell centers. Edge labels move to the line's `aria-label`; an edge with an endpoint not
      on the canvas is omitted.
- [x] 9.3 Render `remembered` nodes as a bounded list below the canvas, keeping their `◆` prefix and
      dashed-border marker, keeping the focus-only click that writes the name/landmark into
      `#local-map-detail`, and carrying no travel action.
- [x] 9.4 Update the local-map CSS in `web/static/webclient/css/elosern.css`: define the cell custom
      properties, make node labels single-line with ellipsis and the full label in `title`/`aria-label`,
      let `.elosern-local-map` scroll in both axes, and remove or raise the `max-height: 10rem`
      narrow-viewport clamp that currently truncates the pane before its own scroll can help.

## 10. Browser acceptance

- [x] 10.1 Extend `web/tests/browser/test_browser_shell.py` (or the matching foundation journey) with:
      two consecutive drawer commands sent with no pointer interaction and focus asserted to remain on
      `#inputfield`; Escape closing the drawer with focus asserted on `#action-dock`; and a free-form
      dialogue send asserted to return focus to `#action-dock`.
- [x] 10.2 Add a narrative rendering journey asserting that after `look` the narrative contains the room's
      prose, contains no literal `<span`/`&lt;`/`&amp;` source characters, and that at least one rendered
      segment carries a `color-NNN` class from the palette. Add a wide-row assertion: a rendered row wider
      than the pane soft-wraps inside the pane, is not clipped, and does not make the page scroll
      horizontally — matching the scoped alignment guarantee rather than an unconditional one.
- [x] 10.3 Add a pointer-only journey (new `web/tests/browser/test_browser_pointer.py`) at both supported
      viewports covering: an exploration root entry and one submenu submission by click; a service
      submenu submission by click; a combat root action and one combat submenu selection by click; a
      disabled row click that explains and emits nothing; a rapid double activation on a navigation row
      asserting exactly one frame push (one Escape returns to root); and a click under the offline overlay
      that emits nothing. Each asserts the exact `ui_action` count and payload through
      `install_outbound_recorder` / `sent_action_count`. Add a composite-semantics assertion: the row
      container exposes `role="listbox"` with `tabindex="0"` and `aria-activedescendant`, rows expose
      `role="option"` with `aria-selected`, and no row is reachable by sequential Tab navigation.
- [x] 10.4 Extend `web/tests/browser/test_browser_local_map.py` with a containment assertion at 1440x900
      and 1280x720: every node marker's bounding box is inside the map canvas, no two node markers
      overlap, and the legend and detail line remain visible.
- [x] 10.5 Add a keydown-noise assertion to an existing shell journey: capture browser console output
      during a keyboard navigation sequence and assert `NO plugin handled this Keydown` never appears.
- [x] 10.6 Add a drawer-hijack assertion to the exploration browser journey: open free-form dialogue,
      press Escape without sending, then send an ordinary command through the drawer and assert it travels
      as text with no `explore.talk_freeform` action emitted.
- [x] 10.7 Re-run the existing keyboard-only combat, service, creation, and exploration browser suites
      unchanged and confirm they stay green, including mode ownership and teardown.

## 11. Repository contracts, traceability, and final verification

- [x] 11.1 Extend `web/webclient/tests/test_node_suite_evidence.py` with one subprocess bridge test per
      new or modified requirement whose only substantive verification lives in JavaScript, following the
      four-function pattern already in that module. `covers_requirement` attaches only to a discoverable
      Python `test_*`, and this change adds `narrative_markup.test.js` and `dock_surface.test.js` and
      extends `keyboard_router.test.js` and `local_map.test.js`, so every `webclient-narrative-markup` and
      `webclient-pointer-activation` requirement plus the modified `webclient-local-map` rendering
      requirement needs a bridge. Do this before task 11.4, not as part of it — it is the work that makes
      the traceability gate passable, not an annotation pass.
- [x] 11.2 Run the Node gate: `node --test web/static/webclient/js/tests/*.test.js`.
- [x] 11.3 Run the affected Python ownership domains:
      `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb web.webclient`
      and `uv run --locked python -m unittest discover -s web/tests/browser -t .`.
- [x] 11.4 Annotate the substantive test for each new or modified main-spec requirement with
      `covers_requirement`, using canonical IDs from
      `uv run --locked python -m tools.spec_traceability list`, and run
      `uv run --locked python -m tools.spec_traceability check`.
- [x] 11.5 Run `openspec validate webclient-shell-usability-fixes --strict` and
      `openspec validate --all --strict`.
- [x] 11.6 Confirm the change added no runtime dependency, no npm package, no build step, no database
      migration, no presenter/adapter/payload/protocol change, and no backward-compatibility layer; and
      that `git diff --check` is clean.
