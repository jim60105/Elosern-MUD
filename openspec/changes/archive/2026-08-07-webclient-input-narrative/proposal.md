## Why

The browser command surface is the only way to issue free-form and advanced commands, yet a player
reading the narrative later cannot tell which action produced which result: typed commands and
button-triggered `ui_action` mutations never appear in the log, so the story reads as a series of
unexplained state changes. In addition, the bottom command drawer is always open and `/` only opens
it — never closes it — giving the drawer more screen presence than a pause-for-input surface needs.

## What Changes

- `/` becomes a **toggle**: closed → opens and focuses the `.inputfield`; open (with focus outside
  any editable control) → closes and restores action-dock focus. A `/` pressed while an editable
  control is focused stays a literal `/` in the text and never closes the drawer, so commands or
  text that legitimately contain a slash remain typeable.
- The command drawer **defaults to closed**: only an actionable entry button (a real `<button>`
  with an accessible name, e.g. `指令輸入（/）`, and `aria-expanded`) is visible until opened. The
  drawer opens on `/`, on clicking the entry button, or when a dock borrows it; the open drawer
  keeps today's exact send/focus semantics.
- **Player input is echoed into the narrative log** so the play flow reads completely:
  - Every ordinary text send from the drawer appends the raw typed command as an input line.
  - Every dispatched button/action submission (`explore.move`, `combat.cast`, `shop.buy`,
    `explore.talk_freeform`, …) appends exactly one matching command line at dispatch time, so a
    player can learn the command vocabulary by playing with buttons.
  - The command line shows the canonical typed command where the server exposes one (`talk <NPC>
    <話題>`, `cast <技能>[=<目標>]`, `engage <目標>`, `wait <時段>`, `buy <物品> <數量>`, …);
    for actions without a typed equivalent (`combat.flee`, exit traversal) it shows the
    server-authored action label, never a guessed command.
  - Echoed lines are ordinary narrative entries (scroll + unread-marker behavior), rendered as
    literal text, never submitted, never replayed.
- A **visual divider** separates the last system/server message from each player input line, so the
  two never visually merge while re-reading the log.
- **Locked submissions never echo**: when the action client is offline, in-flight, or not yet
  initialized, no mutation dispatches and no line is appended; a borrowed free-form dialogue keeps
  its typed text in the field instead of silently clearing it.

## Capabilities

### New Capabilities
- `webclient-input-narrative`: echo of typed commands and button-triggered actions into the
  narrative log, the display-only command-line catalog, and the divider between server lines and
  each player input line.

### Modified Capabilities
- `webclient-desktop-shell`: `/` becomes a drawer toggle that never fires while an editable control
  is focused; the command drawer defaults to closed behind an actionable entry button; the
  narrative text-surface requirement gains client input lines and a divider; the borrowed free-form
  send closes the drawer only when its action actually dispatches.

## Impact

- **Browser plugins (JS):** `plugins/elosern_ui.js` routing gate (toggle + editable-safe `/`),
  `plugins/goldenlayout.js` (narrative input append, divider, drawer default-closed entry button,
  open/close hooks, single echo on ordinary send), `plugins/elosern_actions.js` (optional echo on
  `submit` gated on a returned request id), and every submit call site that passes a display
  descriptor: `exploration_dock.js` (menu items, rest form, free-form), `combat_dock.js`/
  `elosern_ui.js` cast paths (incl. AREA confirm), `services_dock.js` (buy/sell quantity),
  `creation_dock.js` (preset/custom/activate/reset), and `goldenlayout.js` local-map move.
- **New browser module:** `web/static/webclient/js/elosern/command_echo.js` — a DOM-independent,
  presentation-only catalog resolving a display command line from `(actionId, payload, display)`
  where `display` is a bounded descriptor of server-authored labels attached by the menu builders.
- **Menu model builders:** `exploration_menu.js`, `combat_menu.js` attach `commandDisplay`
  descriptors (exit/NPC/skill/keyword/target labels) to items at build time from the validated
  panel data they already hold.
- **Keyboard router:** `/` event renamed `open-drawer` → `toggle-drawer` (semantic match for the
  new behavior); router stays DOM-independent and never knows drawer state. Runtime consumers are
  the router, `elosern_ui.js`, and the router Node test; archived change evidence is untouched.
- **Styling:** `web/static/webclient/css/elosern.css` closed-drawer rule, entry-button rule, and
  `.narrative-divider` rule.
- **Tests:** Node unit tests for the catalog and updated keyboard-router test; browser tests for
  drawer default-close, `/` toggle and editable-safe slash, typed-command echo, button-action echo,
  free-form single echo, locked/no-echo paths, and the divider. No Python/server, protocol,
  presenter, or persistence changes — the echo is pure client presentation. **No API or dependency
  changes.**
- No backward compatibility or migration is needed (project has no released users); no schema
  change.

## Out of Scope

- Server-authored/panel `command` fields (the catalog stays client-side and presentation-only).
- Explicit training/teaching UI for commands; the log line itself is the teaching.
- Turning any echoed line back into an executable command (a loaded command line is display-only).
- Mobile layout changes.