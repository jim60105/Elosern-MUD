# Tasks: complete-ui-command-echo

## 1. Command catalog and Node gate

- [x] 1.1 In `web/static/webclient/js/elosern/command_echo.js`, add the
      `inventory.use` → `use <item_key>` and `inventory.toggle_equip` →
      `equip <item_key>` resolvers built from the payload's literal `item_key`
      (D1/D2: replayable aliases of `使用`/`裝備`; both toggle directions echo
      `equip`), add `display.targetLabels` composition to `combat.cast` for
      explicit multi-target payloads (D3b: bounded labels joined with `、`,
      payload-order), and export an explicit
      `SILENT_PRESENTATION_CONTROLS` list containing `options.dismiss` that
      `commandLine` checks first and returns `null` for (D4 — declaration and
      behavior are the same code path). Keep the three pinned
      no-typed-command actions (`explore.move`, `combat.flee`,
      `creation.reset`) documented as the form-(b) exceptions (D7).
- [x] 1.2 Extend `web/static/webclient/js/tests/command_echo.test.js`: pin the
      two inventory resolvers byte-for-byte, the both-directions `equip` echo,
      `null` on missing/empty/non-string `item_key`, and `options.dismiss` →
      `null`.
- [x] 1.3 Add the Node coverage invariant test (D5): a pinned literal list of
      every registered mutation action id (`registry.py`: the 26 ids) plus
      fixture descriptors; each resolves to a non-empty bounded line or appears
      on the exported silent list; unknown ids stay `null`. Verify with
      `node --test web/static/webclient/js/tests/*.test.js`.

## 2. Descriptor channels: forwarding, form replay, confirm items, central fill (D3)

- [x] 2.1 Dock activate handler (`stores/elosern.js`): the generic OOB branch
      (combat.flee et al.) and the AREA-confirm and keyboard-target-confirm
      `combat.cast` submits forward the raw item's `commandDisplay`; the
      AREA/keyboard submits merge the chosen magnitude label into the
      forwarded descriptor ONLY when the chosen scale differs from the
      default `1` (`CombatMenu.scaleLabelFor(skill)`; the default shows no
      威力 suffix per its pinned contract) and attach `targetLabels` — the
      committed participant `display_name`s in payload order — when the AREA
      payload carries explicit `target_ids` (D3b). Payload byte-identity is
      unchanged.
- [x] 2.2 `handleServiceItem` action rows and `handleCreationItem`'s
      activate/reset branch: forward `item.commandDisplay || null`.
- [x] 2.3 Quantity form: `openQuantityForm` captures `itemLabel` from the
      opening item's `commandDisplay`; the Enter submit passes
      `{ itemLabel: q.itemLabel }` as the descriptor.
- [x] 2.4 `creation_menu.js`: `confirmMenu()` attaches `commandDisplay` to the
      confirm action item (`creation.activate` → `{ presetKey }` via
      `activateConfirm`; the store's reset confirm passes the
      `RESET_DISPLAY`-exported bounded client label, D7). The
      `CreationOverlay.confirmCurrent` intent (which emits only
      `{action_id, payload:{}}`) is served by the central fill reading the
      committed `creation.confirmItems[0].commandDisplay` — no Vue component
      change.
- [x] 2.5 Central fill in the store's single dispatch entry: a pure,
      action-keyed helper fills MISSING descriptor fields from committed
      reducer state plus committed creation state — services shop
      `display_name` by `item_key` mapped onto the catalog's `itemLabel`
      field, interact `display_name` by `npc_id`/`identity` (exploration
      panel), combat skill `label` by `skill_key`, single `targetLabel` and
      payload-ordered `targetLabels` from combat participants, `explore.move`
      label = the UNIQUELY matching traversable edge label between
      `current_node` and the destination node (parallel-edge ambiguity
      degrades to the destination node `label`, never an arbitrary edge), and
      `creation.activate`/`creation.reset` from
      `creation.confirmItems[0].commandDisplay`. It never overwrites an
      explicitly provided field, never composes across fields, and never
      sends a composed line; genuinely absent fields stay absent (catalog
      silence, audited by the 3.1 table). `dispatchAction` uses the filled
      descriptor only for the catalog call — the envelope is untouched.
- [x] 2.6 Silence audit wiring: `options.dismiss` dispatches resolve null via
      the catalog's silent list (no descriptor, no fill).

## 3. Per-surface behavioral proof (Vitest, D6)

- [x] 3.1 Add a table-driven store/component suite under
      `web/webclient-app/tests/store/` with one row per dispatch surface:
      backpack use/toggle, shop drawer buy/sell (central fill, asserting the
      `display_name`→`itemLabel` mapping), services rows, quantity-form
      Enter, combat cast single-target, AREA with an approved shorthand, AREA
      with explicit multi-target ids (every name in payload order), cast
      with a non-default magnitude (威力 suffix present) and with the default
      (suffix absent), flee, forfeit, minimap move (unique edge label,
      parallel-edge ambiguity falling back to the node label, node-label
      fallback, and no-label expected silence), exploration rows, freeform
      talk, guild/quest rows, creation preset / activate-confirm (dock item
      and overlay intent) / reset-confirm, suggestion-card intents, and the
      `options.dismiss` expected silence. Every echo row asserts the exact
      line, exactly-once append, `ui_action` envelope byte-identity (filled
      and unfilled), and literal-text rendering; every silence is an explicit
      expected-silence row. A final row-invariant test asserts the table's
      exercised action-id set covers every registered mutation id except the
      silent presentation controls.
- [x] 3.2 Pin silence rules: blocked states (offline, locked, in-flight)
      never echo; navigation/chip behavior unchanged; a fill never overrides
      an explicit descriptor.
- [x] 3.3 Run `npm test` and keep the suite green.

## 4. Registry coverage pin (Python)

- [x] 4.1 Add a deterministic unittest to `web/webclient/actions/tests/`
      asserting the production registry's `action_ids()` equals the same
      literal mutation set pinned by the Node suite, with a failure message
      naming `command_echo.js` as the file to update; annotate with
      `covers_requirement("webclient-input-narrative::catalog-coverage-is-pinned-against-the-action-registry")`
      (the canonical id from `tools.spec_traceability list` once the delta is
      in the main spec).
- [x] 4.2 Verify with the focused label:
      `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.actions`.

## 5. Browser trace and consistency verification

- [x] 5.1 Add one backpack-echo acceptance journey to the existing browser
      inventory-actions class in
      `web/tests/browser/test_browser_inventory_actions.py` (equip/use from
      the drawer echo exactly one line; envelope unchanged), annotated
      `covers_requirement("webclient-input-narrative::every-deliberate-mutation-echo-appears-exactly-once-at-dispatch")`;
      run that single class locally within budget.
- [x] 5.2 Confirm no player-command surface changed (keys/aliases/context):
      `docs/game/commands.md` and `command-reference.md` stay untouched and
      `tests/test_command_docs.py` stays green.
- [x] 5.3 Run the Node gate, `npm test`, and `uv run --locked python -m
      tools.spec_traceability check`; keep the remaining existing browser
      narrative tests unmodified (full browser suite stays CI-owned).
- [x] 5.4 Re-read proposal/design/specs/tasks for mutual consistency and run
      `openspec validate complete-ui-command-echo --strict`.

## 6. Post-implementation review fixes (rubber-duck round 2)

- [x] 6.1 Whitespace-free `item_key` invariant: the inventory action
      validators reject whitespace-bearing keys (the typed `use`/`equip`
      commands parse the first token, so the echoed line stays
      byte-replayable), with validator tests and a MODIFIED
      `inventory-item-actions` requirement delta (synced into the main spec).
- [x] 6.2 Single coverage manifest:
      `web/static/webclient/js/tests/command_echo_coverage_manifest.json` is
      now the one id source pinned by the Node catalog gate, the Vitest
      per-surface table, and the Python registry pin (no three-way drift).
- [x] 6.3 Real minimap integration row:
      `web/webclient-app/tests/app_client_map_move.test.js` clicks the
      lattice node through the mounted AppClient (unique edge label echo;
      parallel-edge ambiguity echoes the destination node label).
- [x] 6.4 Declared absent-array semantics: an empty descriptor array is
      documented and pinned as fillable (never a silent wrong-echo).
