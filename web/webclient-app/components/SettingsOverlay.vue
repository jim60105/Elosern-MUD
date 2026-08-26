<script setup>
// SettingsOverlay (B5 overlay family, H5 rework): the body content of the
// shared full-screen overlay surface. The modal chrome now belongs to the
// OverlayHost (header, close control, focus trap). The settings are
// client-local presentation state (webclient-component-showcase delta): no
// settings control dispatches a `ui_action` — `options.dismiss` remains the
// only allowlisted `options.*` action, and this wave does not touch the
// allowlist.
//
// Controls (task 7.2–7.4): the narrative prose scale as the draft's
// A−/A/A+ segmented control at [0.92, 1, 1.12] (replacing the 90/100/110/
// 125% select), the reduced-motion override (three states: default = no
// override, on, off), the text-to-HTML narrative toggle, and the
// colorblind-safe status palette. The invented font-family select is
// removed: the design system's three self-hosted faces are role-assigned and
// the binding design reference has no typeface control.
import { computed } from "vue";

// The draft's three prose-scale steps (index.html :1297 fsScale): A− = 0.92,
// A = 1, A+ = 1.12. The current step is marked by a non-colour indicator
// (border + underline), never by colour alone.
const SCALE_STEPS = [
  { label: "A−", value: 0.92 },
  { label: "A", value: 1 },
  { label: "A+", value: 1.12 },
];

const props = defineProps({
  // The client-local presentation preferences, owned by the store's
  // presentation-preferences slice (task 7.5): the prose scale (number), the
  // text-to-HTML toggle (boolean), the optional reduced-motion override
  // ("on" | "off" | null — null means no override, the OS preference
  // applies), and the colorblind palette (boolean).
  fontScale: { type: Number, default: 1 },
  textToHtml: { type: Boolean, default: true },
  reducedMotion: { type: [String, null], default: null },
  colorblind: { type: Boolean, default: false },
});

const emit = defineEmits([
  "scale-change",
  "text-html-change",
  "reduced-motion-change",
  "colorblind-change",
]);

const currentScaleStep = computed(
  () => SCALE_STEPS.findIndex((s) => s.value === props.fontScale),
);

function selectScale(value) {
  emit("scale-change", value);
}

function onTextHtmlChange(event) {
  emit("text-html-change", event.target.checked);
}

// The reduced-motion control is a three-state segment: 預設 (no override —
// the OS `prefers-reduced-motion` applies), 開 (force reduced), 關 (force
// full motion). The store persists the value through the layout store's
// harmless display-preference lane; the CSS media block is gated on
// `:root:not([data-reduced-motion="off"])` and the explicit states force
// the 1ms motion tokens (task 7.6).
function selectReducedMotion(value) {
  emit("reduced-motion-change", value);
}

function onColorblindChange(event) {
  emit("colorblind-change", event.target.checked);
}
</script>

<template>
  <div class="settings-overlay-body" data-testid="settings-overlay">
    <div class="settings-row">
      <span class="settings-row__label" for="opt-prose-scale">敘述字級</span>
      <span class="settings-row__control">
        <button
          v-for="(step, index) in SCALE_STEPS"
          :key="step.value"
          type="button"
          class="affbtn"
          :class="{ on: index === currentScaleStep }"
          :data-testid="`settings-overlay-scale-${step.label}`"
          :aria-pressed="index === currentScaleStep"
          @click="selectScale(step.value)"
        >
          {{ step.label }}
        </button>
      </span>
    </div>
    <div class="settings-row">
      <span class="settings-row__label">減少動態效果</span>
      <span class="settings-row__control">
        <button
          type="button"
          class="affbtn"
          :class="{ on: reducedMotion === null }"
          data-testid="settings-overlay-reduced-motion-default"
          :aria-pressed="reducedMotion === null"
          @click="selectReducedMotion(null)"
        >
          預設
        </button>
        <button
          type="button"
          class="affbtn"
          :class="{ on: reducedMotion === 'on' }"
          data-testid="settings-overlay-reduced-motion-on"
          :aria-pressed="reducedMotion === 'on'"
          @click="selectReducedMotion('on')"
        >
          開
        </button>
        <button
          type="button"
          class="affbtn"
          :class="{ on: reducedMotion === 'off' }"
          data-testid="settings-overlay-reduced-motion-off"
          :aria-pressed="reducedMotion === 'off'"
          @click="selectReducedMotion('off')"
        >
          關
        </button>
      </span>
    </div>
    <label class="settings-row">
      <input
        type="checkbox"
        class="settings-toggle"
        data-testid="settings-overlay-text-to-html"
        :checked="textToHtml"
        @change="onTextHtmlChange"
      />
      <span class="settings-row__label">HTML 敘事渲染</span>
    </label>
    <label class="settings-row">
      <input
        type="checkbox"
        class="settings-toggle"
        data-testid="settings-overlay-colorblind"
        :checked="colorblind"
        @change="onColorblindChange"
      />
      <span class="settings-row__label">色盲配色</span>
    </label>
  </div>
</template>

<style scoped>
.settings-row {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  font-family: var(--f-sans);
  font-size: var(--text-body);
  color: var(--paper-100);
}

.settings-row__label {
  flex: none;
  color: var(--paper-300);
}

.settings-row__control {
  display: inline-flex;
  gap: var(--sp-2);
}

/* The A−/A/A+ and reduced-motion segmented controls: the current step is
   marked by a gold border and underline — a non-colour indicator, not a
   fill alone (the delta's "marked by a non-colour indicator" scenario). */
.affbtn {
  padding: 6px 12px;
  color: var(--paper-300);
  background: transparent;
  border: var(--line);
  border-radius: var(--radius-sm);
  font-family: var(--f-mono);
  font-size: var(--text-sm);
  cursor: pointer;
}

.affbtn.on {
  color: var(--paper-50);
  border-color: var(--gold-500);
  box-shadow: inset 0 -2px 0 var(--gold-400);
}

.affbtn:hover {
  color: var(--seal-400);
  border-color: var(--seal-400);
}

.affbtn:focus-visible {
  color: var(--gold-400);
  border-color: var(--gold-400);
}

.settings-toggle {
  width: 16px;
  height: 16px;
  accent-color: var(--seal-500);
}
</style>
