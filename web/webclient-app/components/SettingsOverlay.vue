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
// 125% select), the motion level (完整 / 減少 / 關閉), the text-to-HTML
// narrative toggle, and the colorblind-safe status palette. The invented
// font-family select is removed: the design system's three self-hosted faces
// are role-assigned and the binding design reference has no typeface control.
//
// C7 (webclient-typewriter-reading-prefs, design D10): the 閱讀設定 section
// adds the text-speed segment (慢 / 標準 / 快 / 瞬間) and the auto-advance
// toggle. The message window reads both as props; an effective motion level
// other than 完整 always shows pages at once, whatever the chosen speed.
//
// C11a (webclient-motion-level, design D4): the 輔助顯示 section's motion
// control is the three-level 動態效果 segment. It marks the EFFECTIVE level
// (the stored level, or the OS preference while nothing is stored) and
// stores the level the player picks. There is no "follow the system" button:
// a fourth state would be one no reader could tell from its resolved level,
// and the unset state exists only until the first choice.
//
// A14 (webclient-settings-reading-preview): a `ReadingSample` spans the body
// above both cards and previews the prose scale, the text speed and the
// motion level locally — it never reaches the store, the log or the live
// reader, and closing the overlay unmounts it and stops its clock. The
// toggles stay native checkboxes (role="switch", real checked state, Space,
// the same change events) drawn as switches; the segments are one framed
// strip; the cards share equal tracks but keep their own content height.
import { computed } from "vue";
import ReadingSample from "./ReadingSample.vue";
import { MOTION_LEVELS } from "../lib/motion_level.js";
import { TEXT_SPEEDS } from "../lib/message_reveal.js";

// The draft's three prose-scale steps (index.html :1297 fsScale): A− = 0.92,
// A = 1, A+ = 1.12. The current step is marked by a non-colour indicator
// (border + underline), never by colour alone.
const SCALE_STEPS = [
  { label: "A−", value: 0.92 },
  { label: "A", value: 1 },
  { label: "A+", value: 1.12 },
];

// The four text-speed steps, in `TEXT_SPEEDS` order.
const SPEED_LABELS = { slow: "慢", normal: "標準", fast: "快", instant: "瞬間" };
const SPEED_STEPS = TEXT_SPEEDS.map((value) => ({ value, label: SPEED_LABELS[value] }));

// The three motion levels, in `MOTION_LEVELS` order (design D4).
const MOTION_LABELS = { full: "完整", reduced: "減少", off: "關閉" };
const MOTION_STEPS = MOTION_LEVELS.map((value) => ({ value, label: MOTION_LABELS[value] }));

const props = defineProps({
  // The client-local presentation preferences, owned by the store's
  // presentation-preferences slice (task 7.5): the prose scale (number), the
  // text-to-HTML toggle (boolean), the EFFECTIVE motion level ("full" |
  // "reduced" | "off"), and the colorblind palette (boolean).
  fontScale: { type: Number, default: 1 },
  textToHtml: { type: Boolean, default: true },
  motionLevel: {
    type: String,
    default: "full",
    validator: (value) => MOTION_LEVELS.includes(value),
  },
  colorblind: { type: Boolean, default: false },
  // C7: the reading preferences — the typing speed (one of `TEXT_SPEEDS`)
  // and the opt-in auto-advance.
  textSpeed: { type: String, default: "normal" },
  autoAdvance: { type: Boolean, default: false },
});

const emit = defineEmits([
  "scale-change",
  "text-html-change",
  "motion-level-change",
  "colorblind-change",
  "text-speed-change",
  "auto-advance-change",
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

// The motion control is the three-level segment (design D4). The pressed
// button is the EFFECTIVE level; selecting one stores it through the layout
// store's harmless display-preference lane, and the store writes the new
// effective level to `<html data-motion>` at once.
function selectMotionLevel(value) {
  emit("motion-level-change", value);
}

function onColorblindChange(event) {
  emit("colorblind-change", event.target.checked);
}

function selectTextSpeed(value) {
  emit("text-speed-change", value);
}

function onAutoAdvanceChange(event) {
  emit("auto-advance-change", event.target.checked);
}
</script>

<template>
  <div class="settings-overlay-body" data-testid="settings-overlay">
    <div class="settings-intro">
      <h4>依照你的閱讀習慣調整介面</h4>
      <p>設定會立即套用並儲存在此瀏覽器，不影響角色能力與遊戲規則。</p>
    </div>
    <ReadingSample
      class="settings-sample"
      :font-scale="fontScale"
      :text-speed="textSpeed"
      :motion-level="motionLevel"
    />
    <section class="settings-section" aria-label="閱讀設定">
      <h4 class="settings-section__title">閱讀設定</h4>
      <div class="settings-row">
        <div class="settings-row__copy">
          <span id="opt-prose-scale" class="settings-row__label">敘述字級</span>
          <p id="opt-prose-scale-help" class="settings-row__description">調整敘事文字的大小。</p>
        </div>
        <span class="settings-row__control" role="group" aria-labelledby="opt-prose-scale" aria-describedby="opt-prose-scale-help">
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
          <span id="opt-text-to-html" class="settings-row__label">HTML 敘事渲染</span>
          <span id="opt-text-to-html-help" class="settings-row__description">保留敘事排版；關閉後以純文字閱讀。</span>
        </span>
        <input
          type="checkbox"
          role="switch"
          class="settings-toggle"
          aria-labelledby="opt-text-to-html"
          aria-describedby="opt-text-to-html-help"
          data-testid="settings-overlay-text-to-html"
          :checked="textToHtml"
          @change="onTextHtmlChange"
        />
      </label>
      <div class="settings-row">
        <div class="settings-row__copy">
          <span id="opt-text-speed" class="settings-row__label">文字速度</span>
          <p id="opt-text-speed-help" class="settings-row__description">逐字顯示訊息的速度；動態效果為「減少」或「關閉」時一律立即顯示。</p>
        </div>
        <span class="settings-row__control" role="group" aria-labelledby="opt-text-speed" aria-describedby="opt-text-speed-help">
        <button
          v-for="step in SPEED_STEPS"
          :key="step.value"
          type="button"
          class="affbtn"
          :class="{ on: step.value === textSpeed }"
          :data-testid="`settings-overlay-text-speed-${step.value}`"
          :aria-pressed="step.value === textSpeed"
          @click="selectTextSpeed(step.value)"
        >
          {{ step.label }}
        </button>
        </span>
      </div>
      <label class="settings-row settings-row--toggle">
        <span class="settings-row__copy">
          <span id="opt-auto-advance" class="settings-row__label">自動翻頁</span>
          <span id="opt-auto-advance-help" class="settings-row__description">每頁顯示完畢後稍候自動翻頁；回應的最後一頁不會自動翻過。</span>
        </span>
        <input
          type="checkbox"
          role="switch"
          class="settings-toggle"
          aria-labelledby="opt-auto-advance"
          aria-describedby="opt-auto-advance-help"
          data-testid="settings-overlay-auto-advance"
          :checked="autoAdvance"
          @change="onAutoAdvanceChange"
        />
      </label>
    </section>
    <section class="settings-section" aria-label="輔助顯示">
      <h4 class="settings-section__title">輔助顯示</h4>
      <div class="settings-row">
        <div class="settings-row__copy">
          <span id="opt-motion-level" class="settings-row__label">動態效果</span>
          <p id="opt-motion-level-help" class="settings-row__description">未選擇時跟隨作業系統的偏好。「減少」只保留短暫淡入淡出並立即顯示文字；「關閉」讓所有變化立即呈現。</p>
        </div>
        <span class="settings-row__control" role="group" aria-labelledby="opt-motion-level" aria-describedby="opt-motion-level-help">
        <button
          v-for="step in MOTION_STEPS"
          :key="step.value"
          type="button"
          class="affbtn"
          :class="{ on: step.value === motionLevel }"
          :data-testid="`settings-overlay-motion-${step.value}`"
          :aria-pressed="step.value === motionLevel"
          @click="selectMotionLevel(step.value)"
        >
          {{ step.label }}
        </button>
        </span>
      </div>
      <label class="settings-row settings-row--toggle">
        <span class="settings-row__copy">
          <span id="opt-colorblind" class="settings-row__label">色盲配色</span>
          <span id="opt-colorblind-help" class="settings-row__description">以替代色盤區分狀態資訊。</span>
        </span>
        <input
          type="checkbox"
          role="switch"
          class="settings-toggle"
          aria-labelledby="opt-colorblind"
          aria-describedby="opt-colorblind-help"
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
/* Two equal tracks; each card is as tall as its content (no blank filler
   height under the shorter card). The reading sample and the intro span
   both tracks. */
.settings-overlay-body {
  color-scheme: dark;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: start;
  gap: calc(24px * var(--ui-scale));
}

.settings-intro,
.settings-sample,
.settings-footnote {
  grid-column: 1 / -1;
}

.settings-intro h4 {
  margin: 0 0 calc(8px * var(--ui-scale));
  color: var(--paper-50);
  font: var(--text-3xl)/1.4 var(--f-serif);
}

.settings-intro p,
.settings-footnote {
  margin: 0;
  color: var(--paper-300);
  font-size: var(--text-md);
  line-height: 1.7;
}

.settings-section {
  min-width: 0;
  padding: calc(8px * var(--ui-scale)) calc(24px * var(--ui-scale)) calc(12px * var(--ui-scale));
  border: var(--line);
  border-radius: var(--radius);
  background: linear-gradient(140deg, #242629a0, #101215d0);
}

.settings-section__title {
  display: flex;
  align-items: center;
  gap: calc(10px * var(--ui-scale));
  margin: 0;
  padding: calc(16px * var(--ui-scale)) 0 calc(14px * var(--ui-scale));
  border-bottom: var(--line);
  color: var(--gold-400);
  font: var(--text-xl) var(--f-serif);
  letter-spacing: 0.06em;
}

/* A small gold lozenge seats each card title, echoing the band's ornament. */
.settings-section__title::before {
  content: "";
  flex: none;
  width: calc(6px * var(--ui-scale));
  height: calc(6px * var(--ui-scale));
  transform: rotate(45deg);
  border: 1px solid var(--gold-400);
  background: #0f0c12;
}

.settings-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--sp-3);
  padding: calc(18px * var(--ui-scale)) 0;
  font-family: var(--f-sans);
  font-size: var(--text-base);
  color: var(--paper-100);
}

.settings-row + .settings-row {
  border-top: 1px solid #ffffff0d;
}

.settings-row__label {
  color: var(--paper-100);
  font-size: var(--text-base);
}

.settings-row__copy {
  flex: 1;
  min-width: calc(180px * var(--ui-scale));
}

/* Help copy sits one step above the 12px chrome floor, at a readable tier. */
.settings-row__description {
  display: block;
  margin: calc(6px * var(--ui-scale)) 0 0;
  color: var(--paper-300);
  font-size: var(--text-md);
  line-height: 1.7;
}

.settings-row--toggle {
  cursor: pointer;
}

/* The A−/A/A+, text-speed, and motion-level segmented controls: one framed
   strip of equal segments. The current step is filled, carries a gold inset
   underline and is the pressed button — a non-colour indicator, not a fill
   alone (the delta's "marked by a non-colour indicator" scenario). */
.settings-row__control {
  display: inline-flex;
  flex: none;
  padding: calc(3px * var(--ui-scale));
  gap: calc(3px * var(--ui-scale));
  border: var(--line);
  border-radius: var(--radius-sm);
  background: #0c0d11b0;
}

.affbtn {
  min-width: calc(48px * var(--ui-scale));
  min-height: calc(36px * var(--ui-scale));
  padding: calc(6px * var(--ui-scale)) calc(12px * var(--ui-scale));
  color: var(--paper-300);
  background: transparent;
  border: 1px solid transparent;
  border-radius: calc(var(--radius-sm) - 2px);
  font-family: var(--f-sans);
  font-size: var(--text-md);
  cursor: pointer;
  transition:
    color var(--motion-fast) var(--ease-standard),
    background-color var(--motion-fast) var(--ease-standard),
    border-color var(--motion-fast) var(--ease-standard);
}

.affbtn.on {
  color: var(--paper-50);
  background: var(--gold-glow);
  border-color: var(--gold-500);
  box-shadow: inset 0 -2px 0 var(--gold-400);
}

.affbtn:hover {
  color: var(--gold-400);
}

.affbtn:focus-visible {
  color: var(--gold-400);
  outline: 2px solid var(--gold-400);
  outline-offset: 1px;
}

/* The toggles are native checkboxes (role="switch", real checked state,
   Space, change events) drawn as switches: a track whose knob slides right
   and whose ground turns gold when on. Position and fill both mark the
   state; the knob's travel uses the motion tokens, so it is instant at
   減少 and 關閉. */
.settings-toggle {
  appearance: none;
  position: relative;
  flex: none;
  width: calc(46px * var(--ui-scale));
  height: calc(26px * var(--ui-scale));
  margin: 0;
  border: 1px solid var(--paper-700);
  border-radius: var(--radius);
  background: #0c0d11;
  cursor: pointer;
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    border-color var(--motion-fast) var(--ease-standard);
}

.settings-toggle::before {
  content: "";
  position: absolute;
  top: calc(3px * var(--ui-scale));
  left: calc(3px * var(--ui-scale));
  width: calc(18px * var(--ui-scale));
  height: calc(18px * var(--ui-scale));
  border-radius: 50%;
  background: var(--paper-300);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
  transition:
    transform var(--motion-fast) var(--ease-standard),
    background-color var(--motion-fast) var(--ease-standard);
}

.settings-toggle:checked {
  border-color: var(--gold-400);
  background: linear-gradient(180deg, var(--gold-500), var(--gold-600));
}

.settings-toggle:checked::before {
  transform: translateX(calc(20px * var(--ui-scale)));
  background: var(--paper-50);
}

.settings-row--toggle:hover .settings-toggle {
  border-color: var(--gold-400);
}

.settings-toggle:focus-visible {
  outline: 2px solid var(--gold-400);
  outline-offset: calc(3px * var(--ui-scale));
}

@media (forced-colors: active) {
  .settings-toggle {
    border-color: CanvasText;
  }
  .settings-toggle::before {
    background: CanvasText;
  }
  .settings-toggle:checked {
    background: Highlight;
  }
}

@media (max-width: 850px) {
  .settings-overlay-body { grid-template-columns: minmax(0, 1fr); gap: calc(18px * var(--ui-scale)); }
  .settings-section { padding: calc(6px * var(--ui-scale)) calc(18px * var(--ui-scale)) calc(10px * var(--ui-scale)); }
  .settings-intro h4 { font-size: var(--text-xl); }
}
</style>
