<script setup>
// NpcPersonaEditor (npc-persona-editor-window D1/D4/D5/D5a): the NPC author
// editor window. A passive, props-driven renderer of the editor view model
// (`use-npc-persona-editor.js`): it owns only presentation-local state (the
// dirty-close confirmation and focus routing) and emits intents — `input`
// (key, value), `save`, `close`, `reload`, `discard`, `retry`.
//
// It sits on the shared drawer frame (`HudDrawer` + `DrawerHeader` + the
// shared focus trap): a fixed dossier column carries the NPC's name, the
// state, the card's total capacity and the two standing notices, so they
// never scroll away; the form column scrolls on its own. Every text is
// rendered as plain text (interpolation only — no `v-html`), and over-budget
// input is reported, never truncated.
import { computed, nextTick, ref, watch } from "vue";
import HudDrawer from "./HudDrawer.vue";
import {
  CARD_BLOCK_LIMIT,
  CARD_FIELDS,
  GREETING_FIELD,
  IDENTITY_SECTION_LIMIT,
  LEAF_LIMIT,
  OFFLINE_GREETING_LIMIT,
} from "./npc-persona-editor-model.js";
import "./npc-persona-editor.css";

const props = defineProps({
  // The editor view model (see `use-npc-persona-editor.js` `view`).
  editor: { type: Object, required: true },
});
const emit = defineEmits(["input", "save", "close", "reload", "discard", "retry"]);

const drawerRef = ref(null);
const rootRef = ref(null);
const confirmOpen = ref(false);
const confirmKeepRef = ref(null);
const confirmDiscardRef = ref(null);
const closeNotice = ref("");
let confirmOpener = null;

const TITLE_ID = "npc-persona-editor-title";
const ed = computed(() => props.editor);
const state = computed(() => ed.value.state);
watch(state, () => { closeNotice.value = ""; });
const ready = computed(() => ed.value.baseline != null);
const validation = computed(() => ed.value.validation);

const identityFields = CARD_FIELDS.filter((field) => field.section === "identity");
const leafFields = CARD_FIELDS.filter((field) => field.section !== "identity");

const drawerTitle = computed(() => ed.value.displayName || "編輯人物設定");
const drawerSubtitle = computed(() =>
  !ready.value ? "" : ed.value.npcTitle ? `編輯人物設定 ‧ ${ed.value.npcTitle}` : "編輯人物設定",
);

function domKey(key) {
  return key.replace(/\./g, "-");
}
function fieldId(key) {
  return `npc-persona-field-${domKey(key)}`;
}

const STATUS = {
  loading: { label: "讀取中", tone: "muted" },
  ready_clean: { label: "已儲存", tone: "ok" },
  ready_dirty: { label: "尚未儲存", tone: "gold" },
  saving: { label: "儲存中", tone: "gold" },
  conflict: { label: "版本衝突", tone: "seal" },
  rejected: { label: "未通過檢查", tone: "seal" },
  unavailable: { label: "暫時無法編輯", tone: "muted" },
  closed: { label: "", tone: "muted" },
};
const status = computed(() => STATUS[state.value] || STATUS.closed);
const statusDetail = computed(() => {
  const count = (ed.value.dirtyFields || []).length;
  if (state.value === "ready_dirty" || (state.value === "rejected" && count)) {
    return `${count} 個欄位有修改`;
  }
  return "";
});

// The total-capacity ring: the rendered card total (labels and separators
// counted) against the 2,000 code-point block.
const RING_R = 42;
const RING_C = 2 * Math.PI * RING_R;
const total = computed(() => validation.value.total);
const ringRatio = computed(() => Math.min(1, total.value.used / CARD_BLOCK_LIMIT));
const ringDash = computed(() => `${(RING_C * ringRatio.value).toFixed(2)} ${RING_C.toFixed(2)}`);
const ringTone = computed(() => {
  if (total.value.over) return "over";
  if (total.value.remaining <= 200) return "near";
  return "ok";
});

function fieldReport(key) {
  return key === GREETING_FIELD.key ? validation.value.greeting : validation.value.fields[key];
}
function countTone(report) {
  if (!report) return "ok";
  if (report.over || report.multiline || report.emptyRequired) return "over";
  if (report.remaining <= Math.ceil(report.limit * 0.1)) return "near";
  return "ok";
}
function meterWidth(report) {
  if (!report) return "0%";
  return `${Math.min(100, (report.used / report.limit) * 100).toFixed(1)}%`;
}
function isChanged(key) {
  return (ed.value.dirtyFields || []).includes(key);
}
function serverError(key) {
  const rejection = ed.value.rejection;
  return rejection && rejection.field === key ? rejection.message : null;
}
function fieldError(key) {
  const report = fieldReport(key);
  return serverError(key) || (report && report.error) || null;
}
function describedBy(key) {
  const ids = [`${fieldId(key)}-hint`, `${fieldId(key)}-count`];
  if (key.startsWith("identity.") && (serverError("identity") || validation.value.identity.error)) ids.push("npc-persona-identity-error");
  if (fieldError(key)) ids.push(`${fieldId(key)}-error`);
  return ids.join(" ");
}

const editable = computed(() => ready.value && state.value !== "saving");
const generalRejection = computed(() => {
  const rejection = ed.value.rejection;
  return rejection && !rejection.field ? rejection.message : null;
});
// The local errors that name no single control (the identity-section and
// whole-card bounds) are announced politely as they appear.
const blockErrors = computed(() =>
  [validation.value.identity.error, validation.value.total.error].filter(Boolean),
);

const sectionIndex = computed(() => [
  { key: "identity.public", label: "身分" },
  ...leafFields.map((field) => ({ key: field.key, label: field.label })),
  { key: GREETING_FIELD.key, label: GREETING_FIELD.label },
]);
function indexFlag(key) {
  const keys = key === "identity.public" ? ["identity.public", "identity.hidden"] : [key];
  if (keys.some((k) => fieldError(k)) || (key === "identity.public" && validation.value.identity.over)) {
    return "error";
  }
  if (keys.some((k) => isChanged(k))) return "changed";
  return "";
}

function focusField(key) {
  const el = rootRef.value?.querySelector(`#${fieldId(key)}`);
  if (el) {
    el.focus({ preventScroll: true });
    const scroller = rootRef.value.querySelector(".npe-main");
    if (scroller) scroller.scrollTop += el.getBoundingClientRect().top - scroller.getBoundingClientRect().top - scroller.clientHeight / 2;
  }
}

watch(
  () => ed.value.focusRequest && ed.value.focusRequest.seq,
  async (seq) => {
    if (!seq) return;
    await nextTick();
    focusField(ed.value.focusRequest.field);
  },
);

function onInput(key, event) {
  emit("input", key, event.target.value);
}

function onSave() {
  if (ed.value.canSave) emit("save");
}

function onFormKeydown(event) {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
    event.preventDefault();
    onSave();
  }
}

// The dirty-close guard (design D5): Escape, the close control, the scrim,
// and 取消 all route through `closeGuard`; a dirty draft asks first.
function closeGuard() {
  if (state.value === "saving") {
    closeNotice.value = "儲存中，完成後才能關閉。";
    return false;
  }
  if (ed.value.dirty && state.value !== "closed") {
    openConfirm();
    return false;
  }
  return true;
}
async function openConfirm() {
  confirmOpener = document.activeElement;
  confirmOpen.value = true;
  await nextTick();
  confirmKeepRef.value?.focus();
}
function keepEditing() {
  confirmOpen.value = false;
  void nextTick().then(() => {
    if (confirmOpener && document.contains(confirmOpener)) confirmOpener.focus();
    else rootRef.value?.querySelector("textarea")?.focus();
  });
}
function confirmDiscard() {
  confirmOpen.value = false;
  drawerRef.value?.forceClose();
}
function onConfirmKeydown(event) {
  if (event.key === "Escape") {
    event.preventDefault();
    event.stopPropagation();
    keepEditing();
    return;
  }
  if (event.key === "Tab") {
    // The confirmation holds focus between its two buttons.
    event.preventDefault();
    event.stopPropagation();
    const next = document.activeElement === confirmKeepRef.value ? confirmDiscardRef.value : confirmKeepRef.value;
    next?.focus();
  }
}
function onCancel() {
  if (closeGuard()) drawerRef.value?.forceClose();
}

const footSummary = computed(() => {
  if (state.value === "loading") return "正在讀取……";
  if (!ready.value) return "";
  if (!validation.value.valid && ed.value.dirty) return "有欄位未通過檢查，修正後才能儲存。";
  if (ed.value.dirty) return `${dirtyCount.value} 個欄位有修改，尚未儲存。`;
  return "沒有未儲存的修改。";
});
const dirtyCount = computed(() => (ed.value.dirtyFields || []).length);
const saveLabel = computed(() => (state.value === "saving" ? "儲存中……" : "儲存設定"));
</script>

<template>
  <HudDrawer
    ref="drawerRef"
    :open="true"
    :title="drawerTitle"
    :subtitle="drawerSubtitle"
    icon="quill"
    drawer-key="npc_persona"
    :title-id="TITLE_ID"
    :close-guard="closeGuard"
    body-flush
    @close="emit('close')"
  >
    <div
      ref="rootRef"
      class="npe"
      data-testid="npc-persona-editor"
      :data-state="state"
      :data-npc-id="ed.npcId ?? ''"
    >
      <div class="npe-layout" :inert="confirmOpen || undefined">
        <!-- The dossier column: fixed, never scrolls the notices away. -->
        <aside class="npe-side" aria-label="人物與狀態">
          <div class="npe-dossier">
            <p class="npe-eyebrow">作者模式</p>
            <p class="npe-name">{{ ed.displayName || "　" }}</p>
            <p v-if="ed.npcTitle" class="npe-npc-title">{{ ed.npcTitle }}</p>
            <div class="npe-meta">
              <span v-if="ed.version != null" class="npe-version" data-testid="npc-persona-editor-version">第 {{ ed.version }} 版</span>
              <span class="npe-pill" :data-tone="status.tone" data-testid="npc-persona-editor-state-pill">
                <span class="npe-pill__dot" aria-hidden="true"></span>{{ status.label }}
              </span>
            </div>
            <p v-if="statusDetail" class="npe-status-detail">{{ statusDetail }}</p>
          </div>

          <section v-if="ready" class="npe-capacity" :data-tone="ringTone" data-testid="npc-persona-editor-total" aria-label="人物設定總容量">
            <svg class="npe-ring" viewBox="0 0 100 100" aria-hidden="true">
              <circle class="npe-ring__track" cx="50" cy="50" :r="RING_R" />
              <circle
                class="npe-ring__value"
                cx="50"
                cy="50"
                :r="RING_R"
                :stroke-dasharray="ringDash"
                transform="rotate(-90 50 50)"
              />
            </svg>
            <div class="npe-capacity__text">
              <p class="npe-capacity__figure">
                <template v-if="total.over">超出 <strong>{{ total.used - CARD_BLOCK_LIMIT }}</strong></template>
                <template v-else>剩餘 <strong>{{ total.remaining }}</strong></template>
              </p>
              <p class="npe-capacity__caption">整張設定 {{ total.used }} / {{ CARD_BLOCK_LIMIT }}</p>
              <p class="npe-capacity__caption" :data-over="validation.identity.over || undefined">
                身分區塊 {{ validation.identity.used }} / {{ IDENTITY_SECTION_LIMIT }}
              </p>
              <p class="npe-capacity__note">字數包含欄位標籤</p>
            </div>
          </section>

          <div class="npe-notices">
            <div class="npe-notice npe-notice--spoiler" role="note" data-testid="npc-persona-editor-notice-spoiler">
              <p class="npe-notice__title"><span class="npe-notice__mark" aria-hidden="true">✦</span>作者模式‧含劇透</p>
              <p class="npe-notice__body">這裡會顯示角色的隱秘身分與幕後設定。修改只影響這一位角色，不花費時間或金錢，也不會改變任何關係。</p>
            </div>
            <div class="npe-notice" role="note" data-testid="npc-persona-editor-notice-static">
              <p class="npe-notice__title"><span class="npe-notice__mark" aria-hidden="true">◇</span>對白與肖像不重新生成</p>
              <p class="npe-notice__body">既有的關鍵字對白與已生成的肖像都不會改變；新的設定會用在之後的 AI 對話。</p>
            </div>
          </div>

          <nav v-if="ready" class="npe-index" aria-label="欄位索引">
            <button
              v-for="row in sectionIndex"
              :key="row.key"
              type="button"
              class="npe-index__item"
              :data-flag="indexFlag(row.key) || undefined"
              @click="focusField(row.key)"
            >
              <span class="npe-index__dot" aria-hidden="true"></span>{{ row.label }}
              <span v-if="indexFlag(row.key) === 'error'" class="npe-visually-hidden">（有錯誤）</span>
              <span v-else-if="indexFlag(row.key) === 'changed'" class="npe-visually-hidden">（已修改）</span>
            </button>
          </nav>
        </aside>

        <!-- The form column: the only scrolling region. -->
        <div class="npe-main" @keydown="onFormKeydown">
          <div v-if="state === 'loading'" class="npe-skeleton" data-testid="npc-persona-editor-loading" aria-busy="true">
            <p class="npe-skeleton__label">正在讀取人物設定……</p>
            <div v-for="n in 4" :key="n" class="npe-skeleton__card">
              <span class="npe-skeleton__line npe-skeleton__line--short"></span>
              <span class="npe-skeleton__block"></span>
            </div>
          </div>

          <div
            v-else-if="!ready && ed.unavailable"
            class="npe-empty"
            data-testid="npc-persona-editor-unavailable"
          >
            <p class="npe-empty__mark" aria-hidden="true">◇</p>
            <p class="npe-empty__title">無法開啟人物設定</p>
            <p class="npe-empty__body">{{ ed.unavailable.message }}</p>
            <button type="button" class="npe-btn" data-testid="npc-persona-editor-retry" :disabled="ed.busy" @click="emit('retry')">重新讀取</button>
          </div>

          <template v-else>
            <div
              v-if="ed.unavailable"
              class="npe-banner npe-banner--muted"
              role="status"
              data-testid="npc-persona-editor-unavailable"
              :data-reason="ed.unavailable.kind"
            >
              <span class="npe-banner__mark" aria-hidden="true">◇</span>
              <p class="npe-banner__text">{{ ed.unavailable.message }}</p>
              <button v-if="ed.unavailable.kind === 'resync_failed'" type="button" class="npe-btn" data-testid="npc-persona-editor-retry" :disabled="ed.busy" @click="emit('retry')">重新讀取</button>
            </div>
            <div v-if="ed.conflict" class="npe-banner npe-banner--seal" data-testid="npc-persona-editor-conflict">
              <span class="npe-banner__mark" aria-hidden="true">!</span>
              <div class="npe-banner__text">
                <p class="npe-banner__title">這位角色的設定已在其他地方更新</p>
                <p>
                  {{ ed.conflict.message || `目前已是第 ${ed.conflict.version} 版。` }}
                  你的草稿仍保留在這裡，不會自動合併或覆蓋。
                </p>
              </div>
              <div class="npe-banner__actions">
                <button type="button" class="npe-btn" data-testid="npc-persona-editor-reload" :disabled="ed.busy" @click="emit('reload')">重新載入（保留草稿）</button>
                <button type="button" class="npe-btn npe-btn--ghost" data-testid="npc-persona-editor-discard" :disabled="ed.busy" @click="emit('discard')">放棄修改</button>
              </div>
            </div>
            <div v-if="generalRejection" class="npe-banner npe-banner--seal" data-testid="npc-persona-editor-rejection">
              <span class="npe-banner__mark" aria-hidden="true">!</span>
              <p class="npe-banner__text">{{ generalRejection }}　草稿已保留。</p>
            </div>

            <form class="npe-form" novalidate :aria-busy="state === 'saving' || undefined" @submit.prevent="onSave">
              <!-- Identity: public and hidden layers in one section. -->
              <fieldset id="npc-persona-field-identity" tabindex="-1" class="npe-section npe-section--identity" :data-over="validation.identity.over || undefined">
                <legend class="npe-section__legend">
                  <span class="npe-section__title">身分</span>
                  <span class="npe-section__meta" :data-tone="validation.identity.over ? 'over' : 'ok'">
                    區塊 {{ validation.identity.used }} / {{ IDENTITY_SECTION_LIMIT }}
                  </span>
                </legend>
                <div class="npe-identity">
                  <div
                    v-for="field in identityFields"
                    :key="field.key"
                    class="npe-field"
                    :data-error="fieldError(field.key) ? 'true' : undefined"
                    :data-changed="isChanged(field.key) || undefined"
                  >
                    <div class="npe-field__head">
                      <label class="npe-field__label" :for="fieldId(field.key)">{{ field.label }}</label>
                      <span class="npe-badge" :data-kind="field.required ? 'required' : 'optional'">{{ field.required ? "必填" : "選填" }}</span>
                      <span class="npe-field__count" :id="`${fieldId(field.key)}-count`" :data-tone="countTone(fieldReport(field.key))">
                        <strong>{{ fieldReport(field.key).used }}</strong> / {{ LEAF_LIMIT }}
                      </span>
                    </div>
                    <p :id="`${fieldId(field.key)}-hint`" class="npe-field__hint">{{ field.hint }}</p>
                    <textarea
                      :id="fieldId(field.key)"
                      class="npe-input"
                      :data-testid="fieldId(field.key)"
                      :value="ed.draft[field.key]"
                      :readonly="!editable || undefined"
                      :aria-required="field.required ? 'true' : undefined"
                      :aria-invalid="fieldError(field.key) ? 'true' : undefined"
                      :aria-describedby="describedBy(field.key)"
                      rows="3"
                      spellcheck="false"
                      @input="onInput(field.key, $event)"
                    ></textarea>
                    <div class="npe-meter" :data-tone="countTone(fieldReport(field.key))" aria-hidden="true">
                      <span :style="{ width: meterWidth(fieldReport(field.key)) }"></span>
                    </div>
                    <p v-if="fieldError(field.key)" :id="`${fieldId(field.key)}-error`" class="npe-field__error">{{ fieldError(field.key) }}</p>
                  </div>
                </div>
                <p v-if="serverError('identity') || validation.identity.error" id="npc-persona-identity-error" class="npe-field__error npe-section__error">{{ serverError('identity') || validation.identity.error }}</p>
              </fieldset>

              <div class="npe-grid">
                <div
                  v-for="field in leafFields"
                  :key="field.key"
                  class="npe-section npe-field"
                  :data-error="fieldError(field.key) ? 'true' : undefined"
                  :data-changed="isChanged(field.key) || undefined"
                >
                  <div class="npe-field__head">
                    <label class="npe-field__label npe-field__label--section" :for="fieldId(field.key)">{{ field.label }}</label>
                    <span class="npe-badge" :data-kind="field.required ? 'required' : 'optional'">{{ field.required ? "必填" : "選填" }}</span>
                    <span class="npe-field__count" :id="`${fieldId(field.key)}-count`" :data-tone="countTone(fieldReport(field.key))">
                      <strong>{{ fieldReport(field.key).used }}</strong> / {{ LEAF_LIMIT }}
                    </span>
                  </div>
                  <p :id="`${fieldId(field.key)}-hint`" class="npe-field__hint">{{ field.hint }}</p>
                  <textarea
                    :id="fieldId(field.key)"
                    class="npe-input"
                    :data-testid="fieldId(field.key)"
                    :value="ed.draft[field.key]"
                    :readonly="!editable || undefined"
                    :aria-required="field.required ? 'true' : undefined"
                    :aria-invalid="fieldError(field.key) ? 'true' : undefined"
                    :aria-describedby="describedBy(field.key)"
                    rows="4"
                    spellcheck="false"
                    @input="onInput(field.key, $event)"
                  ></textarea>
                  <div class="npe-meter" :data-tone="countTone(fieldReport(field.key))" aria-hidden="true">
                    <span :style="{ width: meterWidth(fieldReport(field.key)) }"></span>
                  </div>
                  <p v-if="fieldError(field.key)" :id="`${fieldId(field.key)}-error`" class="npe-field__error">{{ fieldError(field.key) }}</p>
                </div>
              </div>

              <p v-if="validation.total.error" class="npe-total-error" data-testid="npc-persona-editor-total-error">{{ validation.total.error }}</p>

              <!-- The offline greeting: after the card, its own budget. -->
              <div class="npe-divider" aria-hidden="true"><span>◆</span></div>
              <div
                class="npe-section npe-field npe-section--greeting"
                :data-error="fieldError('offline_greeting') ? 'true' : undefined"
                :data-changed="isChanged('offline_greeting') || undefined"
              >
                <div class="npe-field__head">
                  <label class="npe-field__label npe-field__label--section" :for="fieldId('offline_greeting')">{{ GREETING_FIELD.label }}</label>
                  <span class="npe-badge" data-kind="optional">選填</span>
                  <span class="npe-field__count" :id="`${fieldId('offline_greeting')}-count`" :data-tone="countTone(fieldReport('offline_greeting'))">
                    <strong>{{ fieldReport("offline_greeting").used }}</strong> / {{ OFFLINE_GREETING_LIMIT }}
                  </span>
                </div>
                <p :id="`${fieldId('offline_greeting')}-hint`" class="npe-field__hint">
                  填寫後會取代預設問候，成為角色在 AI 離線、或你不帶關鍵字搭話時說的第一句話；留空則恢復預設。關鍵字的回答不受影響，AI 對話永遠依照上方的人物設定。只能寫一個段落，不計入人物設定的總字數。
                </p>
                <div class="npe-default" data-testid="npc-persona-editor-default-greeting">
                  <span class="npe-default__label">目前的預設問候</span>
                  <p v-if="ed.defaultGreeting" class="npe-default__line">{{ ed.defaultGreeting }}</p>
                  <p v-else class="npe-default__line npe-default__line--none">無</p>
                </div>
                <textarea
                  :id="fieldId('offline_greeting')"
                  class="npe-input npe-input--greeting"
                  :data-testid="fieldId('offline_greeting')"
                  :value="ed.draft.offline_greeting"
                  :readonly="!editable || undefined"
                  :aria-invalid="fieldError('offline_greeting') ? 'true' : undefined"
                  :aria-describedby="describedBy('offline_greeting')"
                  rows="2"
                  spellcheck="false"
                  placeholder="留空時使用預設問候"
                  @input="onInput('offline_greeting', $event)"
                ></textarea>
                <div class="npe-meter" :data-tone="countTone(fieldReport('offline_greeting'))" aria-hidden="true">
                  <span :style="{ width: meterWidth(fieldReport('offline_greeting')) }"></span>
                </div>
                <p v-if="fieldError('offline_greeting')" :id="`${fieldId('offline_greeting')}-error`" class="npe-field__error">{{ fieldError("offline_greeting") }}</p>
              </div>
            </form>
          </template>
          <p class="npe-visually-hidden" aria-live="polite">{{ blockErrors.join(" ") }}</p>
        </div>
      </div>

      <!-- The dirty-close confirmation: a small in-drawer alert dialog. -->
      <div v-if="confirmOpen" class="npe-confirm-scrim">
        <div
          class="npe-confirm"
          role="alertdialog"
          aria-modal="true"
          aria-labelledby="npc-persona-editor-confirm-title"
          aria-describedby="npc-persona-editor-confirm-body"
          data-testid="npc-persona-editor-confirm"
          @keydown="onConfirmKeydown"
        >
          <p id="npc-persona-editor-confirm-title" class="npe-confirm__title">放棄未儲存的修改？</p>
          <p id="npc-persona-editor-confirm-body" class="npe-confirm__body">
            你修改了 {{ dirtyCount }} 個欄位。關閉後，本機草稿會清除；已送出的儲存操作不會因此撤回。
          </p>
          <div class="npe-confirm__actions">
            <button ref="confirmKeepRef" type="button" class="npe-btn npe-btn--primary" data-testid="npc-persona-editor-confirm-keep" @click="keepEditing">繼續編輯</button>
            <button ref="confirmDiscardRef" type="button" class="npe-btn npe-btn--danger" data-testid="npc-persona-editor-confirm-discard" @click="confirmDiscard">放棄並關閉</button>
          </div>
        </div>
      </div>
    </div>

    <template #foot>
      <div class="npe-foot" :inert="confirmOpen || undefined">
        <p class="npe-foot__status" role="status" aria-live="polite" data-testid="npc-persona-editor-status">{{ closeNotice || ed.announcement }}</p>
        <p v-if="!ed.announcement" class="npe-foot__status npe-foot__status--summary">{{ footSummary }}</p>
        <span class="npe-foot__hint" aria-hidden="true"><kbd>Ctrl</kbd>+<kbd>Enter</kbd> 儲存</span>
        <button type="button" class="npe-btn npe-btn--ghost" data-testid="npc-persona-editor-cancel" @click="onCancel">取消</button>
        <button
          type="button"
          class="npe-btn npe-btn--primary"
          data-testid="npc-persona-editor-save"
          :disabled="!ed.canSave"
          :aria-disabled="!ed.canSave ? 'true' : undefined"
          @click="onSave"
        >
          {{ saveLabel }}
        </button>
      </div>
    </template>
  </HudDrawer>
</template>
