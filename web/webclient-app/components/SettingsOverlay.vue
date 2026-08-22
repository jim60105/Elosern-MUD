<script setup>
// Settings overlay (B5 overlay family): the full-viewport settings dialog.
// Client-local options only (no OOB settings panel): font family, type
// scale, reduced motion, the text-to-HTML narrative toggle, and the
// colorblind-safe status palette. Every control change emits the exact
// `options.*` OOB action envelope (the OptionCard emit contract) that the
// C-wave store persists/dispatches — the delta spec's "WHEN a settings
// control changes → THEN it emits the matching options.* envelope".
import { computed, watch } from "vue";

const DEFAULT_OPTIONS = Object.freeze({
  font: "default",
  type_scale: 1.0,
  reduced_motion: "off",
  text_to_html: false,
  colorblind: false,
});

const props = defineProps({
  options: { type: Object, default: () => ({}) },
  open: { type: Boolean, default: true },
});

const emit = defineEmits(["action", "close"]);

const opts = computed(() => ({ ...DEFAULT_OPTIONS, ...props.options }))

// The reduced-motion option is reflected in the app-wide motion tokens: the
// client-local state is applied to the document root so every surface (the
// shell, panels, the narrative feed) inherits the 1ms motion tokens, not
// just the settings dialog (the delta spec's "app-wide motion tokens"
// scenario); the tokens.css media block keeps the OS-preference path.
function applyMotionState() {
  document.documentElement.dataset.reducedMotion = opts.value.reduced_motion === "on" ? "on" : "off";
}

const reducedMotion = computed({
  get: () => opts.value.reduced_motion === "on",
  set: (on) => {
    emit("action", {
      action_id: "options.reduced_motion",
      payload: { value: on ? "on" : "off" },
    });
    document.documentElement.dataset.reducedMotion = on ? "on" : "off";
  },
});

const textToHtml = computed({
  get: () => opts.value.text_to_html,
  set: (on) =>
    emit("action", {
      action_id: "options.text_to_html",
      payload: { enabled: on },
    }),
});

const colorblind = computed({
  get: () => opts.value.colorblind,
  set: (on) =>
    emit("action", {
      action_id: "options.colorblind",
      payload: { enabled: on },
    }),
});

function onFontChange(event) {
  emit("action", { action_id: "options.fonts", payload: { font: event.target.value } });
}

function onTypeScaleChange(event) {
  emit(
    "action",
    {
      action_id: "options.type_scale",
      payload: { value: parseFloat(event.target.value) },
    },
  );
}

// Reflect the option on the document root now, and keep it in sync when a
// new `options` prop arrives (the C-wave store owns persistence; here the
// client-local state drives the app-wide motion tokens).
watch(() => opts.value.reduced_motion, applyMotionState);
applyMotionState();
</script>

<template>
  <section
    v-if="open"
    class="settings-overlay"
    role="dialog"
    aria-label="設定"
    data-testid="settings-overlay"
    :data-reduced-motion="opts.reduced_motion"
    :data-colorblind="opts.colorblind ? 'on' : 'off'"
  >
    <header class="settings-overlay__header">
      <h2 class="settings-overlay__title">設定</h2>
      <button
        type="button"
        class="settings-overlay__close"
        data-testid="settings-overlay-close"
        @click="emit('close')"
      >
        關閉
      </button>
    </header>
    <div class="settings-overlay__body" data-testid="settings-overlay-body">
      <label class="settings-row" for="opt-fonts">
        <span class="settings-row__label">字體</span>
        <select
          id="opt-fonts"
          class="settings-select"
          data-testid="settings-overlay-fonts"
          :value="opts.font"
          @change="onFontChange"
        >
          <option value="default">預設</option>
          <option value="f-display">展示體</option>
          <option value="f-serif">宋體</option>
          <option value="f-sans">黑體</option>
          <option value="f-mono">等寬體</option>
        </select>
      </label>
      <label class="settings-row" for="opt-type-scale">
        <span class="settings-row__label">文字縮放</span>
        <select
          id="opt-type-scale"
          class="settings-select"
          data-testid="settings-overlay-type-scale"
          :value="String(opts.type_scale)"
          @change="onTypeScaleChange"
        >
          <option value="0.9">90%</option>
          <option value="1.0">100%</option>
          <option value="1.1">110%</option>
          <option value="1.25">125%</option>
        </select>
      </label>
      <label class="settings-row">
        <input
          v-model="reducedMotion"
          type="checkbox"
          class="settings-toggle"
          data-testid="settings-overlay-reduced-motion"
          :data-state="opts.reduced_motion"
        />
        <span class="settings-row__label">減少動態效果</span>
      </label>
      <label class="settings-row">
        <input
          v-model="textToHtml"
          type="checkbox"
          class="settings-toggle"
          data-testid="settings-overlay-text-to-html"
        />
        <span class="settings-row__label">HTML 敘事渲染</span>
      </label>
      <label class="settings-row">
        <input
          v-model="colorblind"
          type="checkbox"
          class="settings-toggle"
          data-testid="settings-overlay-colorblind"
        />
        <span class="settings-row__label" :data-state="opts.colorblind ? 'on' : 'off'">色盲配色</span>
      </label>
    </div>
  </section>
</template>

<style scoped>
.settings-overlay {
  position: absolute;
  inset: 0;
  z-index: 40;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--sp-5);
  padding: var(--sp-6);
  background: var(--panel-solid);
  color: var(--paper-100);
}

.settings-overlay__header {
  width: 100%;
  max-width: 440px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: var(--sp-4);
  border-bottom: var(--line);
}

.settings-overlay__title {
  font-family: var(--f-display);
  font-size: var(--text-dialog);
  letter-spacing: 0.18em;
  color: var(--paper-50);
}

.settings-overlay__close {
  border: var(--line);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--paper-300);
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  padding: var(--sp-1) var(--sp-3);
  cursor: pointer;
}

.settings-overlay__body {
  width: 100%;
  max-width: 440px;
  display: grid;
  gap: var(--sp-4);
}

.settings-row {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  font-family: var(--f-sans);
  font-size: var(--text-body);
  color: var(--paper-100);
}

.settings-select {
  flex: 1;
  border: var(--line);
  border-radius: var(--radius-sm);
  background: var(--ink-820);
  color: var(--paper-100);
  font-family: var(--f-mono);
  font-size: var(--text-sm);
  padding: var(--sp-2) var(--sp-3);
}

.settings-toggle {
  width: 16px;
  height: 16px;
  accent-color: var(--seal-500);
}

/* Colorblind mode: switch the status palette to the colorblind-safe
   (Okabe-Ito) encoding inside the dialog, so state is never conveyed by
   color alone. */
.settings-overlay[data-colorblind="on"] {
  --vit-hp: #d55e00;
  --vit-mp: #0072b2;
  --vit-sp: #e69f00;
  --ok: #0072b2;
  --warn: #e69f00;
  --crit: #d55e00;
}
</style>

<style>
/* App-wide reduced motion (unscoped, document-root scope): the user's
   client-local option redefines the motion tokens on <html> so every
   surface of the app (shell, panels, narrative feed) inherits the 1ms
   tokens — the delta spec's "reduced-motion is reflected in the app-wide
   motion tokens" scenario. Mirrors the tokens.css media block, driven by
   the option state instead of the OS preference. Only the motion tokens
   are touched; the rest of the app styling stays untouched. */
html[data-reduced-motion="on"] {
  --motion-fast: 1ms;
  --motion-base: 1ms;
  --motion-slow: 1ms;
  --motion-pulse: 1ms;
  --motion-hp-pulse: 1ms;
}

html[data-reduced-motion="on"] *,
html[data-reduced-motion="on"] *::before,
html[data-reduced-motion="on"] *::after {
  animation-duration: 1ms !important;
  animation-iteration-count: 1 !important;
  transition-duration: 1ms !important;
}
</style>
