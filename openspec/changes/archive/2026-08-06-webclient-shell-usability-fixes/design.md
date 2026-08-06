## Context

The version-1 desktop shell (`webclient-oob-foundation`), the minimap (`map-knowledge-minimap`), the service, creation, combat, and exploration docks, and the art panel have all landed. The server side is healthy: presenters emit validated panels, the dispatcher gates epoch/revision/in-flight, and the deterministic core is untouched by any of this. What has never been exercised end-to-end is the *presentation* half of the browser. Four defects, all in landed browser code, currently make the client unusable:

1. `goldenlayout.js:appendNarrative` inserts `args[0]` of Evennia's `text` message through `document.createTextNode`. But the portal already ran `evennia.utils.text2html.parse_html` on that string (`webclient.py::_send_text_legacy`), so what arrives is HTML — player-authored content already `html.escape`d, wrapped in `<span class="color-NNN">`, `<br>`, and occasionally `<a>`. Text-node insertion therefore prints the markup source. The project also deleted the 512 `.color-NNN`/`.bgcolor-NNN` rules when it replaced Evennia's stock `webclient.css` with its own 77-line file, so even correct spans would render unstyled.

   Two paths into `onText` are *not* `parse_html` output and must be accounted for rather than assumed away: `webclient_gui.js` synthesizes `onText(["The connection was closed or lost."], {cls:"err"})` and `onText(["Attempting to reconnect..."], {cls:"sys"})` client-side, and Evennia's `_send_text_legacy` has a `client_raw` branch that sends `text` completely unescaped. The synthesized strings are hardcoded ASCII and tokenize to a single text token, so they are safe by content rather than by contract; `client_raw` is reachable only through `@py`-class builder commands, which already imply code-execution-equivalent access. Both are recorded below as bounded, tested assumptions rather than as an unconditional "the portal escapes everything" claim.
2. Every dock (`exploration_dock.js`, `services_dock.js`, `creation_dock.js`, `combat_dock.js`) renders its rows with `makeElement("button", …)` and never attaches a listener. `grep addEventListener("click"` across `web/static/webclient/js/plugins/` matches only `goldenlayout.js` (the drawer send button, the unread marker, map nodes, art images). The action dock is keyboard-only by accident, not by design — `webclient-desktop-shell` already assumes mouse activation exists ("keyboard or mouse activation emits no mutation") and `webclient-local-map` already specifies "click or Enter". Separately, `elosern_ui.js` binds `document.addEventListener("keydown", routeKeyboard)` instead of exposing the plugin's `onKeydown` hook, so `plugin_handler.onKeydown` falls through every plugin and logs `NO plugin handled this Keydown` on every keystroke.
3. `local_map.js::normalizeLayout` rescales every node into `x ∈ [-64,64]`, `y ∈ [-32,32]`, and `goldenlayout.js::renderLocalMap` places nodes at `left: x+64px`, `top: y+32px`. The entire graph therefore occupies 128×64 CSS pixels while a four-character Chinese room label is 60–90 px wide. The normalization input includes `remembered` nodes, which the grid adapter emits at their *real* grid coordinates far outside the visual range, so the in-view neighbourhood collapses to a couple of pixels. `.local-map-canvas` reserves only `min-height: 3rem` and the nodes are `position: absolute`, so they escape the canvas and overprint the legend. Edges are `div`s sized to the endpoint *bounding box*, which draws a filled rectangle rather than a line.
4. Both drawer send paths (`elosern_ui.js::sendDrawerText` and the drawer component's own `sendCurrent`) end with `closeDrawer(true)`, which focuses `#action-dock`. Sending two commands in a row therefore needs a mouse click in between. The two functions are near-duplicates that both fire for the same Enter keypress and only avoid a double send because the field's listener happens to clear `drawerOpen` before the document listener reads it.

Constraints that shape every decision below: the shell must make no remote request; no `innerHTML` may appear in the shell plugins (enforced by `ui_contract.test.js`); DOM-independent logic lives under `js/elosern/` with Node tests and must not touch `document`/`window` at load time; every main-spec requirement needs a substantively matching test (`tools.spec_traceability`); and the project is unreleased, so no compatibility layer is warranted.

## Goals / Non-Goals

**Goals:**

- The narrative log renders Evennia's ANSI→HTML stream as styled, correctly line-broken text, with colors visible against the ink-night theme and server-rendered ASCII/box map art aligned.
- Rendering server markup does not widen the client's trust surface: everything outside a closed, tested allowlist degrades to visible literal text, and no element, attribute, URL, or handler is ever created from server bytes outside that allowlist.
- Every action-dock row is activatable with the mouse, on exactly the same path as Enter: same focus event, same disabled explanation, same in-flight/awaiting-revision suppression, same single `ui_action`.
- The rows a dock renders are always exactly the keyboard router's current menu frame, in every mode.
- The minimap is readable at the pane's real size: no overlapping labels, no content escaping its container, and no false adjacency implied between the local neighbourhood and remembered remote locations.
- Consecutive commands are typeable in the drawer without touching the mouse.
- `plugin_handler` stops logging `NO plugin handled this Keydown`, because the project routes keydown through the documented plugin contract.

**Non-Goals:**

- No change to any presenter, action adapter, panel payload, schema validator, protocol version, or deterministic rule. This change is browser-side presentation only.
- No new runtime dependency, no sanitizer library, no build step, no npm package.
- No MXP support. Evennia can emit `|lc`/`|lu` links; the project authors none, and this change deliberately does not add a way to execute a server-supplied command from a click.
- No mobile or touch support. Pointer means mouse on the two supported desktop viewports.
- No redesign of the menu hierarchies, panel contents, or theme. Rows keep their current labels, order, and semantics.
- No horizontal-scroll-free rendering of arbitrarily wide map art in the narrative; long lines wrap as they do today.

## Decisions

### D1 — Parse the narrative stream with a hand-written allowlist tokenizer, not `innerHTML`, `DOMParser`, or a sanitizer library

`web/static/webclient/js/elosern/narrative_markup.js` exports `tokenize(source)` returning a bounded, flat token list, and the renderer in `goldenlayout.js` walks that list building elements with `createElement`/`createTextNode`. The module touches no DOM API, so the Node suite exercises the whole grammar directly.

Alternatives rejected: `innerHTML` would break the standing `ui_contract.test.js` prohibition and hand the browser's full HTML parser a server string; `DOMParser` moves the same problem behind a different API and still requires an allowlist walk afterwards; DOMPurify would be a vendored runtime dependency for a grammar with five productions.

Grammar accepted (exactly what `parse_html` can emit):

| Production | Handling |
| --- | --- |
| Text | `createTextNode` after decoding only `&amp; &lt; &gt; &quot; &#x27; &#39; &nbsp;` |
| `<br>` / `<br/>` / `<br />` | `createElement("br")` |
| `<span class="…">` / `</span>` | `createElement("span")`; classes filtered by `^(?:color-\d{3}|bgcolor-\d{3}|underline|blink)$`; unmatched classes dropped |
| `style="color: #rrggbb;background-color: #rrggbb;"` on a span | Only these two declarations, only 6-digit hex, applied via `element.style.color` / `element.style.backgroundColor`; anything else drops the whole attribute |
| `<a …>` / `</a>` | See D2 |

Everything else — an unknown tag, an unknown attribute, a malformed tag, an unbalanced close, nesting past depth 32, or more than 4096 tokens in one message — is emitted as a **literal text token** and rendered verbatim. Degrading to visible text rather than silently dropping means an upstream change to `parse_html` shows up in the narrative instead of quietly disappearing, and it can never create an element.

A Python contract test closes the loop against upstream drift: it feeds a fixture corpus (including hostile player input such as `<script>`, `<img onerror=…>`, quote/entity soup, and every ANSI/xterm/truecolor/blink/underline combination) through the real `parse_html`, then runs the JS tokenizer over the results under Node and asserts that no output token is a literal-text fallback caused by an unrecognized tag or attribute. If Evennia starts emitting something new, that test fails rather than the player seeing raw markup again.

### D2 — Anchors degrade to their text content

`parse_html` produces three anchor shapes: an MXP command link carrying an inline `onclick="Evennia.msg(…)"`, an MXP URL link, and an auto-linked bare URL from `convert_urls`. Keeping the command link would require reconstructing a command from an attribute we are about to discard, and would give server prose a way to make a click send arbitrary text as the player. Keeping the URL links would give server prose a way to open an external origin from inside the client.

Decision: `<a …>` and `</a>` are consumed, their attributes discarded, and their inner content rendered as ordinary narrative text. Nothing is hidden — the label still reads — and no navigable or clickable element is created. Revisit only if the project ever authors MXP.

### D3 — Generate the ANSI/xterm-256 palette with a deterministic contrast floor

`tools/gen_ansi_palette.py` writes `web/static/webclient/css/ansi_palette.css`: the 16 ANSI entries, the 6×6×6 cube on the standard levels `[0x00, 0x5f, 0x87, 0xaf, 0xd7, 0xff]`, and the 24-step grayscale ramp, emitted as `.color-000…255` and `.bgcolor-000…255`. (The standard cube is used rather than copying Evennia's stock sheet, which has a long-standing `0xdf`-instead-of-`0xd7` quirk at level 4.)

Foreground entries pass through a contrast floor: while the WCAG contrast ratio against `--elm-ink` (`#171512`) is below 3.0, blend the color 10% toward `--elm-paper` (`#ece7db`), up to 9 steps. Without it, `color-000` (`#000000`) and the bottom of the grayscale ramp are invisible on the near-black page. Background entries are emitted raw — they are a background, and the span's own foreground class handles legibility. The generator is pure and a repository test regenerates and byte-compares, so the checked-in CSS can never drift.

`.blink` uses the same keyframe animation as upstream but is neutralized under `@media (prefers-reduced-motion: reduce)` to a dotted underline, satisfying the shell's existing reduced-motion requirement.

### D4 — The narrative surface becomes monospace-first

The narrative currently uses `"Noto Serif TC", "Songti TC", Georgia, serif`, so Latin and box-drawing glyphs are proportional and the room description's xyzgrid art renders as ragged noise even once the spans are correct. The narrative switches to a monospace-first stack (`"DejaVu Sans Mono", "Noto Sans Mono CJK TC", Consolas, monospace` ahead of the CJK proportional fallbacks), keeping `white-space: pre-wrap` so leading indentation in map art survives. CJK glyphs fall through to a CJK face and remain double-width in practice, which is the standard arrangement for a CJK MUD client.

The alignment guarantee is deliberately scoped to rows that fit the pane's content width. `.elosern-narrative` keeps `overflow-wrap: break-word`, so a row wider than the pane still soft-wraps and its continuation is not column-aligned; a horizontal-scroll narrative is out of scope. The requirement and its acceptance test are written to that scope rather than claiming alignment unconditionally, and a browser assertion covers the wide-row wrap case so the shipped behavior is the documented behavior.

### D5 — One delegated pointer listener on `#action-dock`, activation routed through the keyboard router

`#action-dock` is created once by `registerActionDock` and every dock replaces only its children, so a single delegated `click` listener installed at shell init survives every re-render — no per-row binding, no leak on the frequent full re-renders, no ordering dependency on which dock is mounted.

The handler resolves `event.target.closest("[data-item-key]")`, then calls:

```
keyboard.focusItemByKey(key);      // new: moves the frame's focus, emits "focus"
keyboard.confirm({ source: "pointer" });   // new: confirm() exposed, with a source
```

`confirm({source})` reuses the existing body verbatim — disabled items emit `disabled` and submit nothing, `mutationInFlight || isAwaitingRevision()` emits `locked` and submits nothing — with one difference: a pointer confirm neither consults nor sets the Enter `repeatGuard`, because that guard exists to suppress *key repeat* and would otherwise wrongly reject a legitimate second click on the same row.

Alternatives rejected: per-dock click handlers duplicate the gating logic five times and drift; calling `dock.handleItem(item)` directly from the click bypasses the router's disabled/locked/focus contract entirely, which is precisely the bug class the router exists to prevent.

### D6 — Composite-widget focus model, and three guards against double or stale activation

A focused native `<button>` fires a synthetic `click` on Enter and Space. With a keydown router *and* a delegated click listener, that is a double activation. Separately, a *navigation* row (`openSubmenu`, or combat's `attack`/`skills`/`forfeit` keys) calls `router.pushMenu` rather than `actions.submit`, so the in-flight mutation lock does not protect it — a second pointer activation that reaches a row the first one already replaced would double-push a frame and desynchronize the menu stack. Three guards, each independently meaningful:

- **Rows are never the keyboard focus target.** Rows carry `tabindex="-1"` and stable ids; the row container carries `role="listbox"`, `tabindex="0"`, and `aria-activedescendant` naming the focused row, and rows carry `role="option"` with `aria-selected`. Standard `listbox`/`option` roles are used rather than an ad-hoc "listbox-style" arrangement of bare buttons, because active-descendant announcement is only reliably supported on a real composite role. The roles go on the *row container* (`.exploration-menu`, `.services-menu`, `.combat-controls`, …) rather than on `#action-dock`, which also holds a heading, a detail pane, and a live region and therefore cannot be a listbox. `#action-dock` keeps `tabindex="0"` and forwards focus to the active listbox when one is mounted, so "the action dock owns focus" still holds and `closeDrawer`'s existing `#action-dock` focus call needs no caller changes. Because the roles and attributes are DOM-observable, a Playwright assertion covers them — this is not left to manual screen-reader verification.
- **Only a primary single activation is admitted.** The delegated handler activates only when `event.detail === 1`. `detail === 0` identifies a keyboard-synthesized click; `detail > 1` identifies the repeat events of a multi-click.
- **A stale row cannot activate.** After resolving `event.target.closest("[data-item-key]")`, the handler ignores the activation when the resolved row is no longer connected to the document. A dock that re-rendered in response to the first activation detaches its old rows, so a second click whose target belongs to a replaced frame is rejected regardless of timing. This makes the guard explicit rather than relying on the unstated assumption that every dock's router-event re-render is synchronous — which the shared renderer does guarantee, and which task 5.4 asserts, but which should not be the only thing standing between a fast double activation and a desynchronized menu stack.

`mousedown` on a row calls `preventDefault()` and explicitly focuses the active listbox container, so DOM focus stays on the composite widget and the visible focus ring stays where the router says it is.

### D7 — A shared dock surface renderer makes "rows == current router frame" a dock-wide invariant

`web/static/webclient/js/plugins/dock_surface.js` exposes `window.Elosern.DockSurface` with `renderRows(container, items, { focusKey, keyPrefix })` and `installPointerBridge()`. Every dock's `_renderMenuItems`-shaped function collapses onto it, so `data-item-key`, the focused/disabled classes, `aria-disabled`, `aria-activedescendant`, and the `（無法使用）` suffix are produced in exactly one place.

The invariant matters beyond deduplication. `combat_dock.js` renders only `panel.root_actions`; opening Skills, a target list, a shorthand choice, or the Forfeit confirmation pushes a router frame that has **no DOM at all**, so today the player navigates those menus blind with only the detail pane as feedback. Pointer activation cannot be defined against a dock whose rows disagree with the router, so the combat dock adopts the shared renderer and re-renders from the router's current frame on every `focus`/`menu-closed` event — which also repairs the pre-existing blind-navigation bug against the already-written requirement that "Skills SHALL open the complete active-skill list".

The character dock stays display-only: its rows become focusable-by-pointer (a click moves focus and updates the detail pane) but carry no action and submit nothing, exactly as its rows behave under the keyboard today.

The invariant is about *router frames*, and three surfaces are deliberately outside it because they are modal forms that are never pushed onto the router stack at all: the creation dock's text/numeric fields, `services_dock.js::_renderQuantityForm`, and `exploration_dock.js::_renderRestForm`. Each captures its own keys while open and restores the router frame when it closes. They keep that behavior unchanged, and both the requirement text and this document name them explicitly so "no pushed frame lacks a rendered representation" is not read as a demand to convert them into rows.

### D8 — Keydown moves onto the plugin `onKeydown` hook

`routeKeyboard` moves from `document.addEventListener("keydown", …)` onto `plugin.onKeydown`, returning `true` exactly when the router consumed the key and `false` otherwise. `elosern_ui.js` is the last script in `base.html`, so it is last in `ordered_plugins` and the stock plugins (notably `history.js`'s Shift+Arrow recall) keep their earlier turn. This removes the console noise, puts the project back on the documented dispatch contract, and makes the "which handler owns this key" question answerable from the plugin list.

The exploration dock's rest-duration form keeps its own capture-phase listener: it is a modal numeric capture that must pre-empt the router, and capture phase is the honest way to express that.

### D9 — The drawer keeps focus after an ordinary send; the drawer component owns the single send path

The send logic is deduplicated onto the drawer component created in `registerCommandDrawer`, exposed as `window.Elosern.drawer.send()`. `elosern_ui.js` delegates to it instead of carrying a second copy. Post-send focus:

| Trigger | Field | Drawer state | Focus |
| --- | --- | --- | --- |
| Ordinary text send (Enter or the send button) | cleared | stays open | stays in the field |
| Free-form dialogue send consumed by the exploration dock | cleared | closes | `#action-dock` |
| Escape | preserved, unsent | closes | `#action-dock` |

Ordinary sends are the overwhelmingly common case and are inherently repetitive, so retaining focus is the correct default; Escape is the documented, discoverable way back to the menu surface. A free-form dialogue send is different in kind — the dock *borrowed* the drawer for one action that has now completed — so focus returns to the dock that owns the interaction. This modifies the shell's existing "close on successful send and restore action-dock focus" requirement, and the browser-verification journey that asserts it, rather than quietly diverging from them.

Consolidating the send path also forces a latent hijack to be resolved rather than inherited. `exploration_dock.js` sets `_pendingFreeform` when the player opens free-form dialogue, `sendDrawerText` consults `consumeFreeformText(text)` on **every** send, and `_pendingFreeform` is cleared only on a *successful* consume — never on Escape or on any other drawer close. Today a player who opens free-form dialogue and cancels leaves the flag set, and their next unrelated typed command is silently converted into `explore.talk_freeform` speech to that NPC. Retaining drawer focus makes multi-command drawer sessions the normal workflow, which is precisely the pattern that turns this from a rare surprise into a repeatable one. The pending free-form reference is therefore cleared whenever the drawer closes for any reason other than a successful free-form consume, and whenever a send is routed as ordinary text. This is in scope because tasks 7.2/7.3 rewrite exactly this code, not because the change set out to fix it.

### D10 — The minimap moves to a bounded integer lattice with the remembered set outside the canvas

Three coupled changes:

- **Model** (`local_map.js`): `normalizeLayout`'s pixel rescale is deleted. `reducePanel` splits nodes into `nodes` (visibility `current`, `visible_unvisited`, `visible_visited`) and `remembered` (a bounded list, order preserved from the payload). Lattice coordinates are computed over `nodes` only: `col = x - minX`, `row = y - minY`, with `cols`/`rows` exported. If that span would exceed 64×64 cells — possible only for a schema-valid but geometrically sparse payload, since `x`/`y` may be anywhere in `-1024..1024` — the model falls back to rank compression (distinct sorted `x` values → column index, likewise `y`), which cannot exceed 64×64 because the payload carries at most 64 nodes. Both paths are deterministic and unit-tested.
- **Renderer** (`goldenlayout.js`): the canvas is sized `cols × --elm-map-cell-w` by `rows × --elm-map-cell-h` so it reserves real space and the pane scrolls instead of letting nodes overprint the legend. Nodes stay absolutely positioned but at true cell centres. Labels are single-line with `text-overflow: ellipsis`, and the full label lives in `aria-label`/`title`. Remembered nodes render as a bounded list below the canvas — keeping their `◆` prefix, dashed-border marker, and focus-only click behaviour — under the legend text the payload already supplies for them (`曾經到過、但不在附近的遠方位置`).
- **Edges**: the bounding-box `div`s are replaced by a single `<svg>` layer built with `createElementNS`, one `<line>` per edge between cell centres, sized to the canvas and `pointer-events: none` so it never intercepts a node click. Edge labels move to the line's `aria-label` instead of a positioned text span; they were pure clutter at this scale. An edge whose endpoint is not on the canvas (i.e. touches a remembered node) is skipped, matching the existing behaviour for endpoints missing from the node set.

Excluding remembered nodes from the coordinate canvas is the load-bearing part. Their coordinates are real but describe places outside the current field of view: on the grid layer they can be dozens of cells away (which is what destroys the normalization), and on the interior/instance layer the adapter assigns them synthetic `(index, 0)` slots in the same row as the current room's exits, which would render them as false neighbours. A list is also a better match for what the spec already requires of them — focusable, name and landmark shown, no travel action.

Alternative rejected: CSS Grid placement. It solves overlap elegantly but makes edge geometry inexpressible without measuring laid-out cells, which reintroduces DOM measurement into a surface that must render deterministically from the model.

### D11 — No compatibility layer

The old text-node narrative, the pixel-normalized map model, and the focus-stealing drawer are removed outright rather than kept behind a flag. There are no released users, `AGENTS.md` forbids speculative compatibility shims, and a dual rendering mode would double the test matrix for the exact surfaces this change exists to make trustworthy. Browser `localStorage` is unaffected: the layout store persists only dimensions, tabs, and preferences, none of which this change touches.

## Risks / Trade-offs

- **Rendering server-produced markup is a genuinely new trust surface** → Player-authored content is already `html.escape`d by `parse_html` before the client sees it, so on the ordinary path the client trusts the *portal*, not the player. On top of that: a closed allowlist, degradation to literal text (never silent dropping, never element creation) for everything outside it, no `innerHTML`/`DOMParser` anywhere on the path, anchors reduced to text so no navigable or command-carrying element exists, and a hostile-input corpus in the Node suite (`<script>`, `<img onerror>`, `javascript:` URLs, entity and quote soup, unbalanced tags, deep nesting, oversize input).
- **The "portal escapes everything" invariant has two exceptions that must stay exceptions** → Evennia's `_send_text_legacy` `raw`/`client_raw` branch sends `text` unescaped, and `webclient_gui.js` synthesizes two hardcoded connection notices straight into `onText`. Neither is attacker-influenced today (the raw options are reachable only through builder-locked `@py`-class commands, and the notices are fixed ASCII), but the tokenizer cannot tell a trusted string from an untrusted one. Mitigated by a repository test asserting that no project code path passes `raw` or `client_raw` on a `msg()`/`send_text` call, so the exception cannot silently widen; the requirement text is scoped to the converted transport stream rather than claiming a blanket guarantee.
- **Upstream `parse_html` could start emitting something the allowlist does not know** → The Python contract test drives the real `parse_html` over the fixture corpus and fails if the tokenizer falls back to literal text for any of it. The failure mode without that test is a silent regression to today's bug.
- **`prefers-reduced-motion` users and the `blink` class** → Explicitly neutralized to a dotted underline; covered by the palette test.
- **Pointer and keyboard double-firing the same row** → Two independent guards (`tabindex="-1"` composite focus so rows never take keyboard focus, and `event.detail === 1`), each individually sufficient, with browser tests asserting exactly one `ui_action` per activation for both input methods.
- **Two rapid activations of a *navigation* row could double-push a router frame** → Navigation rows call `pushMenu`, not `actions.submit`, so the in-flight mutation lock does not cover them, and a pointer confirm deliberately skips the Enter repeat guard. Mitigated by the stale-row guard in D6 (an activation whose resolved row is no longer connected to the document is rejected) plus `event.detail === 1`, so correctness does not depend on the unstated assumption that every dock re-renders synchronously on a router event.
- **A cancelled free-form dialogue could hijack the next ordinary command** → Pre-existing, and made more likely by the new multi-command drawer session; resolved in D9 by clearing the pending free-form reference on any drawer close and on any ordinary send, with a spec scenario and a browser assertion.
- **Almost every new requirement is verified in JavaScript, but traceability only accepts a Python test** → `tools.spec_traceability` can attach `covers_requirement` only to a discoverable Python `test_*`, and this change adds two JS-only test files and extends two more. Mitigated by extending `web/webclient/tests/test_node_suite_evidence.py` with one subprocess bridge test per new or modified requirement, following the pattern that already exists there for the protocol reducer and keyboard router; the tasks list this explicitly rather than folding it into a final "annotate everything" step, because under-scoping it would fail the `spec_traceability check` and `openspec validate --all --strict` gates at the very end of the work.
- **Touching all five docks in one change risks a mode-ownership regression** → The docks' mount/unmount, mode-exclusivity, and teardown logic is not modified; only the row-rendering call site changes. The existing browser suites for combat, services, creation, and exploration all assert mode ownership and teardown and must stay green.
- **The lattice can produce a canvas wider than the pane** (grid `visual_range` is capped at 8, so up to 17 columns) → The pane scrolls in both axes and labels ellipsize. This is a deliberate trade against the alternative of compressing real distances, which would make the map lie about adjacency.
- **Moving remembered nodes into a list is a visible behaviour change for anyone used to the current render** → The current render is unreadable, no user has seen a working version, and the payload contract, visibility states, and no-travel rule are all unchanged; only the presentation of one visibility class moves.
- **The generated palette is 512 rules of checked-in CSS** → It is generated by a pure function and verified byte-for-byte by a repository test, so it is data rather than code to maintain; the alternative (styling spans from JS) would put color decisions on the hot render path.
