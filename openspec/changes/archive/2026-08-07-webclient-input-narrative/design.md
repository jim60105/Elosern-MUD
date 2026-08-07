## Context

The desktop WebClient (GoldenLayout shell + KeyboardRouter + action client) already routes `/` to a
single `open-drawer` event and always renders the bottom command drawer with its input row visible.
The narrative log currently renders only server text (`onText` → `appendNarrative`), so typed
commands and button-triggered `ui_action` mutations never appear in the log and the play flow is not
re-readable as an action→result story. The project's invariants require: single-writer state (nothing
under `web/static/webclient/js/plugins/` may mutate game state), no client-side duplication of
availability rules, allowlisted dispatch (U9) with no arbitrary command strings, and a strict
DOM-independent Node test boundary for all pure modules. There are no released users, so no
migrations or back-compat layers are required.

## Goals / Non-Goals

**Goals:**
- `/` toggles the drawer (open+focus / close+restore dock focus) and never fires while an editable
  control is focused, so slash-containing text stays typeable.
- The drawer defaults to closed behind an actionable entry button, with the exact same send/focus
  semantics once opened.
- Typed drawer commands and button-triggered mutations echo exactly one readable command line into
  the narrative at dispatch time, with a divider before each player input line; locked submissions
  never echo and never clear borrowed text.
- The echo is pure client presentation: deterministic, literal text, no dispatch/state effect, fully
  Node-testable.

**Non-Goals:**
- No server/panel `command` fields, no Python/presenter/protocol changes.
- No command execution from the log; no replay; no typing tutor UI.
- No layout-store or localStorage changes (drawer open state is runtime-only).
- No changes to the action-dispatch protocol envelope or adapters.

## Decisions

### D1 — Drawer toggle lives in the browser routing gate, not in the router

`KeyboardRouter` is DOM-independent and must not know drawer state. The router keeps emitting an
event on `/`; the event name changes `open-drawer` → `toggle-drawer` to state the intent truthfully.
The `routeKeyboard` gate in `plugins/elosern_ui.js` decides open vs close:
- `/` on a non-editable target → if `drawer.isOpen()` → `drawer.close(true)`; else
  `keyboard.handle("/")` → `toggle-drawer` → `drawer.open()`.
- `/` while **any editable control** is focused (`isEditable(target)` or `isDrawerField(target)`) →
  claimed, not `preventDefault`-ed, so the `/` is typed as text; the drawer never closes. This
  covers the drawer field and other editable controls (creation forms, rest forms) uniformly: the
  slash never toggles while text could be being typed.

**Why this over a router-side state?** The router never touches `document`; drawer state is a browser
concern (Node tests cannot see it). Keeping the decision in the gate preserves the router's purity
and keeps the existing `isEditable` gate intact.

### D2 — Default-closed drawer via a real entry button

`registerCommandDrawer` starts with `drawerOpen = false`. The drawer root carries
`data-open="false"` and `aria-expanded="false"`. When closed, CSS hides both `.prompt` and
`.inputfieldwrapper` and shows a dedicated **entry button** (`<button class="drawer-entry"
type="button">` with accessible name `指令輸入（/）`); clicking it opens and focuses the field. When
open, the entry button is hidden and `.prompt`/`.inputfieldwrapper` are shown; `open()` sets
`data-open="true"` + `aria-expanded="true"` before focusing, `close()` reverses it. GoldenLayout
keeps its reserved 9% band so no `stateChanged`/layout-store churn occurs.

**Why a dedicated button and not the `.prompt` row?** `.prompt` is a plain div that the server
(`onPrompt`) overwrites and it has no keyboard semantics; a real `<button>` gives click/Enter/Space
activation, an accessible name, and an `aria-expanded` state. Clicking the entry button preserves
the "pointer-opened field sends on Enter" scenario, which a `display:none` field alone cannot.

### D3 — One display-only command-line catalog, fed by bounded display descriptors

New `web/static/webclient/js/elosern/command_echo.js` (UMD, DOM-independent, stateless):
`commandLine(actionId, payload, display)` returns a bounded string or `null`. The menu model
builders attach `item.commandDisplay` at build time from the validated panel data they already hold —
exit label (move rows, local-map nodes), NPC display name (talk/engage targets), keyword label,
skill label, quantity, seconds/daypart — so the catalog never guesses names from opaque ids. The
catalog:
- Maps each supported mutation to its canonical typed command **where the server exposes one**
  (verified against `commands/*.py`): `talk <NPC> <話題>`, `engage <目標>`, `cast <技能>[=<目標>]`
  (target token or AREA shorthand from the payload), `wait <時段>`, `rest <秒數>`, `sleep`,
  `buy <物品> <數量>`, `sell <物品> <數量>`, guild/creation forms, etc.
- For actions with no typed equivalent — `combat.flee`, and exit traversal (no `move` command
  exists; movement is the exit's own traversal) — emits the bounded **server-authored action
  label** (e.g. the exit label or `逃跑`), documented as an action description, never a guessed
  command.
- Returns `null` for navigation/back/disabled/submenu items and unknown `actionId`s (silent).
- Truncates any label-derived string to a bounded length; rendering stays literal text.

**Why client-side instead of server-authored `command` panel fields?** Adding `command` to the five
panel schemas (exploration, combat, services, creation, local-map) would touch every presenter, the
protocol validators, and their Python tests — a much larger, server-touching surface for a
presentation-only feature. The catalog is a single Node-testable module that cannot drift from
dispatch (it never feeds back into payloads), and it reuses the server labels the client already
trusts (U7). The trade-off — the catalog mirrors the command grammar — is bounded by Node tests that
pin each spelling, and by the label fallback where no command exists.

### D4 — Exactly one echo per deliberate mutation, at dispatch, gated on a request id

`createBrowserActions` gains an optional `echo(text)` callback and `submit(actionId, payload,
display)` calls it **only when `client.submit()` returns a request id** (a real dispatch). Locked,
duplicate, or in-flight submits return `null` and never echo. `wireActions` binds `echo` to
`window.Elosern.narrativeInput.appendInput` (a goldenlayout facade). Every submit call site passes a
`commandDisplay` descriptor built by its menu model (D3).

- **Typed drawer sends** (ordinary text branch only) append the raw typed text through
  `appendInput`, exactly once per `send()`.
- **Borrowed free-form dialogue** is owned by the action path, not the drawer: the exploration dock
  builds the display line (`talk <NPC> <speech>`) and calls `actions.submit(...)`; the echo happens
  at dispatch. The drawer's borrowed branch appends nothing itself, so a single send yields exactly
  one line. `consumeFreeformText()` now returns the request id and only clears the field/closes the
  drawer/returns `true` when it dispatched; when the client is locked it keeps the typed text and
  the drawer open and returns `false` (no echo, no data loss). This also fixes today's silent
  text-loss bug where a locked free-form send returned success.
- Reconnect replay never re-runs a submit, so no double echo. A later rejection leaves the line (it
  records the player's act), matching the spec.

### D5 — Divider and input-line rendering in the narrative

`appendInput(text)` in goldenlayout.js mirrors `appendNarrative` (scroll-keep + unread marker +
`atNarrativeBottom` handling) but: appends a `.narrative-divider` hairline element **before** the
line unless the log has no prior lines, then appends a `.inp` line whose text is inserted as a single
literal text node (never the markup tokenizer — client-authored text must not enter the allowlist
pipeline). **One input event = one unread increment** even though it creates two DOM nodes
(divider + line), and scroll-keep applies to the single event. CSS adds `.narrative-divider` (1px
`--elm-border-dim` hairline with margins); `.inp` uses the mono face with a subtle left accent.

**Why a dedicated divider element rather than a border on `.inp`?** The spec and browser tests can
assert the divider exists as its own element between server output and each input line; a border on
the line is CSS-only and harder to verify.

## Risks / Trade-offs

- **Catalog mirrors command grammar and could drift from real command spellings** → Node tests pin
  every mapping against `commands/*.py` in the same change; actions without a typed equivalent use
  the server label so the catalog never teaches a false command.
- **Display descriptors could go stale across menu rebuilds** → descriptors are built from the same
  validated panel snapshot that produced the item, at the same time; they are bounded strings, not
  references.
- **Echo timing vs rejection**: an echoed line for an action that later rejects could look like a
  success → mitigated by the spec (the line records the act) and by the server's stable rejection
  message directly below it.
- **Locked free-form now keeps text instead of closing**: behavior change vs today, but strictly
  better (no silent text loss) and required by the no-echo-on-locked rule; covered by a browser
  test.
- **`data-open` attribute toggling must not fight the unread/scroll logic** → `appendInput` reuses
  `appendNarrative`'s exact scroll bookkeeping, only swapping the line-builder, and counts one
  unread event per input.
- **Browser tests currently assume an always-visible drawer** → `test_browser_shell.py` asserts
  `#inputfield` visibility and several tests click the field directly; those must switch to the
  entry button and assert the wrapper hidden-by-default. Task list enumerates every affected file.

## Migration Plan

No released users; no data migration. Rollback is a client-only revert of the JS/CSS changes; the
catalog module is additive and `commandLine` returning `null` degrades to today's behavior. The
`open-drawer` → `toggle-drawer` rename is internal to the router/UI-consumer pair plus its Node
test; archived change evidence is not modified.

## Open Questions

- Whether the dock guidance line ("`/` to open the command input") should be reworded to mention the
  toggle — decided: keep the guidance text as-is for now (it remains true when closed) and revisit
  only if player confusion surfaces.
- Whether `combat.flee`'s fallback line should read `逃跑` or the button label — resolved in the
  catalog with a pinned Node test.