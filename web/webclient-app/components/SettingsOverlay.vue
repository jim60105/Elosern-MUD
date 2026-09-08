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
    <div class="settings-intro">
      <h4>依照你的閱讀習慣調整介面</h4>
      <p>設定會立即套用並儲存在此瀏覽器，不影響角色能力與遊戲規則。</p>
    </div>
    <section class="settings-section" aria-label="閱讀設定">
      <h4 class="settings-section__title">閱讀設定</h4>
      <div class="settings-row">
        <div class="settings-row__copy">
          <span id="opt-prose-scale" class="settings-row__label">敘述字級</span>
          <p class="settings-row__description">調整敘事文字的大小。</p>
        </div>
        <span class="settings-row__control" role="group" aria-labelledby="opt-prose-scale">
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
      <label class="settings-row settings-row--toggle">
        <span class="settings-row__copy">
          <span class="settings-row__label">HTML 敘事渲染</span>
          <span class="settings-row__description">保留敘事排版；關閉後以純文字閱讀。</span>
        </span>
        <input
          type="checkbox"
          class="settings-toggle"
          aria-label="HTML 敘事渲染"
          data-testid="settings-overlay-text-to-html"
          :checked="textToHtml"
          @change="onTextHtmlChange"
        />
      </label>
    </section>
    <section class="settings-section" aria-label="輔助顯示">
      <h4 class="settings-section__title">輔助顯示</h4>
      <div class="settings-row">
        <div class="settings-row__copy">
          <span id="opt-reduced-motion" class="settings-row__label">減少動態效果</span>
          <p class="settings-row__description">「預設」會沿用作業系統的偏好。</p>
        </div>
        <span class="settings-row__control" role="group" aria-labelledby="opt-reduced-motion">
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
      <label class="settings-row settings-row--toggle">
        <span class="settings-row__copy">
          <span class="settings-row__label">色盲配色</span>
          <span class="settings-row__description">以替代色盤區分狀態資訊。</span>
        </span>
        <input
          type="checkbox"
          class="settings-toggle"
          aria-label="色盲配色"
          data-testid="settings-overlay-colorblind"
          :checked="colorblind"
          @change="onColorblindChange"
        />
      </label>
    </section>
    <p class="settings-footnote">按 Esc 返回遊戲。</p>
  </div>
</template>

<style scoped>
.settings-overlay-body {
  color-scheme: dark;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 24px;
}

.settings-intro,
.settings-footnote {
  grid-column: 1 / -1;
}

.settings-intro h4 {
  margin: 0 0 12px;
  color: var(--paper-50);
  font: 26px/1.5 var(--f-serif);
}

.settings-intro p,
.settings-footnote {
  margin: 0;
  color: var(--paper-300);
  font-size: 13px;
  line-height: 1.8;
}

.settings-section {
  min-width: 0;
  padding: 24px;
  border: var(--line);
  border-radius: var(--radius);
  background: linear-gradient(140deg, #242629a0, #101215d0);
}

.settings-section__title {
  margin: 0 0 8px;
  padding-bottom: 18px;
  border-bottom: var(--line);
  color: var(--gold-400);
  font: 20px var(--f-serif);
}

.settings-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--sp-3);
  padding: 22px 0;
  font-family: var(--f-sans);
  font-size: var(--text-body);
  color: var(--paper-100);
}

.settings-row__label {
  color: var(--paper-100);
  font-size: 15px;
}

.settings-row__copy {
  flex: 1;
  min-width: 180px;
}

.settings-row__description {
  display: block;
  margin: 8px 0 0;
  color: var(--paper-300);
  font-size: 12px;
  line-height: 1.8;
}

.settings-row--toggle {
  border-top: 1px solid #ffffff0a;
  cursor: pointer;
}

.settings-row__control {
  display: inline-flex;
  gap: var(--sp-2);
}

/* The A−/A/A+ and reduced-motion segmented controls: the current step is
   marked by a gold border and underline — a non-colour indicator, not a
   fill alone (the delta's "marked by a non-colour indicator" scenario). */
.affbtn {
  min-width: 44px;
  min-height: 40px;
  padding: 8px 12px;
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
  background: var(--gold-glow);
  border-color: var(--gold-500);
  box-shadow: inset 0 -2px 0 var(--gold-400);
}

.affbtn:hover {
  color: var(--gold-400);
  border-color: var(--gold-500);
}

.affbtn:focus-visible {
  color: var(--gold-400);
  border-color: var(--gold-400);
}

.settings-toggle {
  flex: none;
  width: 22px;
  height: 22px;
  margin: 0;
  accent-color: var(--gold-500);
  cursor: pointer;
}

@media (max-width: 850px) {
  .settings-overlay-body { grid-template-columns: minmax(0, 1fr); gap: 18px; }
  .settings-section { padding: 18px; }
  .settings-intro h4 { font-size: 21px; }
}
</style>
