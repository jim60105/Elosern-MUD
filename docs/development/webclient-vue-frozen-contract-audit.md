# WebClient Phase-0 Frozen Contract Audit

**Status:** FROZEN by `webclient-vue-00-audit-and-design-docs` (roadmap change **A1**).
**Governing roadmap:** `docs/superpowers/specs/2026-08-19-webclient-vue-migration-roadmap-design.md`.
**Binding consumers:**

- `webclient-vue-08-wire-bridge-contracts` (**C2**) is the **binding consumer** of the frozen
  façade-bridge surface (§1) and applies the delta entries that name it (§3).
- `webclient-vue-10-wire-views-browser` (**C4**) applies the flip-time delta entries that name it
  (§3) and executes the DOM remap decisions (§2.3).

This document is the Phase-0 contract audit of the Phase-0 design (A1 design D1/D2): it enumerates
every implementation-bound client contract across `openspec/specs/webclient-*/spec.md` (the 17
`webclient-*` main capabilities) and the managed Playwright suite `web/tests/browser/`, classifies
each contract as preserve-via-bridge or delta, and freezes (a) the exact `window.Elosern.*`
façade-bridge surface the browser bridge (C2) must expose and (b) the complete `MODIFIED`/`RENAMED`
delta list. The deltas are **not applied by A1**; each entry names its applying change.

Enumeration method (A1 design D2): grep-driven. Every occurrence of `window.Elosern.`, the
`onKeydown` plugin path, `getElementById` / `#`-id targets in the Playwright suite and the keyboard
router, and the layout-persistence keys was captured, then classified; classification sites in the
client source (`web/static/webclient/js/`) and in `web/templates/webclient/base.html` were read to
pin definition evidence. The façade member lists in §1 were derived mechanically from the UMD
modules themselves (Node `Object.keys` on `protocol.js` and `keyboard_router.js`), not transcribed.

Every implementation-bound identifier in this document lands in exactly one bucket (§2). No
identifier is classified twice, and no bucket entry is left without a rationale.

---

## 1. Frozen façade-bridge surface

The browser bridge (C2) SHALL expose exactly these four façades at `window.Elosern.*` with exactly
these members. `Protocol` and `KeyboardRouter` are the preserved UMD modules themselves, attached
byte-identical (the bridge re-exposes the import; it does not re-implement). `narrativeInput` and
`actions` are the single-owner façades: the store's one narrative/choice-point append path and the
one action-dispatch entry, respectively.

```json
{
  "frozen-facade-surface": {
    "Protocol": {
      "kind": "umd-module",
      "defined_at": "web/static/webclient/js/elosern/protocol.js",
      "members": [
        "PROTOCOL_VERSION",
        "MAX_SAFE_INTEGER",
        "MAX_CANONICAL_JSON_BYTES",
        "MAX_DEPTH",
        "MAX_FIELDS",
        "MAX_LIST_ITEMS",
        "MAX_STRING_CODE_POINTS",
        "MAX_PANEL_COUNT",
        "MAX_LAYOUT_VERSION",
        "MAX_MESSAGE_CODE_POINTS",
        "EPOCH_LENGTH",
        "MAX_RETIRED_EPOCHS",
        "MAX_ACTOR_NAME",
        "MAX_ACTOR_IDENTITY",
        "MAX_LOCATION_LABEL",
        "MAX_CONDITION_COUNT",
        "MAX_CONDITION_LABEL",
        "MAX_MODIFIER_KEYS",
        "LOCAL_MAP_MAX_NODES",
        "LOCAL_MAP_MAX_EDGES",
        "LOCAL_MAP_MAX_LEGEND",
        "LOCAL_MAP_MAX_STRING",
        "LOCAL_MAP_MAX_TITLE",
        "LOCAL_MAP_MAX_NODE_ID",
        "LOCAL_MAP_MAX_EXIT_REF",
        "LOCAL_MAP_COORD_MIN",
        "LOCAL_MAP_COORD_MAX",
        "LOCAL_MAP_VISIBILITIES",
        "LOCAL_MAP_LAYERS",
        "LOCAL_MAP_ACTION_KINDS",
        "SERVICES_MAX_BOARD_ROWS",
        "SERVICES_MAX_QUEST_ROWS",
        "SERVICES_MAX_STOCK_ROWS",
        "SERVICES_MAX_SELLABLE_ROWS",
        "SERVICES_MAX_INVENTORY_ROWS",
        "SERVICES_MAX_KEY",
        "SERVICES_MAX_DISPLAY_NAME",
        "SERVICES_MAX_SUMMARY",
        "SERVICES_MAX_DETAIL",
        "SERVICES_MAX_DEADLINE_LINE",
        "SERVICES_MAX_RANK_KEY",
        "SERVICES_MAX_HOST_DISPLAY_NAME",
        "SERVICES_MAX_LABEL",
        "SERVICES_MAX_REASON_MESSAGE",
        "SERVICES_MAX_QUANTITY",
        "SERVICES_MIN_QUANTITY",
        "SERVICES_QUEST_STATES",
        "SERVICES_ACTIONS",
        "EXPLORATION_MAX_MOVE_EXITS",
        "EXPLORATION_MAX_LOOK_ENTITIES",
        "EXPLORATION_MAX_LOOK_OBJECTS",
        "EXPLORATION_MAX_INTERACT_TARGETS",
        "EXPLORATION_MAX_AFFORDANCES",
        "EXPLORATION_MAX_SCRIPTED_KEYWORDS",
        "EXPLORATION_MAX_EXIT_REF",
        "EXPLORATION_MAX_NODE_ID",
        "EXPLORATION_MAX_DISPLAY_NAME",
        "EXPLORATION_MAX_KIND",
        "EXPLORATION_MAX_LABEL",
        "EXPLORATION_MAX_KEYWORD_ID",
        "EXPLORATION_MAX_KEYWORD_LABEL",
        "EXPLORATION_MAX_REASON_MESSAGE",
        "EXPLORATION_ACTION_KINDS",
        "EXPLORATION_ACTION_IDS",
        "EXPLORATION_SURFACES",
        "EXPLORATION_ENTITY_KINDS",
        "CONTEXT_ACTIONS_MAX_AFFORDANCES",
        "CONTEXT_ACTIONS_MAX_AFFORDANCE_LABEL",
        "CONTEXT_ACTIONS_MAX_PARAM_KEYS",
        "CONTEXT_ACTIONS_MAX_PARAM_STRING",
        "CONTEXT_ACTIONS_ACTION_CODES",
        "CONTEXT_ACTIONS_SURFACES",
        "CHARACTER_MAX_TRAIT_ROWS",
        "CHARACTER_MAX_ACTIVE_ROWS",
        "CHARACTER_MAX_PASSIVE_ROWS",
        "CHARACTER_MAX_CATEGORY_GROUPS",
        "CHARACTER_MAX_EQUIPMENT_ROWS",
        "CHARACTER_MAX_DISPLAYED_ROWS",
        "CHARACTER_MAX_KEY",
        "CHARACTER_MAX_LABEL",
        "CHARACTER_MAX_DESCRIPTION",
        "CHARACTER_MAX_SLOT",
        "CHARACTER_MAX_BACKGROUND",
        "CREATION_MAX_PRESETS",
        "CREATION_MAX_RACES",
        "CREATION_MAX_SUBRACES",
        "CREATION_MAX_PROFILES",
        "CREATION_MIN_NAME_LENGTH",
        "CREATION_MAX_NAME_LENGTH",
        "CREATION_AGE_MINIMUM",
        "CREATION_AGE_MAXIMUM",
        "CREATION_APPARENT_AGE_MINIMUM",
        "CREATION_APPARENT_AGE_MAXIMUM",
        "CREATION_MAX_PRESET_KEY",
        "CREATION_MAX_DISPLAY_NAME",
        "CREATION_MAX_RACE_KEY",
        "CREATION_MAX_DESCRIPTION",
        "CREATION_MAX_EMPHASIS",
        "CREATION_MAX_BACKGROUND",
        "CREATION_MAX_PERSONA_BACKGROUND",
        "CREATION_MAX_SUBRACE_KEY",
        "CREATION_MAX_SPECIALTY",
        "CREATION_MAX_LABEL",
        "CREATION_MAX_EXPLANATION",
        "CREATION_AXES",
        "MODES",
        "OUTCOMES",
        "COMBAT_MODES",
        "PROTOCOL_ERROR_CODES",
        "PANEL_ALLOWLIST",
        "checkEnvelope",
        "checkGlobalSafety",
        "jsonByteSize",
        "canonicalJson",
        "validateEpoch",
        "validateServerTime",
        "validateSnapshot",
        "validateUpdate",
        "validateActionResult",
        "validateProtocolError",
        "validateStatusPanel",
        "validateArtPanel",
        "validateExplorationPanel",
        "validateCharacterPanel",
        "validateContextActionsPanel",
        "validateSuggestions",
        "validateSuggestionCard",
        "OPTIONS_STATUSES",
        "OPTIONS_CARD_KINDS",
        "MAX_OPTION_CARDS",
        "MAX_OPTION_LABEL",
        "MAX_OPTION_HINT",
        "MAX_OPTION_PARAMS",
        "OPTIONS_FREEFORM_ACTION_CODE",
        "OPTIONS_MAX_PARAM_STRING",
        "validateLocalMapPanel",
        "validateServicesPanel",
        "validateCreationPanel",
        "validatePanel",
        "syncEnvelope",
        "createRetiredEpochSet",
        "createStore"
      ],
      "create_store_members": [
        "getState",
        "subscribe",
        "setConnected",
        "beginTransport",
        "receive"
      ],
      "envelope_names": [
        "ui_sync",
        "ui_action",
        "ui_snapshot",
        "ui_update",
        "ui_action_result",
        "ui_protocol_error",
        "connection_open"
      ]
    },
    "KeyboardRouter": {
      "kind": "umd-module",
      "defined_at": "web/static/webclient/js/elosern/keyboard_router.js",
      "members": [
        "ARROW_UP",
        "ARROW_DOWN",
        "ARROW_LEFT",
        "ARROW_RIGHT",
        "ENTER",
        "ESCAPE",
        "SPACE",
        "SLASH",
        "menuItem",
        "createRouter"
      ],
      "router_instance_members": [
        "pushMenu",
        "replaceMenu",
        "popMenu",
        "reset",
        "depth",
        "currentItem",
        "currentMenu",
        "setMutationInFlight",
        "isMutationInFlight",
        "setAwaitingRevision",
        "isAwaitingRevision",
        "clearRepeatGuard",
        "press",
        "handle",
        "focus",
        "focusItemByKey",
        "confirm",
        "trail",
        "rootMenu"
      ]
    },
    "narrativeInput": {
      "kind": "object",
      "defined_at": "web/static/webclient/js/plugins/goldenlayout.js",
      "members": [
        "appendInput",
        "mountChoicePoint",
        "replaceChoicePoint",
        "unmountChoicePoint"
      ]
    },
    "actions": {
      "kind": "object",
      "defined_at": "web/static/webclient/js/plugins/elosern_actions.js (createBrowserActions) attached by plugins/elosern_ui.js",
      "members": [
        "client",
        "sync",
        "submit",
        "handleActionResult",
        "handlePresentation",
        "handleReconnect",
        "handleTransportReset",
        "requestResync",
        "resetResyncEpisode"
      ],
      "client_members": [
        "sync",
        "submit",
        "onActionResult",
        "onPresentationAccepted",
        "onReconnect",
        "onDetached",
        "onTransportReset",
        "isLocked",
        "isInFlight",
        "inFlightRequestId",
        "uncertain",
        "lastResult"
      ]
    }
  }
}
```

Façade notes (behavioral contract; the bridge must preserve behavior, not just names):

- **`Protocol`** — the transport-generation reducer and its validator table. `createStore`
  returns the store surface `create_store_members` (atomic snapshot adoption, epoch/revision
  gating, retired-epoch set, one-notification-per-commit semantics — the behavior fixed by the
  `webclient-oob-protocol` and `webclient-desktop-shell` state-reduction requirements). The
  `envelope_names` list is the exact versioned OOB message set (`PROTOCOL_VERSION = 1`).
- **`KeyboardRouter`** — the menu-stack focus router. `createRouter(options)` returns a router
  with exactly `router_instance_members`; `handle(key, repeat)` is the single key-entry adapter.
  Claim semantics: `press`/`handle` returns `true` exactly when the router consumed the key
  (arrows/Enter/Escape/Space/`/`), and repeated Enter/Space are suppressed; unconsumed keys
  return `false` and fall through. `setMutationInFlight`/`isAwaitingRevision` are the
  submission gates. The production `window.Elosern.keyboard` instance is an *adjacent*
  harness-facing global, not part of the frozen module surface (§2.1).
- **`narrativeInput`** — the single narrative append path (player input lines and the
  choice-point stream-end block). `appendInput(text, display?)` echoes one `.inp` line through
  the divider/unread/scroll-keep behavior; `mount/replace/unmountChoicePoint` own exactly one
  stream-end block (no-ops when none is mounted; blocks are caller-supplied DOM nodes).
- **`actions`** — the single action-dispatch entry. `submit(actionId, payload, display?)`
  returns a request id exactly when a real request dispatched (locked or duplicate submits
  dispatch nothing and echo nothing); the `display` descriptor never leaks into the wire
  payload. `client` is the DOM-independent action client (`createActionClient` surface);
  `isInFlight`/`isLocked` drive the mutation lock; reconnects resync and never auto-retry.

---

## 2. Classification (every implementation-bound contract)

Bucket values:

- `PRESERVE-VIA-BRIDGE` — the contract survives as the C2 bridge re-exposes it; no spec delta.
- `PRESERVE-SAME-HOOK` — the Vue shell must render the same element identifier/attribute; the
  managed browser tests keep targeting it; no spec delta.
- `REMAP-TO-TESTID` — the managing change (C4) carries a `data-testid` equal to the current
  identifier string on the Vue element and retargets the affected Playwright slices; no spec
  delta because no main-requirement wording names the identifier.
- `RETIRED-WITH-SHELL` — the implementation retires at the C4 flip; the behavior it carried is
  either already implementation-neutral in spec wording or re-expressed by a §3 delta entry.
- `HARNESS-REMAP` — a test-harness global (injected by `web/tests/browser/*.py`) or an
  adjacent `window.Elosern.*` global that no main-requirement wording depends on; C4 retargets
  the affected harness/slices to the store/component contract.
- `DELTA` — the requirement wording is bound to the retiring implementation and is re-expressed
  by the named §3 delta entry.

### 2.1 façades

| Identifier | Decider | Bucket | Evidence | Rationale |
|---|---|---|---|---|
| `window.Elosern.Protocol` (all §1 members) | C2 | PRESERVE-VIA-BRIDGE | `js/elosern/protocol.js:14-20,3501`; specs `webclient-oob-protocol`, `webclient-desktop-shell` (state reduction), `webclient-browser-verification` (Node gate) | The bridge attaches the imported UMD module byte-identical; every façade-referencing requirement stays true unchanged |
| `window.Elosern.KeyboardRouter` (all §1 members) | C2 | PRESERVE-VIA-BRIDGE | `js/elosern/keyboard_router.js:14-20,353-362` | Same: module re-exposed; router behavior (claim semantics, gates, repeat suppression) preserved by §3 key-path re-expressions |
| `window.Elosern.narrativeInput` (all §1 members) | C2 | PRESERVE-VIA-BRIDGE | `js/plugins/goldenlayout.js:1367-1381`; `js/elosern/stream_end_block.js:5-9`; spec `webclient-action-choicepoints:7,45`; `webclient-desktop-shell` (single append path) | The bridge makes the store's append path the single owner under the same façade name; §2.5 keeps the echo behavior |
| `window.Elosern.actions` (all §1 members) | C2 | PRESERVE-VIA-BRIDGE | `js/plugins/elosern_actions.js:286-338`; attached at `js/plugins/elosern_ui.js:611`; specs `webclient-options-surface:75-76`, `webclient-input-narrative:50-88`, `webclient-local-map:161` | The bridge keeps `actions.submit` the single dispatch entry and `client` the locked action client; requirements naming `window.Elosern.actions.submit` stay true |
| `window.Elosern.keyboard` (live router instance) + adjacent instance façades: `StateController`, `goldenlayout`, `drawer`, `_combat`, `explorationDock`, `serviceDock`, `creationDock`, `characterDock`, `combatDock` | C4 | HARNESS-REMAP | defined in `js/plugins/elosern_ui.js:367`, `goldenlayout.js:1342-1354,496-497,1367`, `combat_dock.js:397-405`, `exploration_dock.js:996-999`, `services_dock.js:550-553`, `creation_dock.js:1141-1144`, `character_dock.js:205-206`; driven by `browser_helpers.py` (`store_state`, `waitActive`) and `test_browser_creation.py:238,711-712`, `test_browser_services.py:332-336,378-380`, `test_browser_exploration.py:403-416`, `test_browser_shell.py:547`, `test_browser_reconnect.py:184,238-240` | No main-requirement wording names these globals; they are test-harness and dock-internal handles. C4 retargets the harness to the store (`C1`) and component contract; the bridge need not expose them |
| Module façades the Node/browser tests import directly: `LayoutStore`, `State`, `Actions`, `DockSurface`, `OptionCards`, `ChoicePoints`/`ChoicePointLogic`, `CharacterMenu`, `CombatMenu`, `ServiceMenu`, `CreationMenu`, `ExplorationMenu`, `LocalMap`, `NarrativeMarkup`, `StreamEndBlock`, `CommandEcho`, `ArtPanel`, `ArtFocus`, `KeyboardRouter` | C4 | HARNESS-REMAP | each defined at `js/elosern/<module>.js` (UMD attach); used by `js/tests/*.test.js` (Node gate, untouched) and `browser_helpers.py`/browser slices | The UMD modules themselves are preserved and imported through Vite CJS interop (A2 `lib/*`); the harness re-imports them via the app bundle at C4. No spec delta |

### 2.2 Keyboard / plugin key-event path

| Identifier | Decider | Bucket | Evidence | Rationale |
|---|---|---|---|---|
| Evennia plugin `onKeydown` hook = `routeKeyboard` (the single production key path) | C2 | DELTA | `js/plugins/elosern_ui.js:168-227,674`; claim contract (claim exactly when the router consumed or the open drawer owned; `/` drawer toggle; slash-as-text in editables; repeat guard) | The plugin hook retires at the C4 flip; the same claim contract is re-expressed against the C2 bridge (entries C2-01, C2-02) so the spec is true from C2 onward |
| Stock-plugin ordering (“the project plugin SHALL be ordered after the stock plugins”) | C2 | DELTA | spec `webclient-pointer-activation:73-82` (requirement “Keyboard input is dispatched through the WebClient plugin contract”) | With no Evennia plugins after the flip, ordering is meaningless; the fall-through contract (unclaimed keys reach the text/history path) replaces it (entry C2-01) |
| Plugin-handler log semantics (“NO plugin handled this Keydown”, “no unhandled keydown”) | C2 | DELTA | specs `webclient-desktop-shell:118-121,192`; `webclient-character-creation-ui:177,193,197` | Re-expressed as the bridge claiming owned keys and letting unowned keys reach the fall-through text path (entries C2-02, C2-03) |
| Self-contained modal key captures: `_bindFormKeys` (creation), `_bindQuantityKeys` (services), `_bindRestKeys` (exploration) | C2 | DELTA | `js/plugins/creation_dock.js:791`, `services_dock.js:256`, `exploration_dock.js:587`; spec `webclient-character-creation-ui:177-197` | The capture-phase pre-emption behavior is preserved by the bridge/app; only the wording naming the stock handler changes (entry C2-03) |
| `Evennia.sendInputField` (ordinary text send through the transport) | C4 | PRESERVE-VIA-BRIDGE | `js/plugins/goldenlayout.js:484`; spec `webclient-desktop-shell:136-160` (drawer text control) | The Vue app keeps the existing `evennia.js` transport; typed commands keep sending as ordinary text (never `ui_action`) — the requirement wording is implementation-neutral and stays true |

### 2.3 DOM identifiers (managed browser tests + keyboard router targets) — re-frozen at the
post-redesign client (H6)

The H1–H5 redesign waves re-mapped the browser-targeted identifier set. This section is the renewed
frozen list: the preserved contract hooks H1 froze, plus every `data-testid` re-map performed by
H1–H5 and the CSS class hooks the managed browser suite targets. It is a single deliverable — no
second parallel list.

**Preserved contract hooks** — the Vue shell renders these identifiers unchanged; the managed browser
tests keep targeting them; no spec delta:

| Hook | What it is | Bucket |
|---|---|---|
| `action-dock` | the single persistent `#action-dock` node carrying its `data-mode` attribute and listbox composite role; the surface's documented focus target (`webclient-pointer-activation`, `webclient-browser-verification:50,54,86`) | PRESERVE-SAME-HOOK |
| `combat-row-<i>` (row id pattern, prefix `combat-row`) | the combat dock's row frames (`test_browser_combat.py` targets `#combat-row-0` before key presses) | PRESERVE-SAME-HOOK |
| `data-item-key` (row attribute; `target-` prefix in target menus) | row identity and pointer/keyboard parity handle (`webclient-options-surface:75-76`) | PRESERVE-SAME-HOOK |
| `inputfield` (command-line field, inside `.inputfieldwrapper`) | the always-visible command-line input the key path owns (`webclient-desktop-shell:136-167`) | PRESERVE-SAME-HOOK |
| `.inp` / `.narrative-divider` (narrative classes) | player input line + divider (`webclient-desktop-shell:285-318`) | PRESERVE-SAME-HOOK |
| `narrative-unread` (+ `.narrative-unread-button`, `data-count`) | the unread marker control (`webclient-desktop-shell:51-68`) | PRESERVE-SAME-HOOK |
| `elosern-action-live` | the non-interrupting live region for action notices (`webclient-desktop-shell:238-239`); rendered by the Vue shell, no longer actively targeted by the managed suite | PRESERVE-SAME-HOOK |
| `elosern-offline-overlay` | the non-dismissible offline overlay (`webclient-desktop-shell:262-283`); `test_browser_shell.py`, `test_browser_reconnect.py` | PRESERVE-SAME-HOOK |
| `data-node` / `data-node-id` (minimap node attributes) | minimap node identity/focus hooks (`test_browser_local_map.py`) | PRESERVE-SAME-HOOK |

**Re-mapped `data-testid` set (H1–H5)** — each family below is re-mapped to a stable `data-testid`
hook; the managed Playwright slices were retargeted by the owning wave (roadmap §5: each wave re-maps
the selectors it breaks). Prefix entries cover dynamic suffixes.

| Hook family | Wave | Bucket |
|---|---|---|
| `topbar`, `topbar-clock`, `topbar-location` | H1 | REMAP-TO-TESTID |
| `narrative-feed`, `narrative-fulllog-control` | H1 | REMAP-TO-TESTID |
| `text-console`, `text-console-input`, `text-console-log` (the dependency-free fallback console) | H1 | REMAP-TO-TESTID |
| `scene-backdrop` + `scene-backdrop-<suffix>` (`scene-backdrop-image`, `scene-backdrop-label`, `scene-backdrop-alt`, `scene-backdrop-placeholder`) | H1 | REMAP-TO-TESTID |
| `anchor-<name>` (prefix `anchor`: `anchor-hud-left`, `anchor-hud-right`, `anchor-feed`, `anchor-dock`) | H1 | REMAP-TO-TESTID |
| `elosern-stage` (carries `data-elosern-mode` + `data-menu-open`), `elosern-vue-root` | H1 | REMAP-TO-TESTID |
| `status-panel` + `status-panel__<suffix>` (`status-panel__condition-overflow`, `status-panel__condition--<code>`, `status-panel__gauge-value--<gauge>`) | H2 | REMAP-TO-TESTID |
| `character-head` + `character-head__<suffix>` (`__badge`, `__disguise`, `__glyph`, `__name`, `__rank`, `__wallet`) | H2 | REMAP-TO-TESTID |
| `local-map`, `local-map-detail`, `local-map-remembered`, `local-map__<suffix>` (`local-map__lattice`, `local-map__legend`, `local-map__title`, `local-map__marker--current`, `local-map__unavailable`, `local-map__actionable`); H5 adds `local-map__expand` (the full-map control, mounted with the `MapOverlay` it opens) | H2, H5 | REMAP-TO-TESTID |
| `dock-menu`, `dock-crumb`, `dock-crumb__<suffix>` (covers the breadcrumb back control `dock-crumb__back`), `suggestions-section`, `suggestions-generating`, `dock-tab-<tab>` (prefix `dock-tab`: `dock-tab-flee`, `dock-tab-interact`, `dock-tab-move`, `dock-tab-look`, `dock-tab-suggestions`), `action-dock-description`, `exploration-detail`, `exploration-rest-form` | H3 | REMAP-TO-TESTID |
| `command-line` + `command-line-<suffix>` (`command-line-input-field`, `command-line-prompt`, `command-line-settings`, `command-line-help`) | H5 | REMAP-TO-TESTID |
| `map-overlay`, `map-overlay-content`, `map-overlay-unavailable` | H5 | REMAP-TO-TESTID |
| `settings-overlay`, `help-overlay`, `creation-<suffix>` (prefix `creation`: `creation-body`, `creation-submit`, `creation-confirm`, `creation-reset`, `creation-concept-indicator`, `creation-preset-card`, `creation-race`, `creation-field-<name>`), `overlay-host`, `overlay-host-close` | H5 | REMAP-TO-TESTID |
| `character-status-drawer__condition--<code>` (covers e.g. --regen), `character-status-drawer__guild-merit`, `character-status-drawer__guild-rank` (the re-chromed status-drawer condition and guild-counter rows, added by the align-webclient-character-status-drawer-chrome change) | chrome-align | REMAP-TO-TESTID |
| `fulllog-overlay`, `fulllog-close` | H1 | REMAP-TO-TESTID |
| `hud-drawer`, `hud-drawer-scrim` + `.hud-drawer__title`; `character-status-drawer`, `equipment-doll` (the drawer bodies H4 migrated out of the right column) | H4 | REMAP-TO-TESTID |
| `participant-frame`, `participant-portrait-placeholder` + `participant-frame__<suffix>` (`participant-frame__row`, `participant-frame__name`, `participant-frame__group-label`, `img.participant-frame__portrait`) | H3 | REMAP-TO-TESTID |
| `quest-board` + `quest-board__<suffix>` (`quest-board__abandon`, `quest-board__register`, `quest-board__rankblock`, `quest-board__board-row--<state>`, `quest-board__quest-row--<state>`) | H4 | REMAP-TO-TESTID |
| `art-panel` + `.art-panel__<suffix>` (`.art-panel__portrait-tile`) | H1 (still mounted) | REMAP-TO-TESTID |
| `connect-overlay` (the offline/connect overlay in the Vue root) | H1 | REMAP-TO-TESTID |
| `combat-detail` | H3 | REMAP-TO-TESTID |
| `quick-word-chip-<verb>` (prefix `quick-word-chip`: `quick-word-chip-看`, the quick-word command chips) | H6 | REMAP-TO-TESTID |

**CSS class hooks the managed browser suite targets** (re-mapped to stable hooks, no main-requirement
wording names any of these, so no spec delta):

| Hook | Bucket |
|---|---|
| `.dock-menu-item` (prefix; covers `.dock-menu-item--focused` under `#action-dock`) | REMAP-TO-TESTID |
| `.dock-menu`, `.dock-menu-layout`, `.dock-menu__outlet`, `.dock-menu__outlet-tile`, `.dock-menu__nav-sub`, `.dock-menu__plain`, `.dock-menu .dock-menu__scale`, `.dock-menu .dock-menu__skill--on`, `.dock-menu .dock-menu__token--pressed` | REMAP-TO-TESTID |
| `.dock-tab-bar__<suffix>` (prefix `dock-tab-bar`: `__badge`, `__tab--on`, `svg.dock-tab-bar__icon`) | REMAP-TO-TESTID |
| `.hint` (the command-line hint cluster naming the history-recall keys; targeted by `test_browser_input_narrative.py`) | PRESERVE-SAME-HOOK |
| `.drawer-entry`, `.header-mode`, `.meta-conn`, `.services-confirm`, `.skill-detail-pane__disabled`, `.narrative-divider` (preserved), `.inputfieldwrapper` (preserved wrapper for `inputfield`) | RETIRED-WITH-SHELL |
| `.lm_header` (legacy GoldenLayout header assertion: must NOT render) | RETIRED-WITH-SHELL |
| `.elosern-*` retired visual classes (`.elosern-narrative`, `.elosern-placeholder`, `.elosern-header`, `.elosern-status`, `.elosern-action-dock`) — the managed suite asserts they no longer render on the Vue shell | RETIRED-WITH-SHELL |
| `messagewindow` (the retired `default_out` fallback host; revealed on demand by `test_vue_foundation.py`) | RETIRED-WITH-SHELL |

**Out of shell scope (harness targets a Django-rendered page):** the managed harness logs in through
`#id_username` / `#id_password` (`web/tests/browser/browser_helpers.py:105-112`). These select the
stock Evennia login form, which the Vue shell does not own, so the login targets stay valid with no
preserve/remap decision.

**Template / mount contract** (renewed at H6; no spec delta beyond the entries above):

| Contract | Bucket |
|---|---|
| `base.html` serves the built Vite bundle (`web/static/webclient/app/dist`) — the jQuery/GoldenLayout/plugin script loads were removed at the C4 flip; the stage mounts through `main.js` | RETIRED-WITH-SHELL |
| `evennia.js` transport + `Evennia.*` globals (`sendInputField`, `connection`, `.msg`) are preserved by the bridge | PRESERVE-VIA-BRIDGE |

**H6 verification (task 3.4):** the `window.Elosern.*` public façade surface (the §1
`frozen-facade-surface` JSON — `Protocol`, `KeyboardRouter`, `narrativeInput`, `actions`) and the
keyboard-router claim contract (C2's re-expression in `webclient-pointer-activation`) are **unchanged**
by the H1–H5 redesign: the redesign is a view-layer change on the existing transport, so the frozen
façade member lists in §1 remain the binding surface, and the keyboard-router consumption contract
(`routeKeyboard` claim rules, modal capture pre-emption) is carried by the bridge untouched.

### 2.4 Layout-persistence keys

| Key / constant | Decider | Bucket | Evidence | Rationale |
|---|---|---|---|---|
| `elosern.layout` (localStorage) + `CURRENT_LAYOUT_VERSION = 1` + wrapper shape `{layout_version, dimensions, tabs, preferences}` | — | PRESERVE-VIA-BRIDGE | `js/elosern/layout_store.js:25-33`; `webclient-desktop-shell:222-235` (“Browser persistence is versioned and presentation-only”); `test_browser_layout.py:25-34` | The preserved `LayoutStore` module remains the persistence owner (C1's store consumes it); the wording is implementation-neutral |
| `STOCK_KEYS` = `["evenniaGoldenLayoutSavedState", "evenniaGoldenLayoutSavedStateName"]` | — | PRESERVE-VIA-BRIDGE | `layout_store.js:28-31`; spec scenario “Stock layout state is not imported” (`:233-235`) | Version 1 still must not import stock keys; the constant survives in the preserved module |
| `REQUIRED_COMPONENTS` = header, narrative, art, status, local-map, action-dock, command-drawer; `PREFERENCE_TYPES` = `text2html`, `fontScale`; `MAX_STORAGE_BYTES = 2048`; dimension/font-scale bounds | — | PRESERVE-VIA-BRIDGE | `layout_store.js:33-53`; `webclient-desktop-shell:8` (required-component list) | The required-surface set is the Vue shell's too (roadmap §5 B-waves); `command-drawer` maps to the GL config id `inputComponent` (`layout_store.js:104`) |
| Migration/reset rule (known versions migrate explicitly; unknown/malformed/oversized/stock reset to the version-1 default) | — | PRESERVE-VIA-BRIDGE | `layout_store.js:344-359,440-447`; `test_browser_layout.py:56-120` (incl. `elosern.migration-probe`) | Behavior preserved; C4 keeps the same `LayoutStore` under the Vue shell |
| `elosern.sync_recovery_reload` (sessionStorage recovery marker) | C2 | PRESERVE-VIA-BRIDGE | `js/plugins/elosern_state.js:314`; `webclient-desktop-shell:262-283`, `webclient-oob-protocol:173`; `test_browser_session_lifecycle.py` | The one-reload-sync recovery stays with the state owner over the bridge |

### 2.5 Input path (typed command flow)

| Contract | Decider | Bucket | Evidence | Rationale |
|---|---|---|---|---|
| Drawer default-closed; entry button a real `<button type="button">` with accessible name + `aria-expanded`; `/` toggle | C4 | PRESERVE-SAME-HOOK | `goldenlayout.js:385-391,446-457`; spec `webclient-desktop-shell:136-167` (behavioral wording, no id) | The Vue drawer implements the same behavioral contract; the entry-button hook is in the §2.3 remap table |
| Enter sends exactly one ordinary text message via the transport; Shift+Enter newline; focus retention; borrowed-drawer release rules | C4 | PRESERVE-VIA-BRIDGE | `goldenlayout.js:459-489` (`sendCommand` → `Evennia.sendInputField`); spec `webclient-desktop-shell:136-218` | Implementation-neutral wording; the Vue input routes through the same transport text path |
| Slash-as-text in focused editables (drawer field, creation forms, rest forms) | C2 | DELTA | spec `webclient-desktop-shell:96-98,129-133`; key path `js/plugins/elosern_ui.js:20-28,204-219` | Part of the bridge key-claim contract; covered by entry C2-02's re-expression |
| One echo per dispatched mutation / typed send, via `CommandEcho.commandLine` → `narrativeInput.appendInput` (echo never affects the wire payload) | C2 | PRESERVE-VIA-BRIDGE | `js/elosern/command_echo.js`; `js/plugins/elosern_actions.js:286-338`; specs `webclient-input-narrative:11-88`, `webclient-desktop-shell:285-318` | Both façades frozen in §1; `CommandEcho` is preserved UMD logic imported by the bridge/app |

### 2.6 Test-harness globals (injected, not product surface)

| Global | Decider | Bucket | Evidence |
|---|---|---|---|
| `window.__elosernWs` (OOB capture wrapper) | C4 | HARNESS-REMAP | `web/tests/browser/browser_base.py` (`_WS_CAPTURE_SCRIPT`) |
| `window.__elosernSent` (outbound recorder) + helpers `sent_action_count`, `store_state`, `fresh_epoch`, `snapshot_envelope`, `valid_status_panel`, `guard_local_only` | C4 | HARNESS-REMAP | `web/tests/browser/browser_helpers.py` |
| Adjacent-façade drives (`Elosern.StateController.getState/requestResync`, `Elosern.goldenlayout.onText/getGL`, `Elosern.explorationDock.*`, `Elosern.serviceDock.*`, `Elosern.creationDock.*`, `Elosern._combat.*`) | C4 | HARNESS-REMAP | `test_browser_input_narrative.py:162,212,238,445,556-558`, `test_browser_creation.py:711-712,1019-1023`, `test_browser_services.py:332-336,378-380`, `test_browser_exploration.py:403-416`, `test_browser_reconnect.py:184,334-336`, `test_browser_combat.py:426-443` |
| `BROWSER_ACCOUNT`, `ELOSERN_BROWSER_EXPLORATION`, default viewport 1440x900 / 1280x720 | C4 | HARNESS-REMAP | `browser_helpers.py`, `browser_base.py` | Not a client contract; the harness retarget at C4 keeps these invariants unchanged |

---

## 3. Delta list (MODIFIED / RENAMED)

The complete `MODIFIED`/`RENAMED` delta set. Each entry names the affected main-spec requirement
(capability + requirement heading, as of A1), the applying change, the instruction to the applying
change, and the rationale. Entries are non-overlapping: no `(capability, requirement)` pair
appears twice. The applying change writes the exact re-expression during its own implementation
and re-points the requirement's traceability test in the same change (C2 design D2). Every
requirement whose wording stays true through the migration is **not** listed here (it is
preserve-classified in §2).

```json
{
  "frozen-delta-list": [
    {
      "delta_id": "C2-01",
      "kind": "MODIFIED",
      "capability": "webclient-pointer-activation",
      "requirement": "Keyboard input is dispatched through the WebClient plugin contract",
      "applying_change": "webclient-vue-08-wire-bridge-contracts",
      "binding_identifiers": [
        "Evennia plugin onKeydown hook (routeKeyboard)",
        "stock-plugin ordering"
      ],
      "directive": "Re-express against the preserved public keyboard bridge: key input SHALL be dispatched through the KeyboardRouter handle path exposed by the bridge (window.Elosern.KeyboardRouter claim contract), claimed exactly when the router consumed the event or when the open command drawer owns the key; unconsumed keys SHALL fall through to the text and history path; the stock-plugin ordering sentence is dropped; a modal capture that must pre-empt the router MAY use a capture-phase listener and SHALL remove it when its form closes. No requirement-name change.",
      "rationale": "The Evennia plugin onKeydown hook and the stock-plugin ordering retire at the C4 flip, but the claim contract itself is implementation-neutral and is owned by the bridge that C2 lands; re-expressing at C2 keeps the spec true from C2 onward and gives C2 a passing bridge test against the re-expressed wording"
    },
    {
      "delta_id": "C2-02",
      "kind": "MODIFIED",
      "capability": "webclient-desktop-shell",
      "requirement": "Keyboard routing is menu-first and submission-safe",
      "applying_change": "webclient-vue-08-wire-bridge-contracts",
      "binding_identifiers": [
        "WebClient plugin onKeydown contract (spec:90-91)",
        "scenario 'Key dispatch goes through the plugin contract' (spec:118-121)",
        "plugin-handler 'no unhandled keydown' assertion (spec:192)"
      ],
      "directive": "Replace the plugin onKeydown dispatch sentence and the two plugin-handler log assertions with the bridge claim contract (claimed exactly when the router consumed or the open drawer owned; unclaimed keys reach the text path; slash-in-editable stays ordinary text). Keep every other sentence (menu geometry, `/` toggle, repeat/Enter suppression, mutation gating) verbatim. No requirement-name change.",
      "rationale": "Same bridge-contract re-expression as C2-01 for the shell's own keyboard-routing requirement; the behavioral contract is unchanged, only the dispatch mechanism named"
    },
    {
      "delta_id": "C2-03",
      "kind": "MODIFIED",
      "capability": "webclient-character-creation-ui",
      "requirement": "The creation dock is keyboard-first, form-capable, and confirmation-protected",
      "applying_change": "webclient-vue-08-wire-bridge-contracts",
      "binding_identifiers": [
        "'claim every keydown while the form owns focus so no unclaimed keydown reaches the stock plugin handler' (spec:177)",
        "'no NO plugin handled this Keydown is logged' (spec:193, 197)"
      ],
      "directive": "Re-express the form-capture clauses against the bridge: the custom form SHALL pre-empt the keyboard bridge while it owns focus (capture-phase), and keys the form owns SHALL be claimed by the form so none reach the bridge's fall-through text path. Keep the IME/no-preventDefault, held-Enter-suppression, and confirmation behavior verbatim. No requirement-name change.",
      "rationale": "The creation form already owns its keys today via _bindFormKeys; only the named destination of unowned keys (stock plugin handler vs bridge fall-through) changes"
    },
    {
      "delta_id": "C4-01",
      "kind": "RENAMED+MODIFIED",
      "capability": "webclient-desktop-shell",
      "requirement": "The WebClient loads a local Vue SPA desktop shell",
      "rename_to": "The WebClient loads a local Vue SPA desktop shell",
      "applying_change": "webclient-vue-10-wire-views-browser",
      "binding_identifiers": [
        "jQuery 3.2.1 + GoldenLayout 1.x vendor assets (spec:8)",
        "settings.hasHeaders: false / .lm_header scenario (spec:22-24)",
        "scenario 'Offline page load has its UI dependencies' GoldenLayout wording (spec:10-12)"
      ],
      "directive": "Rename the requirement to 'The WebClient loads a local Vue SPA desktop shell'. Re-express the body: the shell is the project's Vite-built Vue SPA bundle served from the project origin (still with Evennia's existing transport; still no remote runtime UI dependency); the layout-version-1 required-surface list (header, narrative, art, status, local-map, action-dock, command-drawer) is preserved; the 'no GoldenLayout tab strip' and the `.lm_header` scenario become 'the shell renders no tab strip' with each surface self-identifying by content. Keep the local-map/art component sentences verbatim.",
      "rationale": "The shell identity changes only at the C4 production flip; until then the main spec must keep describing the real production shell"
    },
    {
      "delta_id": "C4-02",
      "kind": "MODIFIED",
      "capability": "webclient-desktop-shell",
      "requirement": "Required desktop surfaces remain visible and usable",
      "applying_change": "webclient-vue-10-wire-views-browser",
      "binding_identifiers": [
        "scenario 'Mounting the shell retires the degraded text fallback': 'the GoldenLayout shell mounts into its container ... the stock text-only fallback is hidden' (spec:38-40)"
      ],
      "directive": "Re-express only that scenario: mounting the Vue SPA shell retires the degraded stock text fallback (the `#messagewindow` fallback is hidden so it cannot stack with the mounted shell). Keep every other sentence and scenario verbatim. No requirement-name change.",
      "rationale": "The fallback-hiding contract is preserved; only the mounting entity named (GoldenLayout container vs Vue mount) changes at the flip"
    },
    {
      "delta_id": "C4-03",
      "kind": "MODIFIED",
      "capability": "webclient-narrative-markup",
      "requirement": "The converted-stream assumption is bounded and enforced",
      "applying_change": "webclient-vue-10-wire-views-browser",
      "binding_identifiers": [
        "'the shell or the stock plugins insert into the narrative without conversion' (spec:86)",
        "scenario 'Client-synthesized notices are inert': 'the stock handler inserts its notice into the narrative' (spec:93)"
      ],
      "directive": "Applied at the flip, when the stock plugins leave the load path (C4 task 1.1). Drop 'or the stock plugins': client-synthesized notices that the shell inserts into the narrative without conversion SHALL be fixed literal strings containing no markup characters; in the 'Client-synthesized notices are inert' scenario, 'the stock handler inserts its notice' becomes 'the shell inserts its notice'. Keep the raw/client_raw prohibition and the repository test sentence verbatim. No requirement-name change.",
      "rationale": "The stock plugins (default_out et al.) stay in the legacy load path until the C4 atomic flip, so the main spec must keep naming them until exactly the moment that behavior disappears; the C4 flip + legacy-load removal are one atomic change (roadmap C4 D1), so the wording fix lands with it. The literal-notice rule is unchanged, with one fewer insertor named"
    }
  ]
}
```

Entry notes:

- **C2-01 … C2-03** are the bridge-contract re-expressions. The bridge (C2) lands with tests that
  establish each re-expressed contract (asserted key path over the `KeyboardRouter` module,
  single-entry `narrativeInput`/`actions`, no plugin involvement), so each re-expressed
  requirement has a passing test at C2's archive (C2 design D2).
- **C4-01, C4-02, C4-03** are the flip-time edits, applied at the production flip, where the main
  spec becomes true-at-archive for the Vue desktop shell (roadmap §5 C4: “`webclient-desktop-shell`
  RENAMED from the GoldenLayout shell to the Vue SPA desktop shell”). C4-03’s narrative-markup fix
  lands with C4 (not C2) because the stock plugins it stops naming remain in the legacy load path
  until the flip. C4 also executes the §2.3 remap decisions and remaps the remaining Playwright
  behavioral slices to the preserved hooks + `data-testid` in the same change.
- No other `webclient-*` requirement wording goes stale: every remaining implementation-bound
  identifier is preserve-classified (§2) — the four façades survive via the bridge, the DOM
  contract hooks are preserved, the layout-persistence contract is owned by the preserved
  `LayoutStore`, and the narrative/echo/transport behavior is implementation-neutral.

---

## 4. Reference (informational; unchanged by the migration)

- **OOB envelopes** (client-validated names, `PROTOCOL_VERSION = 1`): `ui_sync`, `ui_action`,
  `ui_snapshot`, `ui_update`, `ui_action_result`, `ui_protocol_error`, `connection_open`
  (`js/elosern/protocol.js`; spec `webclient-oob-protocol:8`). Server-side shapes are unchanged by
  the migration (roadmap §2 non-goals).
- **Server-side action allowlist** (dispatched via `actions.submit`; the client never
  allowlists): `explore.look`, `explore.move`, `explore.talk_scripted`, `explore.talk_freeform`,
  `explore.examine`, `explore.ask`, `explore.query`, `explore.interact`, `explore.pick`,
  `explore.drop`, `explore.engage`, `explore.wait`, `explore.party_invite`, `explore.party_leave`,
  `explore.character`, `explore.guild`, `explore.guild.quest_accept`, `explore.guild.quest_turnin`,
  `explore.guild.quest_abandon`, `creation.preset_selected`, `creation.custom_filled`,
  `creation.concept_filled`, `creation.activate_player`, `creation.exploration`, `creation.reset`,
  `combat.basic_attack`, `combat.cast`, `combat.attack_entity`, `combat.attack_allies`,
  `combat.attack_all_enemies`, `combat.flee`, `combat.forfeit`, `guild.register`,
  `guild.quest_accept`, `guild.quest_abandon`, `guild.quest_turnin`, `guild.exam_start`,
  `shop.buy`, `shop.sell`, `options.dismiss` (spec `webclient-action-dispatch:30-50`).
- **Test-harness invariants** (unaffected by the migration): isolated managed Evennia runtime
  per invocation, localhost-only requests, deterministic fixtures, `BROWSER_ACCOUNT`,
  1440x900 primary / 1280x720 minimum viewport (spec `webclient-browser-verification:19-38`).

---

## 5. Completeness statement

- Enumeration was grep-driven (A1 design D2): `window.Elosern.`, `onKeydown`, `getElementById` /
  `#` id selectors in `web/tests/browser/` and the keyboard router, and the layout-persistence
  keys, across `openspec/specs/webclient-*/spec.md`, `web/tests/browser/`,
  `web/static/webclient/js/`, and `web/templates/webclient/`.
- Every implementation-bound identifier found lands in exactly one §2 row (one bucket). The
  four frozen façades and their members are listed exhaustively in §1 (machine-derived).
- Every main-spec requirement whose wording is bound to the retiring implementation appears in
  exactly one §3 delta entry; every other requirement is preserve-classified. C2 re-checks this
  net against the Playwright suite before the flip (C2 risk section); any omission C2 surfaces is
  amended back into this document (roadmap §9 precedence).

---

## 6. Revision log

### A1.1 — 2026-08-20 (post-archive, synchronous rubber-duck critique)

- **§2.3 completeness:** five missed managed-browser target groups were added as
  `REMAP-TO-TESTID` rows — `creation-concept-submit` / `creation-form-message` /
  `creation-race-<i>` (creation dock), `exploration-detail` (element + class), and
  `services-quantity` / `services-quantity-value` (services dock). The harness login selects
  (`#id_username`, `#id_password`) are documented as out of shell scope: they target the
  Django-rendered login page, which the flip does not touch. `tests/test_webclient_frozen_contract.py`
  now extracts every `getElementById` / `#id` target from `web/tests/browser/` and fails unless it
  is covered by a §2 row (or an explicit exemption), so this class of omission cannot recur.
- **C2-04 → C4-03 re-assignment:** the `webclient-narrative-markup` delta now names
  `webclient-vue-10-wire-views-browser` as its applying change. The stock plugins it stops naming
  remain in the legacy load path from C2 until C4's atomic flip (C4 task 1.1), so the main spec
  must keep describing them until exactly the moment that behavior disappears. The C4 change's
  artifacts were updated in the same revision (its `webclient-narrative-markup` delta spec, flip
  task, and D2 hook wording now reference this audit row-by-row).
- **C4-01 `rename_to` fixed** to `The WebClient loads a local Vue SPA desktop shell`, the exact
  target name the C4 delta spec and the roadmap use (the A1.0 text had the word order inverted).
