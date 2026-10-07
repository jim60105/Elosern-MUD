<script setup>
// The 存檔 page (gm-portal-s5-saves): the world's save slots. A save is the
// whole world (database plus generated art); a restore stages the save, saves
// the current world first, and shuts the server down — the operator starts it
// again and the launcher applies the save before migrating. Every request goes
// through the injected GM fetch boundary; failures surface by code next to the
// action that raised them and never route to the permission view. Only one
// create/restore/delete is in flight at a time; downloads run independently.
import { computed, inject, nextTick, reactive, ref } from "vue";
import GmCodeBlock from "../components/GmCodeBlock.vue";
import GmConfirmDialog from "../components/GmConfirmDialog.vue";
import GmEmpty from "../components/GmEmpty.vue";
import GmError from "../components/GmError.vue";
import GmPanel from "../components/GmPanel.vue";
import GmSaveSlot from "../components/GmSaveSlot.vue";
import {
  KIND_FILTERS,
  LABEL_MAX_LENGTH,
  countByKind,
  deletePath,
  downloadPath,
  errorTitle,
  formatBytes,
  formatCreated,
  formatGameDate,
  restorePath,
  savesPath,
  totalBytes,
} from "../lib/saves.js";

const props = defineProps({
  // Fixed zone for deterministic stories/tests; the browser's own otherwise.
  timeZone: { type: String, default: "" },
});

const api = inject("gmApi");

const state = reactive({ status: "idle", data: null, error: null });
const filter = ref("all");
const tabRefs = ref([]);
const create = reactive({ label: "", busy: false, error: null });
const announcement = ref("");
const arrivedId = ref("");
const rowErrors = reactive({});
const downloads = reactive({});
const restore = reactive({ target: null, busy: false, error: null });
const removal = reactive({ target: null, busy: false, error: null });
const shutdown = ref(null);
const shutdownHeading = ref(null);
const labelInput = ref(null);

const saves = computed(() => state.data?.saves ?? []);
const counts = computed(() => countByKind(saves.value));
const visible = computed(() =>
  filter.value === "all" ? saves.value : saves.value.filter((save) => save.kind === filter.value),
);
const pendingId = computed(() => state.data?.pending ?? null);
const locked = computed(() => create.busy || restore.busy || removal.busy || Boolean(pendingId.value));
const keep = computed(() => state.data?.autosave_keep ?? null);
const result = computed(() => state.data?.restore_result ?? null);
const zone = computed(() => (props.timeZone ? { timeZone: props.timeZone } : {}));

function describe(error) {
  const code = typeof error?.code === "string" ? error.code : "client_error";
  return { code, title: errorTitle(code), message: error?.message ?? "" };
}

async function load() {
  if (!state.data) state.status = "loading";
  try {
    state.data = await api.get(savesPath());
    state.status = "ready";
    state.error = null;
  } catch (error) {
    state.status = state.data ? "ready" : "error";
    state.error = describe(error);
  }
}

function clearRowError(id) {
  delete rowErrors[id];
}

async function submitCreate() {
  if (locked.value) return;
  create.busy = true;
  create.error = null;
  announcement.value = "";
  try {
    const save = await api.post(savesPath(), { label: create.label });
    create.label = "";
    arrivedId.value = save.id;
    if (filter.value !== "all" && filter.value !== save.kind) filter.value = "all";
    announcement.value = `已建立存檔「${save.label || "未命名存檔"}」。`;
    await load();
  } catch (error) {
    create.error = describe(error);
    // A pending restore may explain the refusal: show it.
    if (error?.code === "save_in_progress") load();
  } finally {
    create.busy = false;
    nextTick(() => labelInput.value?.focus());
  }
}

function askRestore(save) {
  clearRowError(save.id);
  restore.error = null;
  restore.target = save;
}

function askDelete(save) {
  clearRowError(save.id);
  removal.error = null;
  removal.target = save;
}

async function confirmRestore() {
  const target = restore.target;
  if (!target || restore.busy) return;
  restore.busy = true;
  restore.error = null;
  try {
    const accepted = await api.post(restorePath(target.id), {});
    restore.target = null;
    shutdown.value = { save: target, preId: accepted.pre_restore_save };
    await nextTick();
    shutdownHeading.value?.focus();
  } catch (error) {
    restore.error = describe(error);
    if (["save_not_found", "save_in_progress"].includes(error?.code)) load();
  } finally {
    restore.busy = false;
  }
}

async function confirmDelete() {
  const target = removal.target;
  if (!target || removal.busy) return;
  removal.busy = true;
  removal.error = null;
  const order = visible.value.map((save) => save.id);
  const index = order.indexOf(target.id);
  try {
    await api.post(deletePath(target.id), {});
    removal.target = null;
    announcement.value = `已刪除存檔「${target.label || target.id}」。`;
    await load();
    await nextTick();
    const neighbour = order[index + 1] ?? order[index - 1];
    const next = neighbour && document.querySelector(`[data-save="${neighbour}"] [data-action="restore"]`);
    (next ?? document.getElementById("gm-saves-list-heading"))?.focus();
  } catch (error) {
    removal.error = describe(error);
    if (["save_not_found", "save_in_progress"].includes(error?.code)) load();
  } finally {
    removal.busy = false;
  }
}

async function download(save) {
  if (downloads[save.id] === "busy") return;
  clearRowError(save.id);
  downloads[save.id] = "busy";
  try {
    const { blob, filename } = await api.download(downloadPath(save.id));
    const url = globalThis.URL?.createObjectURL?.(blob);
    if (url) {
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename || `elosern-save-${save.id}.tar`;
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      setTimeout(() => globalThis.URL.revokeObjectURL(url), 60_000);
    }
    downloads[save.id] = "done";
    setTimeout(() => {
      if (downloads[save.id] === "done") downloads[save.id] = "idle";
    }, 3000);
  } catch (error) {
    downloads[save.id] = "idle";
    rowErrors[save.id] = describe(error);
  }
}

// The kind filter is a tablist: arrows move and select, Home/End jump.
function onTabKeydown(event, index) {
  const last = KIND_FILTERS.length - 1;
  const target = { ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: last }[event.key];
  if (target === undefined) return;
  event.preventDefault();
  const next = (target + KIND_FILTERS.length) % KIND_FILTERS.length;
  filter.value = KIND_FILTERS[next].key;
  tabRefs.value[next]?.focus();
}

const counterWarn = computed(() => create.label.length >= LABEL_MAX_LENGTH - 8);

load();
</script>

<template>
  <div class="gm-saves">
    <div class="gm-saves__layout">
    <p class="gm-visually-hidden" role="status" aria-live="polite">{{ announcement }}</p>

    <!-- After an accepted restore the page holds still: the server is going down. -->
    <section v-if="shutdown" class="gm-saves__shutdown" aria-labelledby="gm-saves-shutdown-title">
      <span class="gm-saves__shutdown-ornament" aria-hidden="true"></span>
      <h2 id="gm-saves-shutdown-title" ref="shutdownHeading" class="gm-saves__shutdown-title" tabindex="-1" role="status">
        伺服器正在關閉
      </h2>
      <p class="gm-saves__shutdown-lead">
        讀檔已排定：「{{ shutdown.save.label || "未命名存檔" }}」<code>{{ shutdown.save.id }}</code>
        會在下次啟動時套用。
      </p>
      <p class="gm-saves__shutdown-note">
        目前的世界已先保存為讀檔前自動存檔 <code>{{ shutdown.preId }}</code>，需要時可以讀回。
      </p>
      <ol class="gm-saves__steps">
        <li>
          <span class="gm-saves__step-title">等待伺服器停止</span>
          <span class="gm-saves__step-note">所有連線會在數秒內中斷，這個頁面也會失去連線。</span>
        </li>
        <li>
          <span class="gm-saves__step-title">重新啟動伺服器</span>
          <span class="gm-saves__step-note">啟動器會在資料庫遷移之前套用存檔。</span>
          <span class="gm-saves__commands">
            <span class="gm-saves__command"><code>scripts/serve.sh</code><GmCodeBlock text="scripts/serve.sh" copy-only /></span>
            <span class="gm-saves__command"><code>podman compose up</code><GmCodeBlock text="podman compose up" copy-only /></span>
          </span>
        </li>
        <li>
          <span class="gm-saves__step-title">重新整理此頁</span>
          <span class="gm-saves__step-note">頁面頂端會顯示讀檔的結果。</span>
        </li>
      </ol>
    </section>

    <template v-else>
      <div v-if="result || pendingId" class="gm-saves__notices">
      <div
        v-if="result"
        class="gm-saves__result"
        :class="result.outcome === 'restored' ? 'is-restored' : 'is-failed'"
        role="status"
      >
        <span class="gm-saves__result-glyph" aria-hidden="true">{{ result.outcome === "restored" ? "✓" : "✕" }}</span>
        <div class="gm-saves__result-text">
          <p class="gm-saves__result-title">
            {{ result.outcome === "restored" ? "上次讀檔成功" : "上次讀檔失敗" }}
            <span v-if="result.finished_at" class="gm-saves__result-time">· {{ formatCreated(result.finished_at, zone) }}</span>
          </p>
          <p class="gm-saves__result-body">
            <template v-if="result.save">「{{ result.label || "未命名存檔" }}」<code>{{ result.save }}</code></template>
            <template v-if="result.outcome === 'restored'">已成為目前的世界。</template>
            <template v-else>未套用：{{ result.reason }}。目前世界維持原狀。</template>
          </p>
        </div>
      </div>

      <div v-if="pendingId" class="gm-saves__pending" role="status">
        <span class="gm-saves__pending-glyph" aria-hidden="true">▲</span>
        伺服器正在關閉，讀檔 <code>{{ pendingId }}</code> 將於下次啟動時套用；在那之前不能建立、讀取或刪除存檔。
      </div>
      </div>

      <GmPanel
        class="gm-saves__create"
        title="建立存檔"
        description="保存目前的整個世界：資料庫與所有生成的美術。"
        :busy="create.busy"
      >
        <form class="gm-saves__form" @submit.prevent="submitCreate">
          <label class="gm-saves__field-label" for="gm-save-label">存檔名稱<span class="gm-muted">（選填）</span></label>
          <div class="gm-saves__field">
            <input
              id="gm-save-label"
              ref="labelInput"
              v-model="create.label"
              class="gm-saves__input"
              type="text"
              :maxlength="LABEL_MAX_LENGTH"
              placeholder="例如：決戰之前"
              autocomplete="off"
              aria-describedby="gm-save-label-count"
            >
            <button
              type="submit"
              class="ui-btn ui-btn--primary"
              :aria-disabled="locked ? 'true' : null"
              data-action="create"
            >
              {{ create.busy ? "建立中…" : "建立存檔" }}
            </button>
          </div>
          <p id="gm-save-label-count" class="gm-saves__counter" :class="{ 'is-near': counterWarn }">
            {{ create.label.length }} / {{ LABEL_MAX_LENGTH }}
          </p>
        </form>
        <GmError
          v-if="create.error"
          compact
          :title="create.error.title"
          :message="create.error.message"
          :code="create.error.code"
        />
      </GmPanel>

      <section class="gm-saves__stats" aria-label="存檔統計">
        <div class="gm-stat gm-saves__stat">
          <span class="gm-stat__value">{{ state.data ? counts.manual : "—" }}</span>
          <span class="gm-stat__label">手動存檔</span>
        </div>
        <div class="gm-stat gm-saves__stat">
          <span class="gm-stat__value">
            {{ state.data ? counts.auto_restore : "—" }}<span v-if="keep" class="gm-saves__of">/ {{ keep }}</span>
          </span>
          <span class="gm-stat__label">讀檔前自動</span>
        </div>
        <div class="gm-stat gm-saves__stat">
          <span class="gm-stat__value">
            {{ state.data ? counts.auto_intervention : "—" }}<span v-if="keep" class="gm-saves__of">/ {{ keep }}</span>
          </span>
          <span class="gm-stat__label">介入前自動</span>
        </div>
        <div class="gm-stat gm-saves__stat">
          <span class="gm-stat__value">{{ state.data ? formatBytes(totalBytes(saves)) : "—" }}</span>
          <span class="gm-stat__label">總大小</span>
        </div>
        <p v-if="keep" class="gm-saves__footnote">
          自動存檔每類保留最近 {{ keep }} 份；手動存檔不會自動刪除。
        </p>
      </section>

      <section class="gm-saves__list" aria-labelledby="gm-saves-list-heading">
        <header class="gm-saves__list-header">
          <h2 id="gm-saves-list-heading" class="gm-saves__list-title" tabindex="-1">存檔列表</h2>
          <div class="ui-tabs gm-saves__tabs" role="tablist" aria-label="依種類篩選">
            <button
              v-for="(tab, index) in KIND_FILTERS"
              :id="`gm-saves-tab-${tab.key}`"
              :key="tab.key"
              ref="tabRefs"
              type="button"
              role="tab"
              class="ui-tabs__tab"
              :class="{ 'is-active': filter === tab.key }"
              :aria-selected="filter === tab.key ? 'true' : 'false'"
              aria-controls="gm-saves-panel"
              :tabindex="filter === tab.key ? 0 : -1"
              :data-filter="tab.key"
              @click="filter = tab.key"
              @keydown="onTabKeydown($event, index)"
            >
              {{ tab.label }}<span class="gm-saves__count">{{ counts[tab.key] ?? 0 }}</span>
            </button>
          </div>
        </header>

        <div
          id="gm-saves-panel"
          class="gm-saves__panel"
          role="tabpanel"
          :aria-labelledby="`gm-saves-tab-${filter}`"
          :aria-busy="state.status === 'loading' ? 'true' : null"
        >
          <div v-if="state.status === 'loading' || state.status === 'idle'" class="gm-saves__skeleton">
            <span class="gm-visually-hidden">載入存檔中…</span>
            <span v-for="n in 5" :key="n" class="gm-skeleton gm-saves__skeleton-row" aria-hidden="true"></span>
          </div>
          <div v-else-if="state.status === 'error'" class="gm-saves__panel-pad">
            <GmError :title="state.error.title" :message="state.error.message" :code="state.error.code">
              <template #actions>
                <button type="button" class="ui-btn ui-btn--sm" @click="load">重試</button>
              </template>
            </GmError>
          </div>
          <GmEmpty
            v-else-if="!saves.length"
            title="尚無存檔"
            message="建立第一份手動存檔；讀檔或 GM 介入前也會自動存檔。"
          />
          <GmEmpty v-else-if="!visible.length" title="此分類沒有存檔" />
          <template v-else>
            <div class="gm-saves__columns" aria-hidden="true">
              <span>種類</span><span>名稱</span><span>建立／遊戲內時間</span><span>玩家角色</span>
              <span class="gm-saves__columns-end">大小</span><span class="gm-saves__columns-end">操作</span>
            </div>
            <ol class="gm-saves__slots">
              <GmSaveSlot
                v-for="save in visible"
                :key="save.id"
                :save="save"
                :locked="locked"
                :download-state="downloads[save.id] ?? 'idle'"
                :error="rowErrors[save.id] ?? null"
                :arrived="save.id === arrivedId"
                :time-zone="timeZone"
                @restore="askRestore"
                @download="download"
                @delete="askDelete"
              />
            </ol>
          </template>
        </div>
      </section>
    </template>
    </div>

    <GmConfirmDialog
      :open="Boolean(restore.target)"
      title="讀取這份存檔？"
      confirm-label="關閉伺服器並讀檔"
      busy-label="送出中…"
      danger
      :busy="restore.busy"
      fallback-focus="#gm-saves-list-heading"
      @cancel="restore.target = null"
      @confirm="confirmRestore"
    >
      <template v-if="restore.target">
        <dl class="gm-ledger gm-saves__summary">
          <div class="gm-ledger__row"><dt>名稱</dt><dd>{{ restore.target.label || "未命名存檔" }}</dd></div>
          <div class="gm-ledger__row"><dt>識別碼</dt><dd><code>{{ restore.target.id }}</code></dd></div>
          <div class="gm-ledger__row">
            <dt>遊戲內時間</dt><dd>{{ formatGameDate(restore.target.clock) ?? "—" }}</dd>
          </div>
          <div class="gm-ledger__row">
            <dt>建立時間</dt><dd>{{ formatCreated(restore.target.created_at, zone) }}</dd>
          </div>
        </dl>
        <ol class="gm-saves__consequences">
          <li>目前的世界會先保存為<strong>讀檔前自動存檔</strong>。</li>
          <li>接著<strong>伺服器會關閉</strong>，所有連線都會中斷。</li>
          <li>你需要<strong>手動重新啟動伺服器</strong>；讀檔會在下次啟動時套用，較舊的存檔會自動升級資料庫格式。</li>
        </ol>
      </template>
      <template v-if="restore.error" #error>
        <GmError compact :title="restore.error.title" :message="restore.error.message" :code="restore.error.code" />
      </template>
    </GmConfirmDialog>

    <GmConfirmDialog
      :open="Boolean(removal.target)"
      title="刪除存檔？"
      confirm-label="永久刪除"
      busy-label="刪除中…"
      danger
      :busy="removal.busy"
      fallback-focus="#gm-saves-list-heading"
      @cancel="removal.target = null"
      @confirm="confirmDelete"
    >
      <template v-if="removal.target">
        <p class="gm-saves__delete-target">
          「{{ removal.target.label || "未命名存檔" }}」<code>{{ removal.target.id }}</code>
        </p>
        <p>資料庫與美術兩半都會刪除，<strong>此動作無法復原</strong>。</p>
      </template>
      <template v-if="removal.error" #error>
        <GmError compact :title="removal.error.title" :message="removal.error.message" :code="removal.error.code" />
      </template>
    </GmConfirmDialog>
  </div>
</template>

<style scoped>
/* The page is the container; its layout grid answers to the container's
   width (a container query never styles the container itself). */
.gm-saves {
  container: gm-saves / inline-size;
}

.gm-saves__layout {
  display: grid;
  grid-template-columns: minmax(0, 5fr) minmax(0, 7fr);
  grid-template-areas:
    "notices notices"
    "create stats"
    "list list";
  gap: var(--sp-5);
  align-items: start;
}

.gm-saves__notices {
  display: grid;
  grid-area: notices;
  gap: var(--sp-3);
}

.gm-saves__create {
  grid-area: create;
  height: 100%;
}

.gm-saves__stats {
  grid-area: stats;
}

.gm-saves__list {
  grid-area: list;
}

.gm-saves__shutdown {
  grid-column: 1 / -1;
}

.gm-saves code {
  padding: 0 var(--sp-1);
  font-size: 0.9em;
  color: var(--paper-200);
  overflow-wrap: anywhere;
}

/* Latest restore outcome. */
.gm-saves__result {
  display: flex;
  align-items: flex-start;
  gap: var(--sp-4);
  padding: var(--sp-4) var(--sp-5);
  background: var(--ink-860);
  border: var(--line);
  border-radius: var(--radius);
}

.gm-saves__result.is-restored {
  border-left: 3px solid var(--ok);
}

.gm-saves__result.is-failed {
  border-left: 3px double var(--crit);
}

.gm-saves__result-glyph {
  display: grid;
  place-items: center;
  flex: none;
  width: 28px;
  height: 28px;
  font-weight: 700;
  border: 1px solid currentcolor;
  border-radius: 50%;
}

.is-restored .gm-saves__result-glyph {
  color: var(--ok);
}

.is-failed .gm-saves__result-glyph {
  color: var(--crit);
  border-style: double;
  border-width: 3px;
}

.gm-saves__result-title {
  font-family: var(--f-serif);
  font-size: var(--text-md);
  font-weight: 600;
  color: var(--paper-50);
}

.gm-saves__result-time {
  font-family: var(--f-mono);
  font-size: var(--text-sm);
  font-weight: 400;
  color: var(--paper-500);
}

.gm-saves__result-body {
  color: var(--paper-300);
}

.gm-saves__pending {
  padding: var(--sp-3) var(--sp-5);
  color: var(--warn);
  background: color-mix(in srgb, var(--warn) 7%, var(--ink-860));
  border: 1px dashed var(--warn);
  border-radius: var(--radius);
}

.gm-saves__pending-glyph {
  margin-right: var(--sp-2);
}

/* Create form. */
.gm-saves__form {
  display: grid;
  gap: var(--sp-2);
  margin-bottom: var(--sp-3);
}

.gm-saves__field-label {
  font-size: var(--text-sm);
  color: var(--paper-300);
}

.gm-saves__field {
  display: flex;
  gap: var(--sp-3);
}

.gm-saves__input {
  flex: 1;
  min-width: 0;
  min-height: 40px;
  padding: var(--sp-2) var(--sp-3);
  font: inherit;
  color: var(--paper-50);
  background: var(--ink-950);
  border: 1px solid var(--ink-600);
  border-radius: var(--radius);
  transition: border-color var(--motion-fast) var(--ease-standard);
}

.gm-saves__input::placeholder {
  color: var(--paper-700);
}

.gm-saves__input:hover {
  border-color: var(--paper-700);
}

.gm-saves__input:focus-visible {
  outline: none;
  border-color: var(--gold-500);
  box-shadow: var(--focus);
}

.gm-saves__counter {
  justify-self: end;
  font-family: var(--f-mono);
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-saves__counter.is-near {
  color: var(--warn);
}

.gm-saves .ui-btn[aria-disabled="true"] {
  opacity: 0.45;
  cursor: not-allowed;
}

/* Stats tiles. */
.gm-saves__stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--sp-3);
}

.gm-saves__stat {
  align-content: center;
  min-height: 84px;
  padding: var(--sp-4) var(--sp-5);
  background: var(--ink-860);
  box-shadow: inset 0 1px 0 color-mix(in srgb, var(--gold-500) 14%, transparent);
}

.gm-saves__of {
  margin-left: var(--sp-1);
  font-size: var(--text-sm);
  color: var(--paper-500);
}

.gm-saves__footnote {
  grid-column: 1 / -1;
  font-size: var(--text-xs);
  color: var(--paper-500);
}

/* The list panel: GmPanel's chrome with a tablist header. */
.gm-saves__list {
  min-width: 0;
  background: var(--ink-860);
  border: var(--line);
  border-radius: var(--radius);
  box-shadow:
    inset 0 1px 0 color-mix(in srgb, var(--gold-500) 22%, transparent),
    var(--shadow);
}

.gm-saves__list-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-3);
  padding: var(--sp-4) var(--sp-5);
  border-bottom: 1px solid var(--ink-700);
}

.gm-saves__list-title {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  font-family: var(--f-serif);
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--paper-100);
  border-radius: var(--radius-sm);
}

.gm-saves__list-title::before {
  content: "";
  width: 6px;
  height: 6px;
  background: var(--gold-500);
  transform: rotate(45deg);
}

.gm-saves__list-title:focus-visible,
.gm-saves__tabs .ui-tabs__tab:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.gm-saves__tabs .ui-tabs__tab {
  min-height: 34px;
}

.gm-saves__count {
  margin-left: var(--sp-2);
  font-family: var(--f-mono);
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.ui-tabs__tab.is-active .gm-saves__count {
  color: var(--gold-500);
}

.gm-saves__panel {
  display: grid;
  grid-template-columns: 9.5rem minmax(13rem, 2.2fr) minmax(13rem, 1.5fr) minmax(11rem, 1.4fr) 6.5rem max-content;
}

.gm-saves__panel > * {
  grid-column: 1 / -1;
}

.gm-saves__panel-pad {
  padding: var(--sp-5);
}

.gm-saves__columns {
  display: grid;
  grid-template-columns: subgrid;
  column-gap: var(--sp-5);
  padding: var(--sp-2) var(--sp-5);
  font-size: var(--text-xs);
  letter-spacing: 0.08em;
  color: var(--paper-500);
  background: var(--ink-900);
  border-bottom: 1px solid var(--ink-700);
}

.gm-saves__columns-end {
  text-align: end;
}

.gm-saves__slots {
  display: grid;
  grid-template-columns: subgrid;
  margin: 0;
  padding: 0;
  list-style: none;
}

.gm-saves__skeleton {
  display: grid;
  gap: var(--sp-4);
  padding: var(--sp-5);
}

.gm-saves__skeleton-row {
  height: 2.6em;
}

/* Dialog content. */
.gm-saves__summary {
  padding: var(--sp-3) var(--sp-4);
  background: var(--ink-900);
  border: var(--line);
  border-radius: var(--radius-sm);
}

.gm-saves__consequences {
  display: grid;
  gap: var(--sp-2);
  margin: 0;
  padding-left: 1.6em;
  color: var(--paper-200);
}

.gm-saves__consequences li::marker {
  font-family: var(--f-mono);
  color: var(--seal-400);
}

.gm-saves__consequences strong,
.gm-saves__delete-target + p strong {
  font-weight: 600;
  color: var(--paper-50);
}

.gm-saves__delete-target {
  font-size: var(--text-md);
  color: var(--paper-50);
}

/* The shutdown state: one centred ledger sheet. */
.gm-saves__shutdown {
  display: grid;
  justify-items: center;
  gap: var(--sp-4);
  width: min(48rem, 100%);
  margin: var(--sp-8) auto;
  padding: var(--sp-8);
  text-align: center;
  background: var(--ink-860);
  border: var(--line);
  border-top: 1px solid var(--seal-600);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}

.gm-saves__shutdown-ornament {
  width: 120px;
  height: 11px;
  background:
    var(--band-ornament) center / 30px 11px no-repeat,
    linear-gradient(90deg, transparent, var(--band-edge-dim) 20%, var(--band-edge-dim) 80%, transparent)
      center / 100% 1px no-repeat;
}

.gm-saves__shutdown-title {
  font-family: var(--f-display);
  font-size: var(--text-3xl);
  font-weight: 400;
  color: var(--paper-50);
  border-radius: var(--radius-sm);
}

.gm-saves__shutdown-title:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.gm-saves__shutdown-lead {
  color: var(--paper-200);
}

.gm-saves__shutdown-note {
  font-size: var(--text-sm);
  color: var(--paper-400);
}

.gm-saves__steps {
  display: grid;
  gap: var(--sp-3);
  width: 100%;
  margin: var(--sp-2) 0 0;
  padding: 0;
  text-align: start;
  list-style: none;
  counter-reset: gm-step;
}

.gm-saves__steps > li {
  display: grid;
  gap: var(--sp-1);
  padding: var(--sp-3) var(--sp-4) var(--sp-3) calc(var(--sp-4) + 2.4em);
  position: relative;
  background: var(--ink-900);
  border: var(--line);
  border-radius: var(--radius-sm);
  counter-increment: gm-step;
}

.gm-saves__steps > li::before {
  content: counter(gm-step, decimal-leading-zero);
  position: absolute;
  top: var(--sp-3);
  left: var(--sp-4);
  font-family: var(--f-mono);
  color: var(--gold-500);
}

.gm-saves__step-title {
  font-weight: 600;
  color: var(--paper-100);
}

.gm-saves__step-note {
  font-size: var(--text-sm);
  color: var(--paper-400);
}

.gm-saves__commands {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
  margin-top: var(--sp-1);
}

.gm-saves__command {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
  padding: var(--sp-1) var(--sp-1) var(--sp-1) var(--sp-3);
  background: var(--ink-950);
  border: var(--line);
  border-radius: var(--radius-sm);
}

@container gm-saves (max-width: 959px) {
  .gm-saves__layout {
    grid-template-columns: minmax(0, 1fr);
    grid-template-areas:
      "notices"
      "create"
      "stats"
      "list";
  }

  .gm-saves__panel {
    display: block;
  }

  .gm-saves__columns {
    display: none;
  }

  .gm-saves__slots {
    display: block;
  }
}

@container gm-saves (min-width: 560px) and (max-width: 959px) {
  .gm-saves__stats {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@container gm-saves (max-width: 559px) {

  .gm-saves__field {
    flex-direction: column;
  }
}
</style>
