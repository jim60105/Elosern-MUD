<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { createFocusTrap } from "./focus-trap.js";
const props = defineProps({ state: { type: Object, required: true }, store: { type: Object, required: true } });
const message = ref("");
const direction = ref("");
const thread = ref("");
const refusal = ref("");
const directionEditor = ref(null);
const directionInput = ref(null);
const stage = ref(null);
// The authoritative direction most recently copied into the editor. An unsent
// edit that differs from it is the player's own draft and is never overwritten
// by a later publication.
const syncedDirection = ref("");
let trap = null;
onMounted(() => {
  trap = createFocusTrap(stage.value, { initialFocusEl: stage.value, openerEl: document.activeElement });
  trap.enter();
});
onUnmounted(() => { trap?.restore(); trap = null; });
function onKeydown(event) {
  // Escape cancels an in-progress IME composition for Traditional Chinese
  // input; that keystroke never awakens the dream.
  if (event.isComposing) return;
  if (event.key === "Tab") { trap?.onKeydown(event); return; }
  event.stopPropagation();
  if (event.key === "Escape" && props.state.open) {
    event.preventDefault();
    if (!transportLocked.value) send("awaken");
  }
}
const preferenceFields = [
  { key: "themes", label: "想探索的主題", hint: "例如：信任、重逢。每行一項。" },
  { key: "atmosphere", label: "喜歡的氛圍", hint: "例如：溫柔、懸疑。每行一項。" },
  { key: "participants", label: "希望出現的人物", hint: "每行一位；這是創作偏好，不會改變人物的實際狀態。" },
  { key: "emphasis", label: "想多描寫的部分", hint: "例如：探索、人物互動。每行一項。" },
  { key: "exclusions", label: "不想出現的內容", hint: "例如：暴力。每行一項。" },
];
const preferences = reactive(Object.fromEntries(preferenceFields.map(({ key }) => [key, ""])));
const transportLocked = computed(() => !props.store.view.connected || !!props.store.view.dispatch.inFlight);
const savedDirection = computed(() => (props.state.direction_parts || []).join(""));
const directionPreview = computed(() => direction.value.trim() || savedDirection.value);
const previewLabel = computed(() => direction.value.trim() && direction.value.trim() !== savedDirection.value.trim()
  ? "你修改的方向" : props.state.draft_preferences ? "已保存的草稿" : "最近提出的方向");
const selectedStory = computed(() => thread.value
  ? props.state.thread_choices.find((choice) => choice.id === thread.value)?.label || "已保存的故事線"
  : "新故事");
watch(() => props.state.session_id, () => { message.value = ""; });
watch(() => JSON.stringify([props.state.session_id, props.state.draft_preferences, props.state.direction_parts]), () => {
  const authoritative = Array.from(savedDirection.value).length <= 2000 ? savedDirection.value : "";
  // `dream say` republishes the authored direction on every exchange, so adopt
  // it only while the player has not typed their own unsent edit.
  if (direction.value === "" || direction.value === syncedDirection.value) {
    direction.value = authoritative;
  }
  syncedDirection.value = authoritative;
  thread.value = props.state.draft_preferences?.thread_id || "";
  for (const { key } of preferenceFields) {
    const values = props.state.draft_preferences?.[key];
    preferences[key] = Array.isArray(values) ? values.join("\n") : "";
  }
}, { immediate: true });
async function send(action) {
  refusal.value = "";
  const payload = { session_id: props.state.session_id, revision: props.state.revision };
  if (action === "say") {
    const units = Array.from(message.value);
    payload.message_parts = [units.slice(0, 2000).join(""), units.slice(2000).join("")];
  }
  if (action === "confirm" || action === "draft") {
    const summary = direction.value.trim() || savedDirection.value;
    if (action === "confirm" && !summary.trim()) {
      refusal.value = "先寫下要保存的故事方向，再確認並醒來。你也可以不保存，直接醒來。";
      if (directionEditor.value) directionEditor.value.open = true;
      await nextTick();
      directionInput.value?.focus();
      return;
    }
    const values = Object.fromEntries(preferenceFields.flatMap(({ key }) => {
      const items = preferences[key].split("\n").map((item) => item.trim()).filter(Boolean);
      return items.length ? [[key, items]] : [];
    }));
    payload.direction = (summary || thread.value || Object.keys(values).length)
      ? { ...values, kind: thread.value ? "thread_direction" : "new_story", thread_id: thread.value || null, summary }
      : "";
  }
  const request = props.store.dispatchAction("dream." + action, payload, null);
  if (request && action === "say") message.value = "";
}
</script>

<template>
  <section ref="stage" class="dream-scene" role="dialog" aria-modal="true" aria-label="夢境協作" tabindex="-1" data-testid="dream-panel" @keydown="onKeydown">
    <img v-if="state.scene_art" class="dream-scene__art" :src="state.scene_art" alt="雲海之上的純白王座與王座上的女神" decoding="async" />
    <div v-if="$slots.storyTools" class="dream-scene__story-tools"><slot name="storyTools" /></div>
    <div class="dream-folio">
    <header class="dream-folio__head">
      <p class="dream-folio__eyebrow">雲上王座之夢</p>
      <p class="dream-folio__count" role="status">剩餘交流次數：{{ state.remaining }}。</p>
    </header>
    <p class="dream-folio__opening">{{ state.opening }}</p>
    <div class="dream-folio__narrative">
      <p class="dream-folio__scene">{{ state.scene }}</p>
      <div v-if="state.dialogue" class="dream-folio__dialogue">
        <p class="dream-folio__speaker">王座上的女神</p>
        <blockquote>{{ state.dialogue }}</blockquote>
      </div>
    </div>
    <p class="dream-folio__phase">女神的興奮：{{ state.track.level }}。</p>
    <p v-if="state.pending" class="dream-folio__notice" role="status">女神正在回應。你仍可先儲存草稿，或直接醒來。</p>
    <p v-if="state.failure" class="dream-folio__notice" role="status">暫時沒有收到回應，睡眠已經完成。你可以再試一次，也可以保存方向或醒來。</p>
    <p v-if="state.remaining === 0 && state.open" class="dream-folio__notice">這次夢境的交流已結束。你可以整理方向、儲存草稿，或醒來。</p>
    <p v-if="state.ending" class="dream-folio__ending">{{ state.ending }}</p>
    <form v-if="state.can_input" class="dream-folio__exchange" @submit.prevent="send('say')">
      <label>你輕聲說⋯
        <textarea v-model="message" rows="3" maxlength="4000" :disabled="transportLocked" placeholder="說出你在夢裡想做的事，或回應眼前的女神。" />
      </label>
      <div class="dream-folio__exchange-foot">
        <p>交流不會推進世界時間。</p>
        <button class="ui-btn" type="submit" :disabled="transportLocked || !message.trim()">對女神說</button>
      </div>
    </form>
    <section v-if="state.can_confirm || state.can_draft" class="dream-folio__direction" aria-label="將保存的故事方向">
      <div class="dream-folio__direction-head"><h4>此刻想帶走的念頭</h4><span>{{ selectedStory }}</span></div>
      <template v-if="directionPreview">
        <p class="dream-folio__preview-label">{{ previewLabel }}</p>
        <p class="dream-folio__preview">{{ directionPreview }}</p>
      </template>
      <p v-else class="dream-folio__empty">念頭還未成形。不妨先和眼前的女神聊聊，也可以直接醒來。</p>
      <details ref="directionEditor" data-testid="dream-direction-editor" class="dream-folio__editor">
        <summary>整理想帶走的念頭（選填）</summary>
        <div class="dream-folio__editor-fields">
          <label>要保存的故事方向
            <textarea ref="directionInput" v-model="direction" rows="3" maxlength="2000" :disabled="transportLocked" placeholder="寫下這段故事接下來的走向，最多 2000 字。" />
          </label>
          <p v-if="Array.from(savedDirection).length > 2000 && !direction.trim()" class="dream-folio__notice">最近提出的方向超過 2000 字，請先改寫成較短的故事方向再確認。</p>
          <label v-if="state.thread_choices.length || thread">這個方向屬於哪段故事？
            <select v-model="thread" :disabled="transportLocked">
              <option value="">開始一段新故事</option>
              <option v-for="choice in state.thread_choices" :key="choice.id" :value="choice.id">{{ choice.label }}</option>
            </select>
          </label>
          <details class="dream-folio__preferences"><summary>主題、氛圍與界線（選填）</summary>
            <div class="dream-folio__preference-grid">
              <label v-for="field in preferenceFields" :key="field.key">{{ field.label }}
                <textarea v-model="preferences[field.key]" rows="2" :disabled="transportLocked" :placeholder="field.hint" />
              </label>
            </div>
          </details>
        </div>
      </details>
      <p v-if="refusal" role="alert" class="dream-folio__notice">{{ refusal }}</p>
    </section>
    <footer v-if="state.open" class="dream-folio__choices">
      <p>將想法留作故事方向。醒來後的行動，仍由你決定。</p>
      <div>
        <button v-if="state.can_confirm" class="ui-btn ui-btn--primary" type="button" :disabled="transportLocked" title="確認並保存故事方向，結束這次夢境。" @click="send('confirm')">帶著這個念頭醒來</button>
        <button v-if="state.can_draft" class="ui-btn" type="button" :disabled="transportLocked" title="儲存私人草稿，繼續留在夢裡。" @click="send('draft')">先記下這個念頭</button>
        <button v-if="state.can_awaken" class="ui-btn ui-btn--ghost" type="button" :disabled="transportLocked" @click="send('awaken')">醒來</button>
      </div>
    </footer>
    </div>
  </section>
</template>

<style scoped>
.dream-scene { position: fixed; isolation: isolate; inset: var(--header-h) 0 var(--workspace-bottom); z-index: var(--z-surface-modal); overflow: hidden; background: var(--ink-900); }
.dream-scene:focus { box-shadow: none; outline: none; }
.dream-scene__art { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; object-position: 75% center; }
.dream-scene__story-tools { position: absolute; z-index: 2; top: var(--sp-2); left: var(--sp-5); max-width: calc(100% - 2 * var(--sp-5)); padding: var(--sp-2); background: var(--panel); color: var(--paper-300); }
/* A bottom-left stage instrument, not a framed window: ink feathers toward
   the goddess, with only the band's brass crown and spine mounting it. */
.dream-folio { position: absolute; isolation: isolate; left: var(--sp-4); bottom: 0; display: grid; gap: var(--sp-4); box-sizing: border-box; width: min(58vw, calc(840px * var(--ui-scale))); max-height: calc(100% - 48px * var(--ui-scale)); overflow-y: auto; padding: var(--sp-6) calc(40px * var(--ui-scale)) var(--sp-4) calc(26px * var(--ui-scale)); color: var(--paper-100); font-family: var(--f-serif); font-size: var(--text-base); line-height: 1.8; text-shadow: 0 1px 1px rgba(0,0,0,.8); }
.dream-folio::before { content: ""; position: absolute; inset: 0; z-index: -1; background: var(--panel); backdrop-filter: blur(calc(9px * var(--ui-scale))); mask-image: linear-gradient(90deg, #000 0 85%, transparent), linear-gradient(0deg, #000 0 95%, transparent); mask-composite: intersect; }
.dream-folio::after { content: ""; position: absolute; inset: 0; z-index: -1; pointer-events: none; background: var(--band-ornament) calc(10px * var(--ui-scale)) var(--sp-3) / calc(10px * var(--ui-scale)) calc(10px * var(--ui-scale)) no-repeat, linear-gradient(90deg, var(--band-edge), var(--band-edge-dim), transparent) calc(15px * var(--ui-scale)) var(--sp-4) / 70% 1px no-repeat, linear-gradient(0deg, transparent, var(--band-edge-dim), var(--band-edge)) calc(15px * var(--ui-scale)) var(--sp-4) / 1px 85% no-repeat; }
.dream-folio p, .dream-folio blockquote, .dream-folio h4 { margin: 0; }
.dream-folio__head { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: var(--sp-3); padding-bottom: var(--sp-4); border-bottom: 1px solid var(--band-edge-dim); }
.dream-folio__eyebrow { color: var(--gold-400); font-size: var(--text-sm); letter-spacing: .12em; }
.dream-folio__count { color: var(--paper-50); font-family: var(--f-mono); font-size: var(--text-sm); font-variant-numeric: tabular-nums lining-nums; }
.dream-folio__opening { color: var(--paper-300); font-size: var(--text-sm); }
.dream-folio__phase { color: var(--paper-500); font-size: var(--text-sm); }
.dream-folio__narrative { display: grid; gap: var(--sp-4); }
.dream-folio__scene, .dream-folio__dialogue blockquote, .dream-folio__ending, .dream-folio__preview { white-space: pre-wrap; overflow-wrap: anywhere; }
.dream-folio__dialogue { display: grid; gap: var(--sp-2); padding-left: var(--sp-3); border-left: 1px solid var(--band-edge-dim); color: var(--paper-50); }
.dream-folio__speaker { color: var(--gold-400); font-family: var(--f-sans); font-size: var(--text-sm); }
.dream-folio__notice { padding: var(--sp-3) var(--sp-4); border: var(--line); border-radius: var(--radius-sm); color: var(--paper-300); font-family: var(--f-sans); font-size: var(--text-sm); }
.dream-folio__ending { padding: var(--sp-4); border-block: 1px solid var(--band-edge-dim); color: var(--gold-300); }
.dream-folio__exchange, .dream-folio__editor-fields { display: grid; gap: var(--sp-3); }
.dream-folio__exchange-foot { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: var(--sp-3); }
.dream-folio__exchange-foot p, .dream-folio__choices > p { color: var(--paper-500); font-family: var(--f-sans); font-size: var(--text-sm); }
.dream-folio__direction { display: grid; gap: var(--sp-3); padding-block: var(--sp-4); border-block: 1px solid var(--band-edge-dim); }
.dream-folio__direction-head { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: var(--sp-2); }
.dream-folio__direction-head h4 { color: var(--gold-300); font-size: var(--text-base); font-weight: 500; }
.dream-folio__direction-head span { max-width: 100%; color: var(--paper-500); font-family: var(--f-sans); font-size: var(--text-sm); overflow-wrap: anywhere; }
.dream-folio__preview-label, .dream-folio__empty { color: var(--paper-500); font-family: var(--f-sans); font-size: var(--text-sm); }
.dream-folio__preview { max-height: calc(180px * var(--ui-scale)); overflow-y: auto; }
.dream-folio label { display: grid; min-width: 0; gap: var(--sp-2); color: var(--paper-200); font-family: var(--f-sans); font-size: var(--text-sm); }
.dream-folio textarea, .dream-folio select { box-sizing: border-box; min-width: 0; width: 100%; padding: var(--sp-3); border: 1px solid var(--ink-600); border-radius: var(--radius-sm); background: var(--ink-900); color: var(--paper-100); font: inherit; }
.dream-folio textarea { resize: vertical; font-family: var(--f-serif); font-size: var(--text-base); line-height: 1.6; }
.dream-folio textarea::placeholder { color: var(--paper-500); font-size: var(--text-sm); }
.dream-folio__editor, .dream-folio__preferences { color: var(--paper-300); font-family: var(--f-sans); font-size: var(--text-sm); }
.dream-folio details summary { cursor: pointer; }
.dream-folio details[open] > div { margin-top: var(--sp-4); }
.dream-folio__preference-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(260px * var(--ui-scale), 100%), 1fr)); gap: var(--sp-4); }
.dream-folio__choices { position: sticky; bottom: calc(-1 * var(--sp-4)); z-index: 1; display: grid; gap: var(--sp-2); padding: var(--sp-4) 0; border-top: var(--line); background: var(--ink-900); }
.dream-folio__choices > div { display: flex; flex-wrap: wrap; gap: var(--sp-2); }
@media (max-width: 600px) {
  .dream-folio { width: calc(100% - 2 * var(--sp-4)); max-height: 68%; padding-right: var(--sp-5); }
  .dream-scene__art { object-position: 80% top; }
}
</style>
