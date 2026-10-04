<script setup>
import { computed, ref, watch } from "vue";
const props = defineProps({ state: { type: Object, required: true }, store: { type: Object, required: true } });
const message = ref("");
const direction = ref("");
const thread = ref("");
const preferences = ref("");
const refusal = ref("");
const transportLocked = computed(() => !props.store.view.connected || !!props.store.view.dispatch.inFlight);
watch(() => props.state.session_id, () => { message.value = ""; });
watch(() => JSON.stringify([props.state.session_id, props.state.draft_preferences, props.state.direction_parts]), () => {
  const saved = (props.state.direction_parts || []).join("");
  direction.value = Array.from(saved).length <= 2000 ? saved : "";
  thread.value = props.state.draft_preferences?.thread_id || "";
  const draft = props.state.draft_preferences;
  preferences.value = draft ? JSON.stringify(Object.fromEntries(
    ["themes", "atmosphere", "participants", "emphasis", "exclusions"].filter((key) => draft[key]).map((key) => [key, draft[key]]),
  ), null, 2) : "";
}, { immediate: true });
function send(action) {
  const payload = { session_id: props.state.session_id, revision: props.state.revision };
  if (action === "say") {
    const units = Array.from(message.value);
    payload.message_parts = [units.slice(0, 2000).join(""), units.slice(2000).join("")];
  }
  if (action === "confirm" || action === "draft") {
    let values = {};
    try {
      values = preferences.value.trim() ? JSON.parse(preferences.value) : {};
    } catch {
      refusal.value = "偏好 JSON 格式無法讀取。";
      return;
    }
    payload.direction = preferences.value.trim() || thread.value || direction.value.trim()
      ? { ...values, kind: thread.value ? "thread_direction" : "new_story", thread_id: thread.value || null,
          summary: direction.value.trim() || (props.state.direction_parts || []).join("") }
      : "";
  }
  const request = props.store.dispatchAction("dream." + action, payload, null);
  if (request && action === "say") message.value = "";
}
</script>

<template>
  <section class="dream-folio" aria-label="夢境協作" data-testid="dream-panel">
    <p>{{ state.opening }}</p>
    <p class="dream-folio__scene">{{ state.scene }}</p>
    <p class="dream-folio__dialogue">{{ state.dialogue }}</p>
    <p role="status">剩餘交流次數：{{ state.remaining }}。夢境階段：{{ state.track.level }}。</p>
    <p v-if="state.pending">回應生成中，你仍可儲存草稿或醒來。</p>
    <p v-if="state.failure">回應暫時無法生成，你仍可儲存草稿或醒來。</p>
    <p v-if="state.ending">{{ state.ending }}</p>
    <form v-if="state.can_input" @submit.prevent="send('say')">
      <label>想說的話<textarea v-model="message" maxlength="4000" :disabled="transportLocked" /></label>
      <button type="submit" :disabled="transportLocked || !message.trim()">交流</button>
    </form>
    <label v-if="state.can_confirm || state.can_draft">要保存的故事方向
      <textarea v-model="direction" maxlength="2000" :disabled="transportLocked" placeholder="留白會優先沿用已保存的草稿，尚無草稿時才使用最近提出的方向。" />
    </label>
    <template v-if="state.can_confirm || state.can_draft">
      <label>方向適用的故事
        <select v-model="thread" :disabled="transportLocked">
          <option value="">新故事</option>
          <option v-for="identity in state.thread_choices" :key="identity" :value="identity">{{ identity }}</option>
        </select>
      </label>
      <details><summary>主題、氛圍與偏好</summary>
        <label>偏好 JSON（themes、atmosphere、participants、emphasis、exclusions）
          <textarea v-model="preferences" :disabled="transportLocked" placeholder='{"themes":["尋找鐘聲"],"exclusions":["暴力"]}' />
        </label>
      </details>
      <p role="status">{{ refusal }}</p>
    </template>
    <div class="dream-folio__choices">
      <button v-if="state.can_confirm" type="button" :disabled="transportLocked" @click="send('confirm')">確認故事方向</button>
      <button v-if="state.can_draft" type="button" :disabled="transportLocked" @click="send('draft')">儲存私人草稿</button>
      <button v-if="state.can_awaken && state.open" type="button" :disabled="transportLocked" @click="send('awaken')">醒來</button>
    </div>
  </section>
</template>

<style scoped>
.dream-folio { color: var(--paper-100); font-family: var(--f-serif); line-height: 1.8; padding: calc(20px * var(--ui-scale)); border-top: 1px solid var(--band-edge-dim); }
.dream-folio__scene, .dream-folio__dialogue { white-space: pre-wrap; overflow-wrap: anywhere; }
.dream-folio label { display: grid; gap: .5em; margin-block: 1em; }
.dream-folio textarea { color: var(--paper-100); background: var(--panel); border: 1px solid var(--band-edge-dim); padding: .7em; font: inherit; }
.dream-folio__choices { display: flex; flex-wrap: wrap; gap: 1em; }
.dream-folio button { color: var(--paper-100); background: transparent; border: 1px solid var(--band-edge-dim); padding: .6em; font: inherit; cursor: pointer; }
.dream-folio button:disabled { opacity: .5; cursor: default; }
</style>
