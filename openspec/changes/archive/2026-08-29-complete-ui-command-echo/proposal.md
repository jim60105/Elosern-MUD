# Proposal: complete-ui-command-echo

## Why

The narrative log is the player's tutorial: every button-triggered action should
print the equivalent typed command so the player can learn to type it. The
display-only command-line catalog (`webclient-input-narrative`) already
guarantees this, but the guarantee has holes — the whole inventory surface
(`inventory.use`, `inventory.toggle_equip`) has no resolver at all, and several
dispatch paths (combat menu rows, the services shop rows and quantity form, the
shop drawer, the minimap, generic dock intents) drop the server-authored display
descriptor, so the catalog falls to `null` and those clicks echo nothing. The
result: a player who equips a potion or buys from the shop drawer learns no
typed command, violating the design intent that the UI teaches the keyboard.

## What Changes

- Add catalog resolvers for the inventory surface: `inventory.use` echoes
  `use <item_key>` and `inventory.toggle_equip` echoes `equip <item_key>`
  (both are the typed commands' aliases in `commands/items.py`, which accept
  `item_key` literally, so every echoed line is byte-replayable).
- Close every descriptor-dropping dispatch path so a deliberate mutation from
  any surface (combat menu rows with their chosen magnitude, services shop
  rows, quantity form, shop drawer, minimap move, generic dock intents,
  creation rows including the activate/reset confirmations) resolves exactly
  one echo line, built only from labels already held by the client (payload
  values, panel display names, exit labels, or the verbatim-pinned bounded
  control labels of the no-typed-command actions) — never invented
  names. Echoed lines are the canonical typed command wherever one exists (so
  the player can replay them at the keyboard); the project's three
  already-pinned no-typed-command actions (`explore.move`, `combat.flee`,
  `creation.reset`) keep echoing their bounded action label as a documented
  action description.
- `options.dismiss` is classified as a presentation control (like closing a
  drawer): it stays silent by design, and is the only mutation action allowed
  to have no echoed line.
- Add a Node-gate coverage invariant: every mutation action id registered in
  `web/webclient/actions/registry.py` either resolves to a non-empty catalog
  line for a pinned fixture or appears in the documented silent presentation-
  control list — a future action can no longer land silently uncovered.
- No server, protocol, or typed-command changes: no command keys/aliases change
  (`docs/game/commands.md` and `command-reference.md` stay unchanged), no
  dispatch envelope changes, and no game state is touched. This is client
  presentation only.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `inventory-item-actions`: "Inventory mutations use exact allowlisted UI
    actions" — extended: the `item_key` is whitespace-free (the typed
    `use`/`equip` parsers take the first token; the echoed line stays
    byte-replayable).
- `webclient-input-narrative`:
  - "The command-line catalog resolves a display line deterministically" —
    extended: every registered mutation action is supported (non-null), with
    `options.dismiss` as the one documented presentation-control exception; the
    two inventory actions resolve to their typed `use`/`equip` commands keyed
    by the payload's `item_key`.
  - "Every deliberate mutation echo appears exactly once at dispatch" —
    extended: the echo fires on activation from every surface, which requires
    each dispatch path to forward the server-authored display descriptor to the
    catalog (a mutation activation from any surface must produce its line, not
    silently resolve to `null`).
  - New requirement "Catalog coverage is pinned against the action registry":
    the Node suite enumerates every registered mutation action id and asserts
    non-null resolution or explicit silent-control membership; a Python test
    pins the registry's id set to the same list. This pin is a future-action
    tripwire only — per-surface behavior is proven by a table-driven store
    test in which every dispatch surface is a row (echo expected, or silence
    explicitly expected and audited).

## Impact

- Client catalog: `web/static/webclient/js/elosern/command_echo.js` (the single
  UMD source; the Vue app imports it via the `web/webclient-app/lib/` wrapper).
- Client dispatch paths: `web/webclient-app/stores/elosern.js` — forward the
  dropped `commandDisplay` at the combat / services / creation-confirm submits,
  replay the label on the quantity-form Enter submit, and fill missing
  descriptor fields for component intents from the committed panels at the
  single dispatch entry (the freeform-talk precedent generalized);
  `web/static/webclient/js/elosern/creation_menu.js` (confirmation items carry
  their descriptor), and `AppClient.vue`'s minimap move handler derives the
  echo label via the new `LocalMap.exitLabelFor` unique-edge rule. The
  inventory action validators (`web/webclient/actions/service_actions.py`)
  reject whitespace-bearing `item_key`s. Shared coverage manifest:
  `web/static/webclient/js/tests/command_echo_coverage_manifest.json`.
- Tests: Node gate `web/static/webclient/js/tests/command_echo.test.js`
  (inventory resolvers + registry-coverage invariant), a table-driven Vitest
  store/component suite covering every dispatch surface, a Python registry
  pin test, and one added backpack-echo method in the existing browser class
  `web/tests/browser/test_browser_inventory_actions.py` (rest of the browser
  suite CI-owned).
- No changes to `commands/`, `world/`, the OOB protocol, or player command docs.
