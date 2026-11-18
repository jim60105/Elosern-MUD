<script setup>
// CreationPortraitSlot (design §7.1; creation-stepped-form, completed by
// creation-draft-portrait): the custom form's persistent portrait column in
// every committed `portrait` state. It only reads props and emits intents;
// it never dispatches. The host passes:
//
// - `silhouette`: the single `custom.silhouettes[].artwork` entry the
//   server's table names for the current sex and apparent age (or null);
// - `portrait`: the committed panel union (empty / pending / ready / failed /
//   unavailable). Every state but ready shows the silhouette; ready shows the
//   server's artwork unchanged;
// - `disabled`: the shared single-mutation gate (or the host's own admitted
//   request) holding generation;
// - `canGenerate`: whether the host offers the generation controls at all.
//
// The silhouette is decoration (aria-hidden); the ready portrait carries the
// current name as its alternative text. The status line is one always-mounted
// live region, so every transition is announced as text, never by motion
// alone. Spinner and breathing use the motion tokens, so the reduced and off
// levels stop them.
import { computed, ref } from "vue";
import ArtworkPreview from "./ArtworkPreview.vue";

const props = defineProps({
  // The current (unsent) display name.
  name: { type: String, default: "" },
  // The matching `custom.silhouettes[].artwork` descriptor, or null.
  silhouette: { type: Object, default: null },
  // The committed `creation.portrait` union.
  portrait: { type: Object, default: () => ({ status: "empty" }) },
  // The shared dispatch gate (or the host's admitted request) is held.
  disabled: { type: Boolean, default: false },
  // The host offers generation (and refresh) controls.
  canGenerate: { type: Boolean, default: false },
});

const emit = defineEmits(["generate", "refresh-status"]);

// ArtworkPreview judges availability against a panel; the overlay mounts the
// custom form only for an available creation panel.
const AVAILABLE_PANEL = Object.freeze({ available: true });

// The design §7.1 caption of each state without a server reason.
const CAPTIONS = Object.freeze({
  empty: "填好身分後，為角色繪製肖像。",
  pending: "可以繼續填寫，完成後會自動出現。",
  ready: "不滿意可以重新繪製。",
});

// The short state heading above the caption (shape and text, not colour).
const HEADINGS = Object.freeze({
  empty: "尚未繪製",
  pending: "繪製中",
  ready: "肖像完成",
  failed: "繪製失敗",
  unavailable: "繪圖服務離線",
});

const trimmed = computed(() => (props.name ?? "").trim());
const status = computed(() => {
  const value = props.portrait?.status;
  return Object.prototype.hasOwnProperty.call(HEADINGS, value) ? value : "empty";
});
const artwork = computed(() => (status.value === "ready" ? props.portrait.artwork ?? null : null));
const reason = computed(() => (
  status.value === "failed" || status.value === "unavailable" ? props.portrait.reason ?? "" : ""
));
const caption = computed(() => reason.value || CAPTIONS[status.value] || "");
const generateBlocked = computed(() => (
  props.disabled || status.value === "pending" || status.value === "unavailable"
));
const generateLabel = computed(() => {
  if (status.value === "pending") return "繪製中…";
  return status.value === "ready" ? "重新生成肖像" : "生成肖像";
});

const generateButton = ref(null);
const refreshButton = ref(null);
const statusLine = ref(null);

// The host's focus return after its drawer closes: the generate control when
// it can take focus, else the refresh control, else the status line itself.
function focusHome() {
  const target = [generateButton.value, refreshButton.value].find((el) => el && el.isConnected && !el.disabled);
  (target ?? statusLine.value)?.focus();
}

defineExpose({ focusHome });
</script>

<template>
  <aside
    class="creation-portrait"
    data-testid="creation-portrait-slot"
    :data-state="silhouette ? 'silhouette' : 'neutral'"
    :data-portrait="status"
  >
    <div class="creation-portrait__frame" :aria-hidden="artwork ? null : 'true'">
      <div v-if="artwork" class="creation-portrait__art" data-testid="creation-portrait-artwork">
        <ArtworkPreview :artwork="artwork" :panel="AVAILABLE_PANEL" :alt="trimmed ? `${trimmed}的肖像` : '角色肖像'" />
      </div>
      <div v-else-if="silhouette" class="creation-portrait__figure" data-testid="creation-portrait-silhouette">
        <ArtworkPreview :artwork="silhouette" :panel="AVAILABLE_PANEL" />
      </div>
      <span v-if="status === 'pending'" class="creation-portrait__spinner" aria-hidden="true"></span>
      <span class="creation-portrait__corner creation-portrait__corner--tl"></span>
      <span class="creation-portrait__corner creation-portrait__corner--br"></span>
    </div>
    <p
      class="creation-portrait__name"
      data-testid="creation-portrait-name"
      :data-unnamed="trimmed ? null : 'true'"
    >
      {{ trimmed || "尚未命名" }}
    </p>
    <div
      ref="statusLine"
      class="creation-portrait__status"
      role="status"
      tabindex="-1"
      data-testid="creation-portrait-status"
      :data-state="status"
    >
      <p class="creation-portrait__state"><span class="creation-portrait__mark" aria-hidden="true"></span>{{ HEADINGS[status] }}</p>
      <p class="creation-portrait__caption">{{ caption }}</p>
    </div>
    <div v-if="canGenerate" class="creation-portrait__actions">
      <button
        ref="generateButton"
        type="button"
        class="ui-btn creation-portrait__generate"
        data-testid="creation-portrait-generate"
        :disabled="generateBlocked"
        @click="emit('generate')"
      >
        {{ generateLabel }}
      </button>
      <button
        v-if="status === 'unavailable'"
        ref="refreshButton"
        type="button"
        class="ui-btn ui-btn--ghost creation-portrait__refresh"
        data-testid="creation-portrait-refresh"
        @click="emit('refresh-status')"
      >
        重新檢查
      </button>
    </div>
  </aside>
</template>

<style scoped src="./creation-portrait-slot.css"></style>
