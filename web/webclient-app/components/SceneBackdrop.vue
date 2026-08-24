<script setup>
// SceneBackdrop (H1, webclient-hud-01-shell-and-scene, design D3/D8): the
// full-bleed cinematic stage backdrop. Renders the committed `art` panel's
// scene truthfully:
// - `done` with a same-origin URL → cover-cropped `<img>` as the lowest
//   stage layer.
// - `pending` with a prior image already rendered → the prior image,
//   visibly dimmed, with the explicit `目前場景圖片生成中` label (never
//   presented as the current scene).
// - `missing` / `failed` / invalid / `pending` without a prior image /
//   panel unavailable → the current mode's gradient stage with the
//   truthful placeholder label rendered as text outside the bitmap.
// A failed image URL is remembered (client-local) so it is not re-fetched
// without a new URL or a user reload (art degradation never blocks
// gameplay). The scene label and alternative text always render as DOM
// text nodes, so no required information exists only inside the bitmap.
//
// The scene full view (MODIFIED webclient-art-panel): the backdrop's scene
// control opens a full-screen view on click or Enter, Escape closes it and
// restores focus to the control.
import { computed, nextTick, ref, watch } from "vue";

const props = defineProps({
  // The committed `art` v1 panel payload: `available: true` carries
  // `scene` + `portrait_catalog`; the registry-unavailable form carries
  // `available: false` + `reason`.
  art: { type: Object, required: true },
  // The committed mode (the store's reducer mode). Selects the gradient
  // stage for degraded scenes: exploration → explore gradient, combat →
  // combat gradient, creation → dialogue gradient (design D7: the gradient
  // stage differs per mode and carries the inset vignette, applied by the
  // shell's stage, not the backdrop itself).
  mode: { type: String, default: "exploration" },
});

// The current mode's gradient stage token (design D7/D10): the always-correct
// base layer — a degraded OOB channel is visually indistinguishable from an
// ungenerated scene.
const stageGradient = computed(() => {
  if (props.mode === "combat") {
    return "var(--stage-gradient-combat)";
  }
  if (props.mode === "creation") {
    return "var(--stage-gradient-dialogue)";
  }
  return "var(--stage-gradient-explore)";
});

const unavailable = computed(() => props.art?.available === false);
const scene = computed(() => (unavailable.value ? null : (props.art.scene ?? null)));

// The client-local memory of the last successfully rendered scene image
// (design D3): a pending scene retains that prior image dimmed.
const priorImage = ref(null);
// The set of scene URLs that failed to load in the browser (task 4.7):
// a failed URL is not re-fetched before a user reload.
const failedUrls = new Set();
const imageLoadFailed = ref(false);
// The full-view open state (task 4.6) + the opener element for focus
// restore.
const fullViewOpen = ref(false);
const controlEl = ref(null);
const fullViewEl = ref(null);

// When the full view opens, focus moves into it (focus trap: while open,
// Tab stays within the view; Escape closes and returns focus to the
// control that opened it).
watch(fullViewOpen, (open) => {
  if (open) {
    fullViewEl.value?.focus();
  }
});

watch(
  () => props.art,
  () => {
    // A new scene (a fresh URL) resets the load-failure flag; a failed URL
    // stays remembered until a new URL arrives or the page reloads.
    if (scene.value?.url) {
      imageLoadFailed.value = false;
    }
  },
  { deep: true },
);

const sceneUrl = computed(() => {
  const url = scene.value?.url;
  if (url && failedUrls.has(url)) {
    return null;
  }
  return url ?? null;
});

// Which image element renders:
// - done + a live URL → the current image
// - pending + a prior image → the dimmed prior image
const activeImage = computed(() => {
  if (scene.value?.status === "done" && sceneUrl.value && !imageLoadFailed.value) {
    return { url: sceneUrl.value, dimmed: false };
  }
  if (scene.value?.status === "pending" && priorImage.value) {
    return { url: priorImage.value, dimmed: true };
  }
  return null;
});

const showPlaceholder = computed(() => {
  if (unavailable.value) {
    return true;
  }
  const s = scene.value;
  if (!s) {
    return true;
  }
  if (s.status === "pending" && priorImage.value) {
    return false;
  }
  if (s.status === "done") {
    return imageLoadFailed.value || !sceneUrl.value;
  }
  return true;
});

const placeholderLabel = computed(() => {
  if (unavailable.value) {
    return props.art?.reason?.message || "無法提供";
  }
  return scene.value?.placeholder?.label || "場景圖片尚未生成";
});

const placeholderKind = computed(() => {
  if (unavailable.value) {
    return props.art?.reason?.code || "unavailable";
  }
  return (imageLoadFailed.value ? "load_failed" : (scene.value?.placeholder?.kind ?? "unavailable"));
});

// The scene label + alt always render as text outside the bitmap.
const sceneLabel = computed(() => scene.value?.label ?? (unavailable.value ? "場景" : ""));
const sceneAlt = computed(() => scene.value?.alt ?? "");

function onImageLoad(url) {
  if (url) {
    priorImage.value = url;
  }
  imageLoadFailed.value = false;
}

function onImageError(url) {
  if (url) {
    failedUrls.add(url);
  }
  priorImage.value = null;
  imageLoadFailed.value = true;
}

function openFullView() {
  if (fullViewOpen.value) {
    return;
  }
  fullViewOpen.value = true;
  void nextTick().then(() => fullViewEl.value?.focus());
}

function closeFullView(restoreFocus) {
  fullViewOpen.value = false;
  if (restoreFocus && controlEl.value instanceof HTMLElement && document.contains(controlEl.value)) {
    controlEl.value.focus();
  }
  controlEl.value = null;
}

function onControlKeydown(event) {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    openFullView();
  }
}

function onFullViewKeydown(event) {
  if (event.key === "Escape") {
    event.preventDefault();
    closeFullView(true);
  } else if (event.key === "Tab") {
    // Focus trap: Tab cycles between the close button and the dialog root,
    // so keyboard users stay within the full view and cannot tab into the
    // recessed background HUD.
    const root = fullViewEl.value;
    const closeBtn = root?.querySelector(".scene-backdrop__fullview-close");
    if (!root || !closeBtn) {
      return;
    }
    const focusables = [closeBtn, root];
    const activeIndex = focusables.indexOf(document.activeElement);
    event.preventDefault();
    const next = event.shiftKey
      ? focusables[(activeIndex - 1 + focusables.length) % focusables.length]
      : focusables[(activeIndex + 1) % focusables.length];
    next.focus();
  }
}

// Seed the prior-image memory (stories and tests): a pending scene keeps
// its prior image visibly dimmed — never presented as the current scene.
function setPriorImage(url) {
  priorImage.value = url;
}

defineExpose({ openFullView, closeFullView, setPriorImage });
</script>

<template>
  <div
    class="scene-backdrop"
    data-testid="scene-backdrop"
    :data-available="unavailable ? 'false' : 'true'"
    :data-scene-status="scene?.status ?? 'none'"
    :style="{ background: stageGradient }"
  >
    <img
      v-if="activeImage"
      class="scene-backdrop__image"
      data-testid="scene-backdrop-image"
      :src="activeImage.url"
      :class="{ 'scene-backdrop__image--dimmed': activeImage.dimmed }"
      :alt="''"
      aria-hidden="true"
      @load="onImageLoad(activeImage.url)"
      @error="onImageError(activeImage.url)"
    />

    <div
      v-if="showPlaceholder"
      class="scene-backdrop__placeholder"
      data-testid="scene-backdrop-placeholder"
      :data-kind="placeholderKind"
    >
      <span class="scene-backdrop__placeholder-kind" data-testid="scene-backdrop-placeholder-kind">
        {{ placeholderKind }}
      </span>
      <p class="scene-backdrop__placeholder-label" data-testid="scene-backdrop-placeholder-label">
        {{ placeholderLabel }}
      </p>
    </div>

    <p
      v-if="scene?.status === 'pending' && priorImage"
      class="scene-backdrop__generating"
      data-testid="scene-backdrop-generating"
    >
      目前場景圖片生成中
    </p>

    <!-- The scene label and alternative text render as text outside the
         bitmap (MODIFIED webclient-art-panel): no required information
         exists only inside the image. -->
    <p v-if="sceneLabel" class="scene-backdrop__scene-label" data-testid="scene-backdrop-label">
      {{ sceneLabel }}
    </p>
    <p v-if="sceneAlt" class="scene-backdrop__scene-alt" data-testid="scene-backdrop-alt">
      {{ sceneAlt }}
    </p>

    <!-- The scene control opens the full view (MODIFIED art-panel: click or
         Enter on the control; Escape closes and restores focus). -->
    <button
      v-if="!unavailable && scene"
      ref="controlEl"
      type="button"
      class="scene-backdrop__fullview-control"
      data-testid="scene-backdrop-control"
      aria-label="開啟場景全圖"
      @click="openFullView"
      @keydown="onControlKeydown"
    >
      全圖
    </button>

    <div
      v-if="fullViewOpen"
      ref="fullViewEl"
      class="scene-backdrop__fullview"
      data-testid="scene-backdrop-fullview"
      tabindex="-1"
      role="dialog"
      aria-modal="true"
      @keydown="onFullViewKeydown"
    >
      <button
        type="button"
        class="scene-backdrop__fullview-close"
        data-testid="scene-backdrop-fullview-close"
        aria-label="關閉全圖"
        @click="closeFullView(true)"
      >
        關閉
      </button>
      <img
        v-if="activeImage"
        class="scene-backdrop__fullview-image"
        data-testid="scene-backdrop-fullview-image"
        :src="activeImage.url"
        :alt="sceneAlt"
      />
      <div v-else class="scene-backdrop__fullview-gradient" data-testid="scene-backdrop-fullview-gradient"></div>
      <p v-if="sceneLabel" class="scene-backdrop__fullview-label">{{ sceneLabel }}</p>
    </div>
  </div>
</template>

<style>
.scene-backdrop {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
}

/* The mode's gradient stage is the always-correct base layer (design D3):
   the backdrop element's background carries the current mode's gradient. */
.scene-backdrop .scene-backdrop__image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* A pending scene keeps its prior image visibly dimmed (never presented
   as current). */
.scene-backdrop .scene-backdrop__image--dimmed {
  opacity: 0.45;
}

.scene-backdrop .scene-backdrop__placeholder {
  position: absolute;
  left: 50%;
  bottom: calc(var(--dock-h) + 12px);
  transform: translateX(-50%);
  z-index: 2;
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  padding: var(--sp-2) var(--sp-4);
  background: var(--panel);
  backdrop-filter: blur(8px);
  border: 1px dashed var(--seal-600);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  font-size: var(--text-sm);
  color: var(--paper-300);
}

.scene-backdrop .scene-backdrop__placeholder-kind {
  font-family: var(--f-mono);
  font-size: 0.8em;
  text-transform: uppercase;
  color: var(--paper-500);
}

.scene-backdrop .scene-backdrop__placeholder-label {
  margin: 0;
  color: var(--paper-300);
}

.scene-backdrop .scene-backdrop__generating {
  position: absolute;
  left: 50%;
  bottom: calc(var(--dock-h) + 56px);
  transform: translateX(-50%);
  z-index: 2;
  margin: 0;
  padding: 2px var(--sp-3);
  background: var(--panel);
  backdrop-filter: blur(8px);
  border: var(--line);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow);
  color: var(--warn);
  font-size: var(--text-sm);
}

.scene-backdrop .scene-backdrop__scene-label {
  position: absolute;
  left: 16px;
  bottom: calc(var(--dock-h) + 12px);
  z-index: 2;
  margin: 0;
  padding: 4px var(--sp-3);
  background: var(--panel);
  backdrop-filter: blur(8px);
  border: var(--line);
  border-radius: var(--radius-sm);
  color: var(--paper-100);
  font-size: var(--text-sm);
}

.scene-backdrop .scene-backdrop__scene-alt {
  position: absolute;
  left: 16px;
  bottom: calc(var(--dock-h) + 44px);
  z-index: 2;
  margin: 0;
  padding: 4px var(--sp-3);
  background: var(--panel);
  backdrop-filter: blur(8px);
  border: var(--line);
  border-radius: var(--radius-sm);
  color: var(--paper-500);
  font-size: var(--text-sm);
}

.scene-backdrop .scene-backdrop__fullview-control {
  position: absolute;
  right: 16px;
  bottom: calc(var(--dock-h) + 12px);
  z-index: 2;
  background: var(--ink-780);
  border: 1px solid var(--ink-600);
  border-radius: var(--radius-sm);
  color: var(--paper-300);
  font-size: var(--text-sm);
  font-family: var(--f-sans);
  padding: 4px var(--sp-3);
  cursor: pointer;
}

.scene-backdrop .scene-backdrop__fullview-control:hover {
  border-color: var(--gold-500);
  color: var(--paper-50);
}

/* The full-screen scene view (MODIFIED art-panel keyboard-first): the same
   image (or the mode gradient) at full screen, focus-trapped, Escape closes
   and restores focus to the opener. */
.scene-backdrop .scene-backdrop__fullview {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--ink-950);
  outline: none;
}

.scene-backdrop .scene-backdrop__fullview-image {
  max-width: 100%;
  max-height: 86vh;
  object-fit: contain;
}

.scene-backdrop .scene-backdrop__fullview-gradient {
  width: min(960px, 92vw);
  aspect-ratio: 16 / 9;
  background: inherit;
  border-radius: var(--radius);
}

.scene-backdrop .scene-backdrop__fullview-label {
  margin: var(--sp-3) 0 0;
  color: var(--paper-300);
  font-size: var(--text-sm);
}

/* The full-view close control: a keyboard-reachable close button pinned to
   the top-right of the dialog. */
.scene-backdrop .scene-backdrop__fullview-close {
  position: absolute;
  top: var(--sp-4);
  right: var(--sp-4);
  z-index: 1;
  background: var(--ink-780);
  border: 1px solid var(--ink-600);
  border-radius: var(--radius-sm);
  color: var(--paper-300);
  font-size: var(--text-sm);
  font-family: var(--f-sans);
  padding: var(--sp-1) var(--sp-3);
  cursor: pointer;
}

.scene-backdrop .scene-backdrop__fullview-close:hover,
.scene-backdrop .scene-backdrop__fullview-close:focus {
  border-color: var(--gold-500);
  color: var(--paper-50);
  outline: none;
}
</style>
