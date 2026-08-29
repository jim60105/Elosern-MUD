# Design: complete-ui-command-echo

## Context

The `webclient-input-narrative` capability already defines the contract: every
button-triggered `ui_action` mutation resolves to exactly one display command
line via the pure catalog `commandLine(actionId, payload, display)`
(`web/static/webclient/js/elosern/command_echo.js`), and the store's single
submit path (`dispatchAction` in `web/webclient-app/stores/elosern.js`) appends
that line as literal narrative text at dispatch. The echo hook itself is
centralized and correct — the gaps are:

| Dispatch site | Action(s) | Today | Root cause |
| --- | --- | --- | --- |
| `InventoryPanel.vue` row action → `AppClient.onInventoryItemAction` | `inventory.use`, `inventory.toggle_equip` | no line | no resolver in the catalog |
| `AppClient.onShopBuy` / `onShopSell` (shop drawer) | `shop.buy` / `shop.sell` | no line | `ShopPanel` intent carries only `{action_id, payload}`; resolver needs `display.itemLabel` |
| `handleServiceItem` action rows + quantity-form submit | `shop.buy` / `shop.sell` | no line | site does not forward `item.commandDisplay` (built by `service_menu.js`); `openQuantityForm` drops the label |
| Combat rows (AREA confirm, keyboard target confirm, OOB rows) | `combat.cast`, `combat.flee` | no line for cast/flee | sites do not forward the `commandDisplay` that `combat_menu.js` attaches, and the target/AREA rows' descriptors carry no `scaleLabel` |
| Generic router-submit intent (`actionIntentForItem`) | any | null when a label is needed | the intent shape strips `commandDisplay` |
| `AppClient.onMapMove` | `explore.move` | no line | no `exitLabel` descriptor from the minimap |
| Creation preset/activate/reset rows and confirmation items | `creation.activate`, `creation.reset` | `character create` even on preset activate; no line for reset | `creation_menu.js` `confirmMenu()` stores `itemLabel` on the menu, not on the confirm action item, and `handleCreationItem` forwards no display |
| `options.dismiss` | `options.dismiss` | no line | no resolver (intended silence today, but undeclared) |

Constraints: the echo is presentation-only (never touches the envelope, the
transport, or state); the catalog must never invent a name it was not given;
all labels are server-authored (menu builders and panels already carry them).
The typed inventory commands (`使用`/`use`, `裝備`/`equip` in
`commands/items.py`) parse a literal `item_key` — first whitespace-delimited
token — and accept nothing else.

## Goals / Non-Goals

**Goals:**

- Every deliberate UI mutation activation from every surface appends exactly
  one echo line, except one declared silent presentation control
  (`options.dismiss`) and the audited no-label fallbacks below.
- Echo lines teach the keyboard in the project's established two-form policy
  (D7): the canonical typed command where one exists, otherwise the bounded
  server-authored action label as a documented action description.
- The catalog's coverage of the action registry is a pinned, CI-enforced
  invariant, and the catalog + registry pin are complemented by a per-surface
  behavioral test table (D6): the registry pin is a future-action tripwire,
  never the sole behavioral proof.

**Non-Goals:**

- No new typed commands, aliases, or command-doc changes (docs are unchanged;
  `tests/test_command_docs.py` is untouched). In particular this change does
  NOT add typed `move`/`flee` commands; their label echoes remain the pinned,
  documented exception (D7).
- No protocol, dispatcher, payload-validator, or server menu changes.
- No echo for navigation/back/submenu opens or quick-word chips (unchanged).
- No replay/autocomplete from echoed lines — the line stays literal text.

## Decisions

### D1: Inventory resolvers are payload-only and echo replayable keys

`inventory.use` → `use <item_key>`; `inventory.toggle_equip` →
`equip <item_key>`. Both English spellings are registered aliases in
`commands/items.py`, and the typed parsers take the literal `item_key`, so the
echoed line is exactly what the keyboard accepts. The payload's `item_key` is
not a guessed name — it is the command's own argument, matching the pinned
`guild accept <definition_key>` precedent. Because the typed parsers stop at the
first whitespace, the inventory action validators reject whitespace-bearing
`item_key`s at the boundary (review fix 6.1), so an echoed line is always
byte-replayable. Alternative rejected: echoing the
Chinese display name (as `shop.buy` does) — the typed `use`/`equip` commands do
not accept display names, so a display-name echo would teach an untypable
command.

### D2: The equipment toggle echoes `equip` in both directions

There is no typed `unequip`: `裝備`/`equip` is itself the toggle
(`toggle_equipment`). Both equip and unequip clicks echo `equip <item_key>`;
inventing an `unequip` line would print a command that cannot be typed.

### D3: Descriptor sourcing — explicit forwarding plus a central fill in the single dispatch entry

The catalog stays pure. Labels reach it through two complementary channels,
both carrying only server-authored values:

1. **Explicit forwarding (menu-backed surfaces).** Raw menu items already
   carry `commandDisplay`; the sites that today drop it must forward it: the
   generic OOB branch and the AREA/keyboard-target submits in the dock
   activate handler, `handleServiceItem` action rows, and
   `handleCreationItem`'s activate/reset branch (the exploration path at
   `handleExplorationItem` already forwards — this is the existing pattern,
   not a new idea). Combat magnitude: the row descriptors carry no
   `scaleLabel`, so the AREA and keyboard-target submits merge the chosen
   magnitude's label into the forwarded descriptor via the existing
   `CombatMenu.scaleLabelFor(skill)` — **only when the chosen scale differs
   from the default `1`** (the function's pinned contract: the default shows
   no 威力 suffix; the payload is untouched either way). AREA targets: when
   the AREA payload carries explicit `target_ids` (no approved shorthand),
   the submit attaches `targetLabels` — the committed participant
   `display_name`s in payload order — and the catalog's `combat.cast`
   resolver composes them (D3b). Quantity form: `openQuantityForm` captures
   `itemLabel` from the item's `commandDisplay` at open time and replays it
   on the Enter submit. Creation confirmations: `creation_menu.js`
   `confirmMenu()` keeps `itemLabel` on the menu object only; attach
   `commandDisplay` to the confirmation action item itself
   (`creation.activate` → `{ presetKey }` from `activateConfirm`;
   `creation.reset` → the `RESET_DISPLAY` constant exported by
   `creation_menu.js`, the bounded client-owned action label of D7).
2. **Central fill (intent surfaces).** Component intents
   (`ShopPanel` buy/sell, `ChoiceCardRow`/`ChoicePointBlock` suggestion cards,
   quest/drawer intents, `actionIntentForItem` results) carry only
   `{action_id, payload}`. Instead of touching every component, the store's
   single dispatch entry fills *missing* descriptor fields from committed
   store state before calling the catalog — the exact generalization of what
   the freeform-talk branch already does (reading the NPC's server-authored
   display name from the committed `exploration` panel). The fill is a pure
   helper keyed by `actionId` over committed reducer state (panels) plus the
   committed creation state: services shop row `display_name` by `item_key`
   mapped onto the catalog's `itemLabel` field; interact targets'
   `display_name` by `npc_id`/`identity` (exploration panel); combat skill
   `label` by `skill_key`, participant `display_name`s by payload identity
   order onto `targetLabels`, and single `targetLabel` (combat panel);
   `explore.move` label = the **uniquely** matching traversable edge's label
   between `current_node` and the destination node (committed
   `localMapModel.edges`), falling back to the destination node's `label` —
   a non-unique edge match MUST NOT pick one (the edge model carries no
   `exit_ref` and the schema does not forbid parallel edges, so a match
   ambiguity degrades to the node-label fallback, never a guessed exit);
   and `creation.activate`/`creation.reset` read the committed
   `creation.confirmItems[0].commandDisplay`, which covers the
   `CreationOverlay.confirmCurrent` intent (it emits only `{action_id,
   payload:{}}`) with **no Vue component change**. The fill never overwrites
   an explicitly provided field and never derives a label the committed
   state does not carry — genuinely absent → silent (the catalog never
   fabricates; D6 audits the silence).

The Vue component tree is untouched except for one derivation with no store
input: `AppClient.onMapMove` (it holds the clicked node's `destination`, which
the payload does not carry) builds the descriptor via the new pure
`LocalMap.exitLabelFor` unique-edge rule (review fix 6.3). No `commandDisplay`
is plumbed through Vue emits.

**D3b: multi-target AREA echo contract.** `combat.cast` with explicit
`target_ids` echoes the ordered, label-bounded participant names joined by
`、` inside the target position (`cast <skill（威力×n）>=<甲、乙>`); the
approved-shorthand path keeps the shorthand. Both orders and the join are
pinned by Node catalog tests, so the line records exactly what was cast at.

### D4: `options.dismiss` is the one declared silent mutation

Dismissing the suggestion strip is a presentation control (like closing a
drawer): no game action, no typed equivalent, nothing to learn. The catalog
keeps a single explicit exported `SILENT_PRESENTATION_CONTROLS` list
containing `options.dismiss`, and `commandLine` checks it first and returns
`null` for its members — the declaration and the behavior are the same code
path, not a test-only annotation (the id happens to also have no resolver,
but the silence must not depend on that accident).

### D5: Two-sided coverage pin (Node catalog + Python registry)

- Node gate (`command_echo.test.js`): a pinned literal list of every registered
  mutation action id + fixture descriptors asserts each resolves non-null, and
  each id in the silent list resolves null. Unknown-action `null` behavior is
  unchanged.
- Python side (`web/webclient/actions/tests/`): a deterministic test asserts
  `registry.action_ids()` equals the same literal list, so any new registered
  action fails CI until the catalog (or the silent list) is updated. Rejected
  alternatives: parsing the JS file from Python (brittle) or importing Node
  from the Python suite (toolchain coupling).
- Both pins read the single id source
  `web/static/webclient/js/tests/command_echo_coverage_manifest.json`
  (review fix 6.2), so the Node fixture, the Vitest table, the catalog silent
  list, and the Python registry pin cannot drift into three lists.
- Both pins only prove catalog coverage; per-surface behavior is proven by
  D6's table, not by these pins.

### D6: A per-surface echo table is the behavioral proof

One table-driven Vitest store/component suite asserts, row by row, the exact
echo line produced by a real activation of every dispatch surface: backpack
use/toggle, shop drawer buy/sell, services rows, quantity-form Enter, combat
cast (single-target and AREA, with and without a non-default scale), flee,
forfeit, minimap move (edge label, node-label fallback, and no-label silence),
exploration rows, freeform talk, guild/quest rows, creation preset/activate/
reset confirmations, and the `options.dismiss` silence. Each row asserts
exactly one line, envelope byte-identity, and literal-text rendering. Any
silence in the table must be an explicit expected-silence row — a surface can
therefore never go quietly silent, which bounds D3's no-label escape hatch.

### D7: Typability policy — two documented forms, three audited exceptions

The echoed line is (a) the canonical typed command where one exists — the
overwhelming majority, including the new inventory `use`/`equip` lines — or
(b) a bounded action label of the activating control where the project has
deliberately chosen no typed command: `explore.move` (the server-authored
exit label from the committed panel), `combat.flee`, and `creation.reset`
(the latter two use bounded client-owned control constants — the flee row's
label is pre-existing in `combat_menu.js`, and `creation_menu.js` gains the
matching `RESET_DISPLAY` — pinned by the Node suite because the creation
panel carries no reset label to read). Calling those two "server-authored"
would be false; the spec wording says what it means: a bounded control label,
server- or client-authored depending on the action, always verbatim-pinned.
Those three are inherited or mirror-existing exceptions; this change adds no
other non-typed-form actions. The user-facing "learn by imitation" goal is
met by form (a); form (b) rows still teach what the button did, as one line
in the log.

### D8: One line per deliberate activation, unchanged semantics

Confirm flows (item-use confirm, quest abandon, creation reset/activate
confirm) dispatch once, so they echo once. Keyboard and pointer activation keep
their exactly-once semantics; this change adds lines only where none appears
today and never a second line where one already appears.

## Risks / Trade-offs

- [Descriptor drift: a site forwards a stale label after a panel refresh] →
  descriptors are read from the raw item/committed panel at activation time
  (open-time capture only for the quantity form and creation confirm items,
  both already discarded/rebuilt on panel replacement).
- [Echo line teaches `use <item_key>` (ASCII keys) while narrative prose is
  Chinese] → accepted: replayability wins over prettiness for key-taking
  commands, matching `guild accept`; the item's Chinese name appears in the
  server's result line anyway.
- [The central fill reads committed panels the envelope never carries] → the
  fill output feeds only the catalog call; the envelope builder is untouched
  (a store test asserts the `ui_action` envelope stays byte-identical with
  and without fills), and every filled value is a verbatim committed panel
  field, never a composition across fields (the catalog composes lines).
- [A new action's fill mapping is forgotten] → the fill helper stays
  action-keyed and the D5 pin fails CI for any registered action that neither
  resolves from a fixture nor is declared silent.
- [Two pinned lists (Node test, Python test) can diverge] → the Python test
  fails with a message naming the catalog as the file to update; CI keeps both
  gates on the same branch.
- [Choicepoint cards without any server-authored label still echo nothing] →
  bounded by D6: such a surface must appear as an explicit expected-silence
  row, reviewed like any other; it cannot hide an unlisted silent path.

## Migration Plan

Client-only change; no data or protocol migration. Ship catalog + store +
component changes together with the Node/Vitest tests; rollback is a revert.

## Open Questions

_None_ — surface-level label sources are enumerated above; implementers
follow the D3 table site by site and the D6 test table surface by surface.
