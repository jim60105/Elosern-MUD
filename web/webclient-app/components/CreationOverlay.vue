<script setup>
// CreationOverlay (B5 overlays family): the full-viewport character-creation
// wizard for the committed `creation` v5 panel (web/webclient/presentation/
// creation.py). Sub-states stay separate and testable (design D-risk): a
// preset-pick state, the custom form (name/age/race/subrace/allocation/
// affinity/background/persona), and the concept state. The panel carries
// the player-owned draft `persona` block and the optional transient concept
// `proposal` slot (retool-concept-transient-fill): the slot pre-fills the
// custom form revision-gated and never auto-submits. The age bounds gate
// (design D1) rejects BOTH the age and apparent_age fields below the
// descriptor's minimum before activation. Every action emits the exact OOB `creation.*`
// envelope — no field is invented; the server remains authoritative.
// The preset mode is the CreationPresetWall card wall (creation-preset-card-
// wall): browsing it is local, and only its `choose` reaches `selectPreset`.
// The custom mode is CreationPortraitSlot beside CreationCustomSteps, and the
// concept mode is CreationConceptGuide beside the concept field
// (creation-stepped-form); each child receives the existing state below.
// The behavior groups live in ./composables/use-creation-*.js (each watch
// stays with the state it mutates); every binding below is a group's verbatim
// state/handler; the stepped form receives the whole binding set.
import { computed, ref } from "vue";
import { useCreationOverlay } from "../composables/use-creation-overlay.js";
import CreationPresetWall from "./CreationPresetWall.vue";
import CreationCustomSteps from "./CreationCustomSteps.vue";
import CreationPortraitSlot from "./CreationPortraitSlot.vue";
import CreationConceptGuide from "./CreationConceptGuide.vue";

// The shared mode tabs (design §4 labels), rendered in the header.
const MODE_TABS = [
  { mode: "preset", label: "預設角色" },
  { mode: "custom", label: "自由創建" },
  { mode: "concept", label: "概念生成" },
];

const props = defineProps({
  // The committed `creation` v5 panel payload (the available form, a
  // server-persisted wizard draft, or the registry-owned unavailable form).
  creation: { type: Object, required: true },
  open: { type: Boolean, default: true },
  // The store's last `ui_action_result` (or null): a rejected creation
  // action renders its code/message in the form message (the legacy
  // `creation-form-message` hook).
  result: { type: Object, default: null },
  // The store-driven creation dock stage (the legacy creation dock port):
  // null outside creation mode, otherwise the dock stage the keyboard router
  // and the confirmation screens mirror (root/presets/custom/confirm).
  stage: { type: Object, default: null },
  // A return-bearing dispatch callback (AppClient wraps `store.dispatchAction`):
  // returns the requestId when the mutation is admitted, null when the
  // single-mutation-in-flight gate rejects it. The concept apply sets its
  // loading state ONLY after admission, so a gate-rejected apply never
  // sticks a spinner (retool-concept-fill-navigation D1). Without the prop
  // (standalone mounts/tests) the apply falls back to the `action` event.
  dispatch: { type: Function, default: null },
  // The store's `view.dispatch` slice ({inFlight, submittedRequestId}): the
  // failure-match correlation and the global-gate release safety net (D1).
  dispatchState: { type: Object, default: null },
  // The action-feedback queue API (add-action-feedback-toasts). The form is
  // the SOLE writer of the concept-apply success confirmation toast (D3);
  // the store writes only failure crits.
  pushToast: { type: Function, default: null },
});

const emit = defineEmits(["action", "request-reset", "cancel-confirm"]);

const creation = useCreationOverlay(props, emit);
// The committed draft's preset key: the wall's entry card and its 目前草稿
// marker follow the server draft, never an unconfirmed choose.
const savedPresetKey = computed(() => (
  props.creation?.draft?.mode === "preset" ? props.creation.draft.preset_key ?? null : null
));
const {
  available,
  reason,
  presets,
  custom,
  mode,
  setMode,
  selectPreset,
  name,
  apparentAge,
  sex,
  conceptText,
  conceptPending,
  applyFrozen,
  raceDisplayName,
  formMessage,
  resultMessage,
  confirmCustom,
  applyConcept,
  requestReset,
  confirmCurrent,
  cancelConfirm,
} = creation;

// The empty portrait slot's silhouette: the single entry of the server's
// table for the current sex and apparent age. No age bands are restated here,
// and an input no single entry matches (blank, fractional) keeps the slot
// neutral instead of inventing a row.
const silhouette = computed(() => {
  const value = apparentAge.value;
  const table = Array.isArray(custom.value?.silhouettes) ? custom.value.silhouettes : [];
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  const matches = table.filter((entry) => (
    entry.sex === sex.value && entry.apparent_age_minimum <= value && value <= entry.apparent_age_maximum
  ));
  return matches.length === 1 ? matches[0].artwork : null;
});

// The concept guide reads the committed proposal slot (never a copy).
const conceptProposal = computed(() => props.creation?.proposal ?? null);

// The footer confirmation routes through the stepped form so an error opens
// its step; the existing confirmCustom pipeline runs unchanged inside it.
const customSteps = ref(null);
function submitCustom() {
  if (customSteps.value) customSteps.value.submit();
  else confirmCustom();
}
</script>

<template>
  <section
    v-if="open"
    class="elosern creation-overlay"
    role="dialog"
    aria-modal="true"
    aria-label="角色創建"
    data-testid="creation-overlay"
    :data-available="available ? 'true' : 'false'"
    :data-mode="mode"
  >
    <!-- Three-column header (design §4): title | mode tabs | subtitle. The
         tabs keep their hooks; they step aside while a confirmation stands. -->
    <header class="creation-overlay__header">
      <div class="creation-overlay__brand">
        <p class="creation-overlay__eyebrow">ELOSERN ‧ 伊洛瑟恩</p>
        <h2 class="creation-overlay__title" data-testid="creation-overlay-title">角色創建</h2>
      </div>
      <nav
        v-if="available && !(stage && stage.stage === 'confirm')"
        class="ui-tabs creation-overlay__modes"
        aria-label="建角方式"
      >
        <button
          v-for="tab in MODE_TABS"
          :key="tab.mode"
          type="button"
          class="ui-tabs__tab creation-overlay__mode"
          :class="{ 'is-active': mode === tab.mode }"
          :aria-pressed="mode === tab.mode"
          :data-testid="`creation-mode-${tab.mode}`"
          @click="setMode(tab.mode)"
        >
          {{ tab.label }}
        </button>
      </nav>
      <p class="creation-overlay__intro">選擇起點，寫下你的故事。</p>
    </header>

    <div class="creation-overlay__body" data-testid="creation-body">
      <template v-if="available">
        <p
          v-if="resultMessage"
          class="creation-result-message"
          role="alert"
          data-testid="creation-result-message"
          :data-outcome="result && result.outcome"
        >
          {{ resultMessage }}
        </p>
        <template v-if="stage && stage.stage === 'confirm'">
          <div class="creation-confirm" data-testid="creation-confirm">
            <div class="creation-confirm-title" data-testid="creation-confirm-title">
              {{ stage.confirmLabel }}
            </div>
            <div class="creation-confirm-actions">
              <button
                type="button"
                class="ui-btn ui-btn--primary"
                data-testid="creation-confirm-ok"
                @click="confirmCurrent"
              >
                確認
              </button>
              <button
                type="button"
                class="ui-btn"
                data-testid="creation-confirm-cancel"
                @click="cancelConfirm"
              >
                取消
              </button>
            </div>
          </div>
        </template>
        <template v-else>

        <CreationPresetWall
          v-if="mode === 'preset'"
          :presets="presets"
          :draft-preset-key="savedPresetKey"
          :disabled="!!dispatchState?.inFlight"
          :race-display-name="raceDisplayName"
          :dock-browsing="stage?.stage === 'presets'"
          @choose="selectPreset"
        />

        <div v-else-if="mode === 'custom'" class="creation-overlay__custom">
          <CreationPortraitSlot :name="name" :silhouette="silhouette" />
          <CreationCustomSteps ref="customSteps" :form="creation" />
        </div>

        <div v-else class="creation-overlay__concept">
          <CreationConceptGuide :proposal="conceptProposal" />
          <section class="creation-concept-editor" aria-labelledby="creation-concept-title">
            <p class="creation-overlay__eyebrow">角色構想</p>
            <h3 id="creation-concept-title" class="creation-concept-editor__title">從一段描述開始</h3>
            <p class="creation-concept-editor__hint">套用後會帶你到自由創建，每一項都還能修改，確認後才會建立角色。</p>
            <label class="creation-concept-field">
              <span>角色概念</span>
              <textarea
                data-testid="creation-field-concept"
                rows="4"
                placeholder="例如：北境礦村出身的年輕獵人，話不多，習慣先觀察再開口。為了找失蹤的兄長離開家鄉……"
                :disabled="conceptPending"
                v-model="conceptText"
              ></textarea>
            </label>
            <div
              v-if="conceptPending"
              class="creation-concept-loading"
              role="status"
              data-testid="creation-concept-loading"
            >
              <span class="creation-concept-spinner" aria-hidden="true"></span>
              <p class="creation-concept-loading-text">概念生成中，請稍候…</p>
            </div>
          </section>
        </div>

        <p v-if="formMessage" id="creation-form-message" class="creation-form-message" role="alert" data-testid="creation-form-message">{{ formMessage }}</p>
        <!-- Outside the steps: errors and actions stay reachable on every step. -->
        <footer class="creation-overlay__footer">
          <button
            type="button"
            class="ui-btn ui-btn--danger creation-reset"
            data-testid="creation-reset"
            @click="requestReset"
          >
            重設
          </button>
          <!-- Preset mode's primary action lives on the expanded card; the
               footer names the wall's keys instead (design §4). -->
          <p v-if="mode === 'preset'" class="creation-overlay__keys" data-testid="creation-preset-keys">
            <span><kbd>←</kbd><kbd>→</kbd> 或數字鍵 切換角色</span>
            <span><kbd>Enter</kbd> 選擇</span>
          </p>
          <button
            v-else-if="mode === 'custom'"
            type="button"
            class="ui-btn ui-btn--primary creation-custom-confirm"
            data-testid="creation-submit"
            @click="submitCustom"
          >
            確認角色
          </button>
          <button
            v-else-if="mode === 'concept'"
            type="button"
            class="ui-btn ui-btn--primary creation-concept-apply"
            data-testid="creation-concept-submit"
            :disabled="applyFrozen"
            @click="applyConcept"
          >
            {{ conceptPending ? "生成中…" : "套用概念" }}
          </button>
        </footer>
        </template>
      </template>

      <p v-else class="creation-unavailable-reason" data-testid="creation-unavailable-reason">
        {{ reason }}
      </p>
    </div>
  </section>
</template>

<style scoped src="./creation-overlay.css"></style>
