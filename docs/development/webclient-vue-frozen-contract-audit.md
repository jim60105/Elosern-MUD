# WebClient Phase-0 凍結契約審查（Frozen Contract Audit）

**狀態：** 由 `webclient-vue-00-audit-and-design-docs`（路線圖變更 **A1**）凍結（FROZEN）。
**指導路線圖：** `docs/superpowers/specs/2026-08-19-webclient-vue-migration-roadmap-design.md`。
**約束性消費者（Binding consumers）：**

- `webclient-vue-08-wire-bridge-contracts`（**C2**）為凍結 façade 橋接介面（§1）的**約束性消費者（binding consumer）**，並套用指定它的增量項目（§3）。
- `webclient-vue-10-wire-views-browser`（**C4**）套用指定它的切換期增量項目（§3），並執行 DOM 重新對應決策（§2.3）。

本文件為 Phase-0 設計（A1 設計 D1/D2）的 Phase-0 契約審查：列舉了 `openspec/specs/webclient-*/spec.md`（17 個 `webclient-*` 主要能力）與受管 Playwright 套件 `web/tests/browser/` 中所有綁定實作的客戶端契約，將每個契約分類為「透過橋接保留」或「增量變更」，並凍結 (a) 瀏覽器橋接器（C2）必須暴露的確切 `window.Elosern.*` façade 橋接介面，以及 (b) 完整的 `MODIFIED`/`RENAMED` 增量清單。增量**不由 A1 套用**；每個項目皆註明其套用變更。

列舉方法（A1 設計 D2）：grep 驅動。擷取了所有出現的 `window.Elosern.`、`onKeydown` 外掛路徑、Playwright 套件與鍵盤路由器中的 `getElementById` 與 `#`-id 目標，以及版面配置持久化索引鍵，並加以分類；讀取了客戶端原始碼（`web/static/webclient/js/`）與 `web/templates/webclient/base.html` 中的分類位置以確立定義證據。§1 中的 façade 成員清單是直接從 UMD 模組本身機械式衍生（在 `protocol.js` 與 `keyboard_router.js` 上執行 Node `Object.keys`），而非手動抄錄。

本文件中的每個實作綁定識別碼皆恰好落入單一分組（§2）。沒有任何識別碼被重複分類，且每個分組項目皆具備理由說明。

---

## 1. Frozen façade-bridge surface

瀏覽器橋接器（C2）應在 `window.Elosern.*` 恰好暴露這四個 façade，且恰好包含這些成員。`Protocol` 與 `KeyboardRouter` 為保留的 UMD 模組本身，以位元組完全相同的方式附加（橋接器重新暴露匯入，不重新實作）。`narrativeInput` 與 `actions` 為單一擁有者 façade：分別為 store 的單一敘事／抉擇點附加路徑，以及單一動作分派進入點。

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

Façade 說明（行為契約，橋接器必須保留行為而不僅僅是名稱）：

- **`Protocol`** — 傳輸生成 reducer 及其驗證器表格。`createStore` 回傳 store 介面 `create_store_members`（不可部分發布的快照採用、epoch 與修訂版本門控、過期 epoch 集合、每次認可一次通知的語意，即由 `webclient-oob-protocol` 與 `webclient-desktop-shell` 狀態化簡需求所固定的行為）。`envelope_names` 清單為確切的版本化 OOB 訊息集合（`PROTOCOL_VERSION = 1`）。
- **`KeyboardRouter`** — 選單堆疊焦點路由器。`createRouter(options)` 回傳恰好具備 `router_instance_members` 的路由器；`handle(key, repeat)` 為單一按鍵進入轉接器。宣告語意：`press`/`handle` 恰好在路由器消耗該按鍵（方向鍵／Enter／Escape／Space／`/`）時回傳 `true`，且重複的 Enter 與 Space 會被壓制；未消耗的按鍵回傳 `false` 並向下傳遞。`setMutationInFlight`/`isAwaitingRevision` 為提交門控。正式環境的 `window.Elosern.keyboard` 實例是*相鄰*的測試架構全域變數，非凍結模組介面的一部份（§2.1）。
- **`narrativeInput`** — 單一敘事附加路徑（玩家輸入行與抉擇點串流結尾區塊）。`appendInput(text, display?)` 透過分隔線、未讀與捲動保持行為回顯一行 `.inp`；`mount/replace/unmountChoicePoint` 擁有恰好一個串流結尾區塊（無掛載時為 no-op，區塊為呼叫端提供的 DOM 節點）。
- **`actions`** — 單一動作分派進入點。`submit(actionId, payload, display?)` 恰好在真實請求分派時回傳請求 ID（已鎖定或重複的提交不分派且不回顯）；`display` 描述器絕不外洩至傳輸承載資料中。`client` 為獨立於 DOM 的動作客戶端（`createActionClient` 介面）；`isInFlight`/`isLocked` 驅動異動鎖定；重新連線執行重新同步且絕不自動重試。

---

## 2. Classification (every implementation-bound contract)

分組值（Bucket values）：

- `PRESERVE-VIA-BRIDGE` — 契約在 C2 橋接器重新暴露後存續，無規格增量。
- `PRESERVE-SAME-HOOK` — Vue 主架構必須算繪相同的元素識別碼／屬性，受管瀏覽器測試持續以其為目標，無規格增量。
- `REMAP-TO-TESTID` — 管理變更（C4）在 Vue 元素上帶有等於目前識別碼字串的 `data-testid`，並重新導向受影響的 Playwright 切片，因無主要需求文字命名該識別碼，故無規格增量。
- `RETIRED-WITH-SHELL` — 該實作在 C4 切換時停用，其承載的行為在規格文字中已具備實作中立性，或由 §3 增量項目重新表述。
- `HARNESS-REMAP` — 測試控管全域變數（由 `web/tests/browser/*.py` 注入）或無主要需求文字依賴的相鄰 `window.Elosern.*` 全域變數，C4 將受影響的架構與切片重新導向至 store 與元件契約。
- `DELTA` — 需求文字綁定至停用的實作，並由指定的 §3 增量項目重新表述。

### 2.1 façades

| Identifier | Decider | Bucket | Evidence | Rationale |
|---|---|---|---|---|
| `window.Elosern.Protocol` (all §1 members) | C2 | PRESERVE-VIA-BRIDGE | `js/elosern/protocol.js:14-20,3501`; specs `webclient-oob-protocol`, `webclient-desktop-shell` (state reduction), `webclient-browser-verification` (Node gate) | 橋接器以位元組完全相同的方式附加匯入的 UMD 模組，所有引用 façade 的需求維持不變且為真 |
| `window.Elosern.KeyboardRouter` (all §1 members) | C2 | PRESERVE-VIA-BRIDGE | `js/elosern/keyboard_router.js:14-20,353-362` | 相同：模組重新暴露；路由器行為（宣告語意、門控、重複壓制）由 §3 按鍵路徑重新表述所保留 |
| `window.Elosern.narrativeInput` (all §1 members) | C2 | PRESERVE-VIA-BRIDGE | `js/plugins/goldenlayout.js:1367-1381`; `js/elosern/stream_end_block.js:5-9`; spec `webclient-action-choicepoints:7,45`; `webclient-desktop-shell` (single append path) | 橋接器使 store 的附加路徑成為相同 façade 名稱下的單一擁有者，§2.5 保留回顯行為 |
| `window.Elosern.actions` (all §1 members) | C2 | PRESERVE-VIA-BRIDGE | `js/plugins/elosern_actions.js:286-338`; attached at `js/plugins/elosern_ui.js:611`; specs `webclient-options-surface:75-76`, `webclient-input-narrative:50-88`, `webclient-local-map:161` | 橋接器維持 `actions.submit` 為單一分派進入點，`client` 為鎖定的動作客戶端，命名 `window.Elosern.actions.submit` 的需求維持為真 |
| `window.Elosern.keyboard` (live router instance) + adjacent instance façades: `StateController`, `goldenlayout`, `drawer`, `_combat`, `explorationDock`, `serviceDock`, `creationDock`, `characterDock`, `combatDock` | C4 | HARNESS-REMAP | defined in `js/plugins/elosern_ui.js:367`, `goldenlayout.js:1342-1354,496-497,1367`, `combat_dock.js:397-405`, `exploration_dock.js:996-999`, `services_dock.js:550-553`, `creation_dock.js:1141-1144`, `character_dock.js:205-206`; driven by `browser_helpers.py` (`store_state`, `waitActive`) and `test_browser_creation.py:238,711-712`, `test_browser_services.py:332-336,378-380`, `test_browser_exploration.py:403-416`, `test_browser_shell.py:547`, `test_browser_reconnect.py:184,238-240` | 無主要需求文字命名這些全域變數；它們是測試架構與 dock 內部控制代碼。C4 將測試架構重新導向至 store（`C1`）與元件契約，橋接器無需暴露它們 |
| Module façades the Node/browser tests import directly: `LayoutStore`, `State`, `Actions`, `DockSurface`, `OptionCards`, `ChoicePoints`/`ChoicePointLogic`, `CharacterMenu`, `CombatMenu`, `ServiceMenu`, `CreationMenu`, `ExplorationMenu`, `LocalMap`, `NarrativeMarkup`, `StreamEndBlock`, `CommandEcho`, `ArtPanel`, `ArtFocus`, `KeyboardRouter` | C4 | HARNESS-REMAP | each defined at `js/elosern/<module>.js` (UMD attach); used by `js/tests/*.test.js` (Node gate, untouched) and `browser_helpers.py`/browser slices | UMD 模組本身被保留並透過 Vite CJS 互通匯入（A2 `lib/*`）；測試架構於 C4 透過應用程式組合包重新匯入它們，無規格增量 |

### 2.2 Keyboard / plugin key-event path

| Identifier | Decider | Bucket | Evidence | Rationale |
|---|---|---|---|---|
| Evennia plugin `onKeydown` hook = `routeKeyboard` (the single production key path) | C2 | DELTA | `js/plugins/elosern_ui.js:168-227,674`; claim contract (claim exactly when the router consumed or the open drawer owned; `/` drawer toggle; slash-as-text in editables; repeat guard) | 外掛掛鉤在 C4 切換時停用；相同的宣告契約針對 C2 橋接器重新表述（項目 C2-01、C2-02），使規格自 C2 起維持為真 |
| Stock-plugin ordering (“the project plugin SHALL be ordered after the stock plugins”) | C2 | DELTA | spec `webclient-pointer-activation:73-82` (requirement “Keyboard input is dispatched through the WebClient plugin contract”) | 在切換後無 Evennia 外掛的情況下，排序失去意義；向下傳遞契約（未宣告的按鍵到達文字／歷史路徑）取代之（項目 C2-01） |
| Plugin-handler log semantics (“NO plugin handled this Keydown”, “no unhandled keydown”) | C2 | DELTA | specs `webclient-desktop-shell:118-121,192`; `webclient-character-creation-ui:177,193,197` | 重新表述為橋接器宣告所屬按鍵，並讓非所屬按鍵到達向下傳遞的文字路徑（項目 C2-02、C2-03） |
| Self-contained modal key captures: `_bindFormKeys` (creation), `_bindQuantityKeys` (services), `_bindRestKeys` (exploration) | C2 | DELTA | `js/plugins/creation_dock.js:791`, `services_dock.js:256`, `exploration_dock.js:587`; spec `webclient-character-creation-ui:177-197` | 擷取階段的搶佔行為由橋接器／應用程式保留；僅有命名內建處理常式的文字有所變更（項目 C2-03） |
| `Evennia.sendInputField` (ordinary text send through the transport) | C4 | PRESERVE-VIA-BRIDGE | `js/plugins/goldenlayout.js:484`; spec `webclient-desktop-shell:136-160` (drawer text control) | Vue 應用程式保留現有的 `evennia.js` 傳輸層；鍵入的指令持續作為普通文字發送（絕不為 `ui_action`），需求文字具實作中立性且維持為真 |

### 2.3 DOM identifiers (managed browser tests + keyboard router targets) — re-frozen at the post-redesign client (H6)

H1 至 H5 重設計波次重新對應了以瀏覽器為目標的識別碼集合。本節為更新後的凍結清單：包含 H1 凍結的保留契約掛鉤，加上 H1 至 H5 執行的所有 `data-testid` 重新對應，以及受管瀏覽器套件鎖定的 CSS 類別掛鉤。

**Preserved contract hooks** — Vue 主架構算繪這些不變的識別碼；受管瀏覽器測試持續以其為目標，無規格增量：

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

**Re-mapped `data-testid` set (H1–H5)** — 下列各家族重新對應至穩定的 `data-testid` 掛鉤；受管 Playwright 切片由所屬波次重新導向。前綴項目涵蓋動態後綴。

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
| `hud-drawer`, `hud-drawer-scrim` + `.hud-drawer__title`; `character-status-drawer`, `equipment-doll` + `equipment-doll__<suffix>` (the drawer bodies H4 migrated out of the right column; the realigned doll adds `equipment-doll__title`, `equipment-doll__title-tag`, `equipment-doll__doll`, `equipment-doll__slots`, `equipment-doll__slot--<slot>`, `equipment-doll__slot-empty--<slot>`, `equipment-doll__description`, `equipment-doll__description-row--<slot>`, `equipment-doll__accessories`, `equipment-doll__accessory--<key>`, added by the realign-inventory-drawer-layout change) | H4 | REMAP-TO-TESTID |
| `participant-frame`, `participant-portrait-placeholder` + `participant-frame__<suffix>` (`participant-frame__row`, `participant-frame__name`, `participant-frame__group-label`, `img.participant-frame__portrait`) | H3 | REMAP-TO-TESTID |
| `quest-board` + `quest-board__<suffix>` (`quest-board__abandon`, `quest-board__register`, `quest-board__rankblock`, `quest-board__board-row--<state>`, `quest-board__quest-row--<state>`) | H4 | REMAP-TO-TESTID |
| `art-panel` + `.art-panel__<suffix>` (`.art-panel__portrait-tile`) | H1 (still mounted) | REMAP-TO-TESTID |
| `connect-overlay` (the offline/connect overlay in the Vue root) | H1 | REMAP-TO-TESTID |
| `combat-detail` | H3 | REMAP-TO-TESTID |
| `quick-word-chip-<verb>` (prefix `quick-word-chip`: `quick-word-chip-看`, the quick-word command chips) | H6 | REMAP-TO-TESTID |
| `inventory-panel` + `inventory-panel__<suffix>` (the redesigned inventory drawer: `inventory-panel__tile--<item_key>` item tiles, `inventory-panel__count--<item_key>` held-count badges, `inventory-panel__inspector-<field>` inspector fields; the realigned three-section stack adds `inventory-panel__section--<name>`, `inventory-panel__heading--<name>`, `inventory-panel__items-count`, `inventory-panel__wallet-value`, added by the realign-inventory-drawer-layout change) | inventory-grid | REMAP-TO-TESTID |
| `dock-detail`, `hud-drawer-close` (the shared `DockMenu` detail pane probed by the bag-hosting assertions, and the H4 `HudDrawer` close control newly targeted by the add-inventory-item-actions and bag-drawer journeys) | item-actions | REMAP-TO-TESTID |

**CSS class hooks the managed browser suite targets**（重新對應至穩定掛鉤，無主要需求文字命名這些項目，故無規格增量）：

| Hook | Bucket |
|---|---|
| `.dock-menu-item` (prefix; covers `.dock-menu-item--focused` under `#action-dock`) | REMAP-TO-TESTID |
| `.dock-menu`, `.dock-menu__outlet`, `.dock-menu__outlet-tile`, `.dock-menu__nav-sub`, `.dock-menu__plain`, `.dock-menu .dock-menu__scale`, `.dock-menu .dock-menu__skill--on`, `.dock-menu .dock-menu__token--pressed` | REMAP-TO-TESTID |
| `.dock-tab-bar__<suffix>` (prefix `dock-tab-bar`: `__badge`, `__tab--on`, `svg.dock-tab-bar__icon`) | REMAP-TO-TESTID |
| `.hint` (the command-line hint cluster naming the history-recall keys; targeted by `test_browser_input_narrative.py`) | PRESERVE-SAME-HOOK |
| `.drawer-entry`, `.header-mode`, `.meta-conn`, `.services-confirm`, `.skill-detail-pane__disabled`, `.narrative-divider` (preserved), `.inputfieldwrapper` (preserved wrapper for `inputfield`) | RETIRED-WITH-SHELL |
| `.lm_header` (legacy GoldenLayout header assertion: must NOT render) | RETIRED-WITH-SHELL |
| `.dock-menu-layout` (the removed dock pane wrapper per the remove-redundant-dock-menu-layout change: the managed suite asserts it must NOT render; no replacement selector) | RETIRED-WITH-SHELL |
| `.elosern-*` retired visual classes (`.elosern-narrative`, `.elosern-placeholder`, `.elosern-header`, `.elosern-status`, `.elosern-action-dock`) — the managed suite asserts they no longer render on the Vue shell | RETIRED-WITH-SHELL |
| `messagewindow` (the retired `default_out` fallback host; revealed on demand by `test_vue_foundation.py`) | RETIRED-WITH-SHELL |

**超出主架構範圍（測試架構以 Django 算繪的頁面為目標）：** 受管測試架構透過 `#id_username` / `#id_password` 登入（`web/tests/browser/browser_helpers.py:105-112`）。這些選取的是 Evennia 原廠登入表單，非 Vue 主架構所擁有，因此登入目標維持有效，無保留／重新對應決策。

**範本與掛載契約**（於 H6 更新；除上述項目外無規格增量）：

| Contract | Bucket |
|---|---|
| `base.html` 提供建置後的 Vite 組合包（`web/static/webclient/app/dist`）— jQuery、GoldenLayout 與外掛腳本載入已在 C4 切換時移除；階段透過 `main.js` 掛載 | RETIRED-WITH-SHELL |
| `evennia.js` 傳輸層與 `Evennia.*` 全域變數（`sendInputField`、`connection`、`.msg`）由橋接器保留 | PRESERVE-VIA-BRIDGE |

**H6 驗證（工作 3.4）：** `window.Elosern.*` 公開 façade 介面（§1 `frozen-facade-surface` JSON — `Protocol`、`KeyboardRouter`、`narrativeInput`、`actions`）與鍵盤路由器宣告契約（C2 在 `webclient-pointer-activation` 中的重新表述）在 H1 至 H5 重設計中**維持不變**：重設計為現有傳輸層之上的檢視層變更，因此 §1 中的凍結成員清單維持為約束性介面，且鍵盤路由器消耗契約（`routeKeyboard` 宣告規則、強制回應擷取搶佔）由橋接器完整承載。

### 2.4 Layout-persistence keys

| Key / constant | Decider | Bucket | Evidence | Rationale |
|---|---|---|---|---|
| `elosern.layout` (localStorage) + `CURRENT_LAYOUT_VERSION = 1` + wrapper shape `{layout_version, dimensions, tabs, preferences}` | — | PRESERVE-VIA-BRIDGE | `js/elosern/layout_store.js:25-33`; `webclient-desktop-shell:222-235` (“Browser persistence is versioned and presentation-only”); `test_browser_layout.py:25-34` | 保留的 `LayoutStore` 模組維持為持久化擁有者（C1 的 store 消費它）；文字具實作中立性 |
| `STOCK_KEYS` = `["evenniaGoldenLayoutSavedState", "evenniaGoldenLayoutSavedStateName"]` | — | PRESERVE-VIA-BRIDGE | `layout_store.js:28-31`; spec scenario “Stock layout state is not imported” (`:233-235`) | 版本 1 仍不得匯入原廠索引鍵；常數在保留模組中存續 |
| `REQUIRED_COMPONENTS` = header, narrative, art, status, local-map, action-dock, command-drawer; `PREFERENCE_TYPES` = `text2html`, `fontScale`; `MAX_STORAGE_BYTES = 2048`; dimension/font-scale bounds | — | PRESERVE-VIA-BRIDGE | `layout_store.js:33-53`; `webclient-desktop-shell:8` (required-component list) | 必要外觀集合亦為 Vue 主架構的集合（路線圖 §5 B 波次）；`command-drawer` 對應至 GL 設定 id `inputComponent`（`layout_store.js:104`） |
| Migration/reset rule (known versions migrate explicitly; unknown/malformed/oversized/stock reset to the version-1 default) | — | PRESERVE-VIA-BRIDGE | `layout_store.js:344-359,440-447`; `test_browser_layout.py:56-120` (incl. `elosern.migration-probe`) | 行為獲得保留；C4 在 Vue 主架構下維持相同的 `LayoutStore` |
| `elosern.sync_recovery_reload` (sessionStorage recovery marker) | C2 | PRESERVE-VIA-BRIDGE | `js/plugins/elosern_state.js:314`; `webclient-desktop-shell:262-283`, `webclient-oob-protocol:173`; `test_browser_session_lifecycle.py` | 單次重新載入同步復原機制隨狀態擁有者透過橋接器保留 |

### 2.5 Input path (typed command flow)

| Contract | Decider | Bucket | Evidence | Rationale |
|---|---|---|---|---|
| Drawer default-closed; entry button a real `<button type="button">` with accessible name + `aria-expanded`; `/` toggle | C4 | PRESERVE-SAME-HOOK | `goldenlayout.js:385-391,446-457`; spec `webclient-desktop-shell:136-167` (behavioral wording, no id) | Vue 抽屜實作相同的行為契約；進入按鈕掛鉤位於 §2.3 重新對應表格中 |
| Enter sends exactly one ordinary text message via the transport; Shift+Enter newline; focus retention; borrowed-drawer release rules | C4 | PRESERVE-VIA-BRIDGE | `goldenlayout.js:459-489` (`sendCommand` → `Evennia.sendInputField`); spec `webclient-desktop-shell:136-218` | 實作中立文字；Vue 輸入透過相同的傳輸文字路徑路由 |
| Slash-as-text in focused editables (drawer field, creation forms, rest forms) | C2 | DELTA | spec `webclient-desktop-shell:96-98,129-133`; key path `js/plugins/elosern_ui.js:20-28,204-219` | 橋接器按鍵宣告契約的一部份；由項目 C2-02 的重新表述所涵蓋 |
| One echo per dispatched mutation / typed send, via `CommandEcho.commandLine` → `narrativeInput.appendInput` (echo never affects the wire payload) | C2 | PRESERVE-VIA-BRIDGE | `js/elosern/command_echo.js`; `js/plugins/elosern_actions.js:286-338`; specs `webclient-input-narrative:11-88`, `webclient-desktop-shell:285-318` | 兩個 façade 皆於 §1 凍結；`CommandEcho` 為保留的 UMD 邏輯，由橋接器／應用程式匯入 |

### 2.6 Test-harness globals (injected, not product surface)

| Global | Decider | Bucket | Evidence |
|---|---|---|---|
| `window.__elosernWs` (OOB capture wrapper) | C4 | HARNESS-REMAP | `web/tests/browser/browser_base.py` (`_WS_CAPTURE_SCRIPT`) |
| `window.__elosernSent` (outbound recorder) + helpers `sent_action_count`, `store_state`, `fresh_epoch`, `snapshot_envelope`, `valid_status_panel`, `guard_local_only` | C4 | HARNESS-REMAP | `web/tests/browser/browser_helpers.py` |
| Adjacent-façade drives (`Elosern.StateController.getState/requestResync`, `Elosern.goldenlayout.onText/getGL`, `Elosern.explorationDock.*`, `Elosern.serviceDock.*`, `Elosern.creationDock.*`, `Elosern._combat.*`) | C4 | HARNESS-REMAP | `test_browser_input_narrative.py:162,212,238,445,556-558`, `test_browser_creation.py:711-712,1019-1023`, `test_browser_services.py:332-336,378-380`, `test_browser_exploration.py:403-416`, `test_browser_reconnect.py:184,334-336`, `test_browser_combat.py:426-443` |
| `BROWSER_ACCOUNT`, `ELOSERN_BROWSER_EXPLORATION`, default viewport 1440x900 / 1280x720 | C4 | HARNESS-REMAP | `browser_helpers.py`, `browser_base.py` | 非客戶端契約；C4 的測試架構重新導向維持這些不變量 |

---

## 3. Delta list (MODIFIED / RENAMED)

完整的 `MODIFIED`/`RENAMED` 增量集合。每個項目皆指明受影響的主規格需求（能力名稱與需求標題，截至 A1）、套用變更、給套用變更的指示，以及理由。項目互不重疊：沒有任何 `(capability, requirement)` 配對出現兩次。套用變更在自身的實作期間撰寫確切的重新表述，並在同一個變更中重新指向該需求的追溯性測試（C2 設計 D2）。所有在遷移過程中文字維持為真的需求**未**列於此處（已在 §2 分類為保留）。

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

項目附註：

- **C2-01 至 C2-03** 為橋接契約重新表述。橋接器（C2）帶有建立各重新表述契約的測試（在 `KeyboardRouter` 模組上斷言按鍵路徑、單一進入點 `narrativeInput`/`actions`、無外掛參與），因此每個重新表述的需求在 C2 封存時皆具備通過的測試（C2 設計 D2）。
- **C4-01、C4-02、C4-03** 為切換時編輯，於正式切換時套用，此時主規格在封存時對 Vue 桌面主架構為真（路線圖 §5 C4：「`webclient-desktop-shell` 從 GoldenLayout 主架構更名為 Vue SPA 桌面主架構」）。C4-03 的敘事標記修正隨 C4 落地（而非 C2），因為其停止命名的內建外掛在切換前仍留存在舊版載入路徑中。C4 亦在同一個變更中執行 §2.3 重新對應決策，並將其餘 Playwright 行為切片重新對應至保留掛鉤與 `data-testid`。
- 無其他 `webclient-*` 需求文字失效：其餘所有綁定實作的識別碼皆分類為保留（§2）— 四個 façade 透過橋接器存續，DOM 契約掛鉤獲得保留，版面配置持久化契約由保留的 `LayoutStore` 擁有，且敘事／回顯／傳輸行為具實作中立性。

---

## 4. 參考資料（資訊性，不受遷移影響）

- **OOB 信封**（客戶端驗證名稱，`PROTOCOL_VERSION = 1`）：`ui_sync`、`ui_action`、`ui_snapshot`、`ui_update`、`ui_action_result`、`ui_protocol_error`、`connection_open`（`js/elosern/protocol.js`；規格 `webclient-oob-protocol:8`）。伺服器端形狀不受遷移影響（路線圖 §2 非目標）。
- **伺服器端動作允許清單**（透過 `actions.submit` 分派；客戶端絕不設允許清單）：`explore.look`、`explore.move`、`explore.talk_scripted`、`explore.talk_freeform`、`explore.examine`、`explore.ask`、`explore.query`、`explore.interact`、`explore.pick`、`explore.drop`、`explore.engage`、`explore.wait`、`explore.party_invite`、`explore.party_leave`、`explore.character`、`explore.guild`、`explore.guild.quest_accept`、`explore.guild.quest_turnin`、`explore.guild.quest_abandon`、`creation.preset_selected`、`creation.custom_filled`、`creation.concept_filled`、`creation.activate_player`、`creation.exploration`、`creation.reset`、`combat.basic_attack`、`combat.cast`、`combat.attack_entity`、`combat.attack_allies`、`combat.attack_all_enemies`、`combat.flee`、`combat.forfeit`、`guild.register`、`guild.quest_accept`、`guild.quest_abandon`、`guild.quest_turnin`、`guild.exam_start`、`shop.buy`、`shop.sell`、`options.dismiss`（規格 `webclient-action-dispatch:30-50`）。
- **測試控管不變量**（不受遷移影響）：每次呼叫皆為隔離的受管 Evennia 執行期、僅限本機請求、確定性 fixtures、`BROWSER_ACCOUNT`、1440x900 主要／1280x720 最小視埠（規格 `webclient-browser-verification:19-38`）。

---

## 5. 完整性聲明

- 清點方式為 grep 驅動（A1 設計 D2）：涵蓋 `openspec/specs/webclient-*/spec.md`、`web/tests/browser/`、`web/static/webclient/js/` 與 `web/templates/webclient/` 中的 `window.Elosern.`、`onKeydown`、`web/tests/browser/` 與鍵盤路由器中的 `getElementById` / `#` id 選取器，以及版面配置持久化索引鍵。
- 所發現的每個實作綁定識別碼皆恰好落入單一 §2 列（單一分組）。四個凍結的 façade 及其成員詳盡列於 §1（機械式衍生）。
- 每個文字綁定至停用實作的主規格需求皆恰好出現在單一 §3 增量項目中；其他所有需求皆分類為保留。C2 在切換前對照 Playwright 套件重新檢查此網（C2 風險章節）；C2 發現的任何遺漏皆修正回本文件（路線圖 §9 優先順序）。

---

## 6. 修訂記錄

### A1.1 — 2026-08-20（封存後，同步 rubber-duck 審查）

- **§2.3 完整性：** 五個遺漏的受管瀏覽器目標群組被加入為 `REMAP-TO-TESTID` 列 — `creation-concept-submit` / `creation-form-message` / `creation-race-<i>`（創角 dock）、`exploration-detail`（元素與類別），以及 `services-quantity` / `services-quantity-value`（服務 dock）。測試架構登入選取器（`#id_username`、`#id_password`）被記錄為超出主架構範圍：它們以 Django 算繪的登入頁面為目標，切換不影響該處。`tests/test_webclient_frozen_contract.py` 現從 `web/tests/browser/` 擷取每個 `getElementById` / `#id` 目標，並在未被 §2 列（或明確豁免）涵蓋時判定失敗，防止此類遺漏再次發生。
- **C2-04 → C4-03 重新指派：** `webclient-narrative-markup` 增量現指明 `webclient-vue-10-wire-views-browser` 為其套用變更。其停止命名的內建外掛在 C2 至 C4 的不可部分變更切換前（C4 工作 1.1）仍留存在舊版載入路徑中，因此主規格必須持續描述它們直到該行為消失的確切時刻。C4 變更的工件在同一修訂版本中更新（其 `webclient-narrative-markup` 增量規格、切換工作與 D2 掛鉤文字現逐列引用本審查）。
- **C4-01 `rename_to` 修正**為 `The WebClient loads a local Vue SPA desktop shell`，即 C4 增量規格與路線圖使用的確切目標名稱（A1.0 文字將字詞順序顛倒）。
