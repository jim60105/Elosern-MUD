# remove-creation-overlay-close-control — Design

## Context

現況查證（`CreationOverlay.vue`）：

- `:51` `const emit = defineEmits(["action", "close", "request-reset", "cancel-confirm"]);`
- `:533-535` `function close() { emit("close"); }`
- `:607-615` header 內的 `<button class="ui-btn ui-btn--ghost ui-btn--sm creation-overlay__close" data-testid="creation-overlay-close" @click="close">✕ 關閉</button>`

消費端查證（`AppClient.vue:990-1001`）：掛載 `<CreationOverlay>` 時綁定 `:creation`／`:result`／`:stage`／`:dispatch`／`:dispatch-state`／`:push-toast` 與 `@action`／`@request-reset`／`@cancel-confirm`——**沒有 `@close`**。`close` 事件送出後無人接收，這顆按鈕自 `baa4788`（B5 overlays family）引入起就沒接過線。

呈現所有權查證：overlay 的掛載述詞是 `AppClient.vue:990` 的 `v-if="panelAvailable('creation')"`，語意與 store 的 `creationOverlayPresenting`（`stores/elosern.js:985`：`creation` 面板存在且 `available !== false`）一致，由伺服器快照擁有。創建模式下背後沒有探索 shell 可回落——`webclient-character-creation-ui` 的瀏覽器驗收契約寫明創建 dock 是創建模式的唯一 dock 擁有者，探索面只在啟用交接後才 re-render。

其他退出路徑查證：overlay 未註冊任何 `keydown` → `close` 的處理（Escape 在創建模式由 dock／keyboard router 擁有，語意是「彈出一層選單」，不是關閉 overlay）。所以關閉出口只有這一顆按鈕。

既有契約：`webclient-component-showcase` 的 full-overlays requirement 已載明「The surface SHALL offer no control it does not implement, so a control with no outcome ... SHALL NOT be rendered」——雖然該句寫在 settings overlay 的段落，但正是本案的判準來源。

## Goals / Non-Goals

**Goals:**

- 移除玩家可見的無結果控制項，讓創建面不再承諾一個做不到的動作。
- 把「創建面不提供前端關閉出口」寫進 spec 並以負向測試釘住，避免下一波 chrome 重構又把按鈕加回來。
- 零行為變更：不動任何 `creation.*` 動作、store、掛載述詞、鍵盤路由。

**Non-Goals:**

- **不接 `@close`**（理由見 D1）。
- 不新增創建模式的離開／登出能力。若日後真要讓玩家從創建畫面離線，那是連線層的獨立能力（斷線／回登入畫面），需要自己的面板與伺服端語意，不該由一顆 overlay 內按鈕預先造殼。
- 不動 `open` prop（理由見 D4）。
- 不動 `OverlayHost` 的關閉控制項——那是 map／settings／help 的共用外框，那些 overlay 背後有探索 shell，關閉是合法動作；創建 overlay 不經 `OverlayHost` 掛載，兩者互不影響。

## Decisions

### D1: 移除按鈕，而不是把 `@close` 接上

「按了沒反應」的最小修法看似是在 `AppClient.vue` 補一條 `@close="..."`，但補上去要指向哪裡？創建模式下 overlay 是唯一介面：

- 指向「隱藏 overlay」→ 玩家落在空殼客戶端（無 dock、無敘事、無指令列），且下一次快照提交又會把 overlay 掛回來，等於做出一個閃爍的假關閉。
- 指向「送出某個 `creation.*` 動作」→ 動作允許清單由伺服端擁有，沒有任何「離開創建」的動作，擴充允許清單是伺服端變更，不在本範圍。
- 指向「斷線／登出」→ 是真正的能力，但語意遠超過一顆標著「關閉」的按鈕，且需要確認流（未存草稿的處置），屬獨立提案。

三條路都不是「修好這顆按鈕」，而是「造一個新能力」。既有 showcase 契約既已規定無結果的控制項不得渲染，移除是唯一與契約一致且不擴張範圍的解。

### D2: 契約落點選 `webclient-component-showcase`，不新增 requirement

兩個候選：`webclient-component-showcase`（擁有 full-overlays 完整性與「無結果控制項不得渲染」規則、也擁有釘住此案的 vitest 套件）與 `webclient-character-creation-ui`（擁有創建 dock 的鍵盤／表單行為）。選前者，理由：

1. 被翻轉的測試 `tests/overlays/deferred_surfaces_absent.test.js` 屬 overlays 家族套件，其 requirement 證據就是 `test_vue_showcase_overlays_evidence.py::test_vitest_overlays_family_suite_passes`（直接跑 `npm test -- overlays`）。契約與證據同居一條，不製造跨 spec 的間接鏈。
2. 「不渲染無結果的控制項」這句判準本來就住在這條 requirement 裡，加在同一條是延伸而非新規則。
3. **改寫既有 requirement 而非新增**：`tools/spec_traceability` 要求每條 main-spec requirement 都有 Python `@covers_requirement` 標註（現況 1195 requirements／1195 covered／0 uncovered）。新增一條 requirement 會立刻讓 traceability gate 亮紅，逼出一個為了過閘而寫的 Python 證據測試；改寫既有條目則沿用現成證據，requirement id（由標題 slug 決定）不變，標註不需要動。**因此改寫時必須保持 requirement 標題一字不動**。

不在 `webclient-character-creation-ui` 重述同一件事——兩處寫同一條契約必然漂移。

### D3: 斷言翻轉為負向，不是直接刪掉

`deferred_surfaces_absent.test.js` 現有案 `"the creation overlay renders its own testids and a labelled close control"` 斷言關閉控制項**存在**。直接刪掉那行會讓契約無人看守：這顆按鈕當初就是在一次 chrome 統一（`0c5b57b` 把 overlay 換到共用控制層）時被當成標準 overlay 外框的一部分留著的，下一波重構很可能再加回來。改為斷言 `[data-testid="creation-overlay-close"]` 不存在，並把案名改為說明意圖的形式，讓刪除的理由留在程式碼裡。

`creation_overlay.test.js` 的 `"the close button emits close"` 則是純粹測已刪除的實作，直接刪除；其意圖已由上面的負向斷言承接，不重複。

### D4: 保留 `open` prop

`open`（`:26`，預設 `true`，作為 template 的 `v-if` 守門）在移除按鈕後，於應用內確實不再有任何切換者（`AppClient` 從不傳它）。仍保留，理由：它**不是控制項**——不對玩家渲染任何可視承諾，因此不落在「無結果的控制項不得渲染」的判準內；它是 SFC 的常規掛載守門，供 story／單元測試獨立掛載使用，且有既有覆蓋（`creation_overlay.test.js` 的 `"open=false hides the overlay"`）。移除它是與本案無關的純內部重構，零玩家可見效果，不併入。

## Risks / Trade-offs

- **[showcase 覆蓋率門檻或 story 索引因刪除而失敗]** → 已查證：`component-manifest.json` 只列 `Overlays/CreationOverlay` 這個標題，story 的註冊與 id 不變；`stories/Overlays/CreationOverlay.stories.js` 全部 story 皆未點擊或引用該 testid（`click()` 步驟只用 `creation-mode-*`／`creation-field-concept`／`creation-concept-submit`）。門檻不受影響。
- **[瀏覽器驗收套件破裂]** → 已查證：`web/tests/browser/`（`browser_helpers.py:257-268`、`test_browser_creation.py:123-125,624`）只選取 `[data-testid="creation-overlay"]` 這個容器與其 `data-mode`，不碰關閉按鈕。零改動。
- **[header 版面在少一個子元素後跑版]** → `.creation-overlay__header`（SFC `<style scoped>` `:901-907`）是 `display: flex; align-items: center; justify-content: space-between`，單一子元素時等同 `flex-start`，標題維持靠左；`.creation-overlay__close` 在該 scoped 區塊（`:889-1120`，所有 `.creation-overlay__*` 版面規則所在）無對應規則——按鈕 chrome 全來自 `styles/tokens.css` 的 `.ui-btn`，本地樣式只補版面（`:916-917` 註解自述）——無孤兒 CSS 殘留。仍以 storybook 目視確認一次。
- **[玩家把「沒有關閉鈕」當成卡住]** → 本來按了就沒反應，移除後至少不再誤導。創建流程的正當出口是完成啟用（`creation.activate`）或重設草稿（`creation.reset`），兩者都已在畫面上；本變更不改變任何一條。
- **[取捨] 這是一次減法，沒有補上替代能力** → 有意為之。專案尚未發布、0 名線上玩家，且創建模式的「離開」在伺服端根本沒有對應動作；先把假承諾拿掉，真正需要時再以獨立提案設計完整的離線／登出流程。

## Open Questions

### 這個 overlay 該不該繼續宣稱自己是 `role="dialog" aria-modal="true"`？

`CreationOverlay.vue:598-599` 標了 `role="dialog"` 與 `aria-modal="true"`，而本變更之後，這個 dialog 將**完全沒有任何關閉路徑**（按鈕移除、無 Escape 處理、無 scrim）。`aria-modal` 對輔助科技的意涵是「背後內容 inert、這是一層可退出的離散圖層」，螢幕閱讀器使用者慣例上會預期 Escape 或某個可操作的出口。

本變更**刻意不處理**，理由：這是**既有**問題而非本變更造成的——按鈕原本就 emit 到無人接收的監聽器，鍵盤／螢幕閱讀器使用者在變更前同樣沒有任何**實際**出口，只有一個可聚焦但無效果的控制項。移除它不減少任何真實能力，只是拿掉假承諾。把 ARIA 語意一併改掉會擴張範圍、超出單日規模。

**建議的後續獨立提案**：重新評估「整個模式所擁有的全視窗表面、且刻意沒有關閉路徑」是否該用 dialog 模式描述——很可能該拿掉 `role="dialog"`／`aria-modal="true"`（它不是可關閉的對話框，而是當前模式的主畫面本身），或改用更貼切的 landmark 語意。此問題在本變更落地後**不會消失也不會惡化**，可獨立排程。

## Migration Plan

不適用。專案未發布、無線上使用者、無持久化狀態或 wire 格式涉入；變更僅刪除前端 markup 與其測試。回滾即 `git revert`。
