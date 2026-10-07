<script setup>
// The LLM call payload drawer (gm-portal-s2b-dashboard): a modal side sheet
// on the native <dialog> (showModal gives an inert background, Esc and the
// top layer). It fetches /gm/api/llm/calls/<id> only when a call is
// selected; a later selection always wins over an earlier, slower response.
// Payload text is untrusted and rendered through interpolation only.
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import GmCodeBlock from "./GmCodeBlock.vue";
import GmEmpty from "./GmEmpty.vue";
import GmError from "./GmError.vue";
import GmStatusBadge from "./GmStatusBadge.vue";
import { formatClock, formatMs } from "../lib/format.js";
import { attemptErrors, attemptFailed, messageGroups, resultBadge } from "../lib/dashboard.js";

const props = defineProps({
  callId: { type: String, default: null },
  api: { type: Object, required: true },
  // Where focus goes on close when the opener left the DOM (a poll removed
  // its row): a CSS selector, typically the recent-calls panel heading.
  fallbackFocus: { type: String, default: "" },
});

const emit = defineEmits(["close"]);

const dialog = ref(null);
const heading = ref(null);
const state = ref({ status: "idle", data: null, error: null });
const activeTab = ref(0);
const tabRefs = ref([]);
let token = 0;
let opener = null;
let opened = false;
let pressedOnBackdrop = false;

const EMPTY_STATES = {
  transcript_not_found: {
    title: "紀錄已過期",
    message: "這筆呼叫的 transcript 已輪替清除或尚未寫入。",
  },
  transcript_disabled: {
    title: "未啟用 transcript",
    message: "伺服器目前不保存 LLM 呼叫內容；啟用後的新呼叫才能檢視。",
  },
};

async function load(callId) {
  const mine = ++token;
  state.value = { status: "loading", data: null, error: null };
  activeTab.value = 0;
  try {
    const data = await props.api.get(`/llm/calls/${callId}`);
    if (mine === token) state.value = { status: "ready", data, error: null };
  } catch (error) {
    if (mine === token) state.value = { status: "error", data: null, error };
  }
}

function open() {
  const element = dialog.value;
  if (!element) return;
  if (!element.open) {
    opened = true;
    opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    if (typeof element.showModal === "function") element.showModal();
    else element.setAttribute("open", "");
  }
  document.documentElement.classList.add("gm-scroll-locked");
  nextTick(() => heading.value?.focus());
}

function shut() {
  // Only a drawer that actually opened restores focus or releases the lock.
  if (!opened) return;
  opened = false;
  const element = dialog.value;
  if (element?.open) {
    if (typeof element.close === "function") element.close();
    else element.removeAttribute("open");
  }
  document.documentElement.classList.remove("gm-scroll-locked");
  let target = opener?.isConnected ? opener : null;
  if (!target && props.fallbackFocus) {
    target = document.querySelector(props.fallbackFocus);
    // A heading is not focusable by default; make it a programmatic target.
    if (target && !target.hasAttribute("tabindex")) target.setAttribute("tabindex", "-1");
  }
  opener = null;
  if (target && typeof target.focus === "function") target.focus();
}

watch(
  () => props.callId,
  (callId) => {
    if (callId) {
      load(callId);
      nextTick(open);
    } else {
      token += 1;
      shut();
    }
  },
  { immediate: true },
);

onBeforeUnmount(shut);

function requestClose() {
  emit("close");
}

function onCancel(event) {
  event.preventDefault();
  requestClose();
}

function onKeydown(event) {
  if (event.key === "Escape") {
    event.preventDefault();
    requestClose();
  }
}

// Close on a backdrop click only when the press also started there, so a
// text selection dragged out of the sheet does not dismiss it.
function onPointerDown(event) {
  pressedOnBackdrop = event.target === dialog.value;
}

function onBackdrop(event) {
  if (event.target === dialog.value && pressedOnBackdrop) requestClose();
  pressedOnBackdrop = false;
}

const outcome = computed(() => state.value.data?.outcome ?? null);
const exchanges = computed(() => state.value.data?.exchanges ?? []);
const badge = computed(() => resultBadge(outcome.value?.result));
const emptyState = computed(() => EMPTY_STATES[state.value.error?.code] ?? null);
const fullJson = computed(() => state.value.data ?? {});

const tabs = computed(() =>
  exchanges.value.map((exchange, index) => {
    const failed = attemptFailed(exchange, outcome.value);
    return {
      index,
      id: `gm-call-tab-${index}`,
      panel: `gm-call-panel-${index}`,
      label: `第 ${(exchange.attempt ?? index) + 1} 次`,
      verdict: failed ? "失敗" : "成功",
      failed,
      exchange,
      groups: messageGroups(exchange.request?.messages ?? []),
      params: withoutMessages(exchange.request),
      errors: attemptErrors(exchange, outcome.value),
    };
  }),
);

function withoutMessages(request) {
  if (!request || typeof request !== "object") return null;
  const { messages, ...rest } = request;
  return Object.keys(rest).length ? rest : null;
}

function selectTab(index, focus = false) {
  activeTab.value = index;
  if (focus) nextTick(() => tabRefs.value[index]?.focus());
}

function onTabKeydown(event, index) {
  const last = tabs.value.length - 1;
  const moves = { ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: last };
  if (!(event.key in moves)) return;
  event.preventDefault();
  let next = moves[event.key];
  if (next > last) next = 0;
  if (next < 0) next = last;
  selectTab(next, true);
}

// ISO record timestamp -> local "MM/DD HH:mm:ss"; unparseable stays verbatim.
function stamp(iso) {
  const parsed = Date.parse(iso);
  if (Number.isNaN(parsed)) return iso ?? "—";
  const date = new Date(parsed);
  const day = `${String(date.getMonth() + 1).padStart(2, "0")}/${String(date.getDate()).padStart(2, "0")}`;
  return `${day} ${formatClock(parsed / 1000)}`;
}

function exchangeMeta(exchange) {
  return [
    exchange.profile,
    exchange.endpoint_host,
    exchange.status != null ? `HTTP ${exchange.status}` : "無 HTTP 狀態",
    formatMs(exchange.ms),
  ]
    .filter(Boolean)
    .join(" · ");
}
</script>

<template>
  <dialog
    ref="dialog"
    class="gm-call-drawer"
    aria-labelledby="gm-call-drawer-title"
    @cancel="onCancel"
    @keydown="onKeydown"
    @pointerdown="onPointerDown"
    @click="onBackdrop"
  >
    <div class="gm-call-drawer__sheet">
      <header class="gm-call-drawer__header">
        <div class="gm-call-drawer__heading">
          <h2 id="gm-call-drawer-title" ref="heading" class="gm-call-drawer__title" tabindex="-1">
            LLM 呼叫明細
          </h2>
          <p class="gm-call-drawer__id">
            <span class="gm-call-drawer__id-label">識別碼</span>
            <code>{{ callId }}</code>
          </p>
        </div>
        <div class="gm-call-drawer__actions">
          <GmCodeBlock v-if="state.status === 'ready'" copy-only :text="fullJson" copy-label="複製全部 JSON" />
          <button type="button" class="ui-icon-btn" aria-label="關閉明細" @click="requestClose">✕</button>
        </div>
      </header>

      <div class="gm-call-drawer__body">
        <div v-if="state.status === 'loading'" class="gm-call-drawer__loading" aria-hidden="true">
          <span v-for="width in ['46%', '72%', '58%', '88%', '40%']" :key="width" class="gm-skeleton" :style="{ width }"></span>
        </div>
        <p v-if="state.status === 'loading'" class="gm-visually-hidden" role="status">載入明細中…</p>

        <template v-else-if="state.status === 'error'">
          <GmEmpty v-if="emptyState" :title="emptyState.title" :message="emptyState.message">
            <template #actions><code class="gm-call-drawer__code">{{ state.error.code }}</code></template>
          </GmEmpty>
          <GmError
            v-else
            :title="state.error?.code === 'invalid_call_id' ? '呼叫識別碼格式不正確' : '無法載入明細'"
            :message="state.error?.message"
            :code="state.error?.code"
          >
            <template v-if="state.error?.code !== 'invalid_call_id'" #actions>
              <button type="button" class="ui-btn ui-btn--sm" @click="load(callId)">重試</button>
            </template>
          </GmError>
        </template>

        <template v-else-if="state.status === 'ready'">
          <section class="gm-call-drawer__section" aria-labelledby="gm-call-outcome">
            <h3 id="gm-call-outcome" class="gm-call-drawer__h3">結果</h3>
            <dl v-if="outcome" class="gm-call-drawer__ledger" data-testid="gm-call-outcome">
              <div><dt>時間</dt><dd><time :datetime="outcome.ts" :title="outcome.ts" class="gm-mono">{{ stamp(outcome.ts) }}</time></dd></div>
              <div><dt>層</dt><dd class="gm-mono">{{ outcome.layer }}</dd></div>
              <div><dt>設定檔</dt><dd class="gm-mono">{{ outcome.profile }}</dd></div>
              <div><dt>結果</dt><dd><GmStatusBadge :status="badge.status" :label="badge.label" /></dd></div>
              <div><dt>原因</dt><dd class="gm-mono">{{ outcome.reason ?? "—" }}</dd></div>
              <div><dt>耗時</dt><dd class="gm-mono">{{ formatMs(outcome.ms) }}</dd></div>
              <div><dt>嘗試次數</dt><dd class="gm-mono">{{ outcome.attempts?.length ?? 0 }}</dd></div>
            </dl>
            <p v-else class="gm-call-drawer__notice" data-testid="gm-call-no-outcome">
              <span aria-hidden="true">▲</span>
              沒有結果紀錄：此呼叫只留下請求往返，可能仍在進行，或在寫入結果前中斷。
            </p>
            <GmCodeBlock
              v-if="outcome?.final_text"
              label="最終輸出"
              :text="outcome.final_text"
              :max-lines="12"
            />
          </section>

          <section v-if="tabs.length" class="gm-call-drawer__section" aria-labelledby="gm-call-attempts">
            <h3 id="gm-call-attempts" class="gm-call-drawer__h3">各次嘗試</h3>
            <div class="ui-tabs" role="tablist" aria-label="各次嘗試">
              <button
                v-for="tab in tabs"
                :id="tab.id"
                :key="tab.id"
                :ref="(element) => (tabRefs[tab.index] = element)"
                type="button"
                role="tab"
                class="ui-tabs__tab"
                :class="{ 'is-active': activeTab === tab.index }"
                :aria-selected="activeTab === tab.index ? 'true' : 'false'"
                :aria-controls="tab.panel"
                :tabindex="activeTab === tab.index ? 0 : -1"
                @click="selectTab(tab.index)"
                @keydown="onTabKeydown($event, tab.index)"
              >
                {{ tab.label }}<span class="gm-call-drawer__verdict" :class="{ 'is-failed': tab.failed }"> · {{ tab.verdict }}</span>
              </button>
            </div>
            <div
              v-for="tab in tabs"
              v-show="activeTab === tab.index"
              :id="tab.panel"
              :key="tab.panel"
              role="tabpanel"
              class="gm-call-drawer__panel"
              :aria-labelledby="tab.id"
              tabindex="0"
              :data-testid="`gm-call-attempt-${tab.index}`"
            >
              <p class="gm-call-drawer__meta gm-mono">{{ exchangeMeta(tab.exchange) }}</p>

              <h4 class="gm-call-drawer__h4">請求訊息</h4>
              <details v-for="group in tab.groups" :key="group.role" class="gm-call-drawer__group" open>
                <summary>{{ group.label }} <span class="gm-mono">{{ group.role }}</span>（{{ group.items.length }}）</summary>
                <div class="gm-call-drawer__messages">
                  <div v-for="item in group.items" :key="item.index" class="gm-call-drawer__message" :data-role="group.role">
                    <span class="gm-call-drawer__index gm-mono">#{{ item.index }}</span>
                    <GmCodeBlock :text="item.content" :max-lines="16" />
                  </div>
                </div>
              </details>
              <p v-if="!tab.groups.length" class="gm-call-drawer__muted">此次請求沒有訊息內容</p>
              <details v-if="tab.params" class="gm-call-drawer__group">
                <summary>其他參數</summary>
                <GmCodeBlock :text="tab.params" :max-lines="20" />
              </details>

              <h4 class="gm-call-drawer__h4">回應</h4>
              <GmError
                v-if="tab.exchange.error"
                class="gm-call-drawer__request-error"
                title="請求失敗"
                :message="`${tab.exchange.error.type}：${tab.exchange.error.message ?? '（訊息未記錄）'}`"
              />
              <GmCodeBlock v-if="tab.exchange.response != null" :text="tab.exchange.response" :max-lines="20" />
              <p v-else class="gm-call-drawer__muted">沒有回應內容</p>

              <h4 class="gm-call-drawer__h4">驗證錯誤</h4>
              <ul v-if="tab.errors.length" class="gm-call-drawer__errors">
                <li v-for="(message, index) in tab.errors" :key="index">
                  <span aria-hidden="true">✕</span><span class="gm-mono">{{ message }}</span>
                </li>
              </ul>
              <p v-else class="gm-call-drawer__muted">此次嘗試沒有驗證錯誤</p>

              <div class="gm-call-drawer__copy-attempt">
                <GmCodeBlock copy-only :text="tab.exchange" copy-label="複製此次嘗試 JSON" />
              </div>
            </div>
          </section>
          <p v-else class="gm-call-drawer__muted" data-testid="gm-call-outcome-only">
            此呼叫沒有送出實際請求（假後端或已停用），只有結果紀錄。
          </p>
        </template>
      </div>
    </div>
  </dialog>
</template>

<style scoped>
.gm-call-drawer {
  position: fixed;
  inset: 0 0 0 auto;
  width: clamp(560px, 56vw, 960px);
  max-width: 100vw;
  height: 100dvh;
  max-height: 100dvh;
  margin: 0;
  padding: 0;
  color: var(--paper-200);
  background: var(--panel-solid);
  border: 0;
  border-left: 1px solid var(--band-edge);
  box-shadow: var(--shadow-lg);
  font-family: var(--f-sans);
  font-size: var(--text-md);
  line-height: 1.6;
}

.gm-call-drawer[open] {
  animation: gm-drawer-in var(--motion-base) var(--ease-enter);
}

.gm-call-drawer::backdrop {
  background: color-mix(in srgb, var(--ink-950) 70%, transparent);
  animation: gm-backdrop-in var(--motion-base) var(--ease-enter);
}

@keyframes gm-drawer-in {
  from {
    opacity: 0;
    transform: translateX(var(--motion-shift-lg, 24px));
  }
}

@keyframes gm-backdrop-in {
  from {
    opacity: 0;
  }
}

@media (max-width: 759px) {
  .gm-call-drawer {
    width: 100vw;
  }
}

.gm-call-drawer__sheet {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.gm-call-drawer__header {
  position: sticky;
  top: 0;
  z-index: 1;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sp-4);
  padding: var(--sp-5) var(--sp-6) var(--sp-4);
  background: var(--panel-solid);
  border-bottom: 1px solid var(--band-edge-dim);
}

.gm-call-drawer__heading {
  min-width: 0;
}

.gm-call-drawer__title {
  font-family: var(--f-serif);
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--paper-50);
  outline: none;
}

/* The heading receives programmatic focus on open (tabindex -1, never a tab
   stop); it needs no ring of its own. */
.gm-call-drawer__title:focus,
.gm-call-drawer__title:focus-visible {
  box-shadow: none;
  outline: none;
}

.gm-call-drawer__id {
  display: flex;
  align-items: baseline;
  gap: var(--sp-2);
  margin-top: var(--sp-1);
  min-width: 0;
}

.gm-call-drawer__id-label {
  flex: none;
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-call-drawer__id code {
  overflow: hidden;
  font-size: var(--text-sm);
  color: var(--gold-400);
  text-overflow: ellipsis;
  white-space: nowrap;
  user-select: all;
}

.gm-call-drawer__actions {
  display: flex;
  flex: none;
  align-items: center;
  gap: var(--sp-2);
}

.gm-call-drawer__copy-attempt {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--sp-2);
}

.gm-call-drawer__body {
  display: grid;
  gap: var(--sp-6);
  padding: var(--sp-5) var(--sp-6) var(--sp-8);
  overflow-y: auto;
}

.gm-call-drawer__loading {
  display: grid;
  gap: var(--sp-3);
}

.gm-call-drawer__section {
  display: grid;
  gap: var(--sp-3);
  min-width: 0;
}

.gm-call-drawer__h3 {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  font-family: var(--f-serif);
  font-size: var(--text-md);
  font-weight: 600;
  color: var(--paper-100);
}

.gm-call-drawer__h3::after {
  content: "";
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, var(--band-edge-dim), transparent);
}

.gm-call-drawer__h4 {
  margin-top: var(--sp-3);
  font-size: var(--text-xs);
  font-weight: 600;
  letter-spacing: 0.12em;
  color: var(--paper-400);
}

.gm-call-drawer__ledger {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: var(--sp-3) var(--sp-5);
  padding: var(--sp-4);
  background: var(--ink-860);
  border: var(--line);
  border-radius: var(--radius);
}

.gm-call-drawer__ledger dt {
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-call-drawer__ledger dd {
  min-width: 0;
  overflow-wrap: anywhere;
  font-size: var(--text-sm);
  color: var(--paper-100);
}

.gm-call-drawer__notice {
  padding: var(--sp-3) var(--sp-4);
  font-size: var(--text-sm);
  color: var(--paper-200);
  background: color-mix(in srgb, var(--warn) 6%, var(--ink-860));
  border-left: 3px dashed var(--warn);
  border-radius: var(--radius-sm);
}

.gm-call-drawer__notice span {
  color: var(--warn);
}

.gm-call-drawer__verdict {
  font-weight: 400;
  color: var(--paper-500);
}

.gm-call-drawer__verdict.is-failed {
  color: var(--warn);
}

.gm-call-drawer__panel {
  display: grid;
  gap: var(--sp-2);
  min-width: 0;
  outline: none;
}

.gm-call-drawer__meta {
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-call-drawer__group {
  padding: var(--sp-2) var(--sp-3);
  background: var(--ink-860);
  border: 1px solid var(--ink-700);
  border-radius: var(--radius-sm);
}

.gm-call-drawer__group summary {
  cursor: pointer;
  font-size: var(--text-sm);
  color: var(--paper-200);
}

.gm-call-drawer__group summary .gm-mono {
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-call-drawer__messages {
  display: grid;
  gap: var(--sp-3);
  margin-top: var(--sp-2);
}

.gm-call-drawer__message {
  display: grid;
  grid-template-columns: 3ch minmax(0, 1fr);
  gap: var(--sp-2);
  align-items: start;
}

.gm-call-drawer__index {
  padding-top: var(--sp-3);
  font-size: var(--text-xs);
  color: var(--gold-400);
}

.gm-call-drawer__message[data-role="system"] .gm-call-drawer__index {
  color: var(--paper-400);
}

.gm-call-drawer__muted {
  font-size: var(--text-sm);
  color: var(--paper-500);
}

.gm-call-drawer__errors {
  display: grid;
  gap: var(--sp-1);
  padding: 0;
  list-style: none;
}

.gm-call-drawer__errors li {
  display: flex;
  gap: var(--sp-2);
  font-size: var(--text-sm);
  color: var(--paper-200);
}

.gm-call-drawer__errors li > span:first-child {
  color: var(--crit);
}

.gm-call-drawer__request-error {
  padding: var(--sp-3);
}

.gm-call-drawer__code {
  padding: 2px var(--sp-2);
  font-size: var(--text-sm);
  background: var(--ink-950);
  border: var(--line);
  border-radius: var(--radius-sm);
}

@media (prefers-reduced-motion: reduce) {
  .gm-call-drawer[open],
  .gm-call-drawer::backdrop {
    animation: none;
  }
}
</style>
