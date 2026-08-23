<script setup>
// ArtPanel (B4 world family): the art surface of the world. Renders the
// committed `art` v1 panel payload — a 16:9 scene frame with its label and
// alt as DOM nodes outside the bitmap, and the 3:4 portrait catalog with its
// contextual name/role overlays — or the registry-owned unavailable form.
// Design D1 truthfulness: a not-yet-generated asset degrades to the
// payload's own placeholder frame, and a pending scene keeps its prior
// image with an explicit generating note; nothing is invented.
import { computed, ref, watch } from "vue";

const props = defineProps({
  // The committed `art` v1 panel payload: `available: true` carries
  // `scene` + `portrait_catalog`; the registry-unavailable form carries
  // `available: false` + `reason`.
  art: { type: Object, required: true },
});

// Design-draft aspect frames: 16:9 for the scene, 3:4 for portraits.
const SCENE_STYLE = {
  aspectRatio: "16 / 9",
  objectFit: "cover",
  width: "100%",
  height: "auto",
};
const PLACEHOLDER_FRAME_STYLE = { aspectRatio: "16 / 9", width: "100%" };
const PORTRAIT_STYLE = {
  aspectRatio: "3 / 4",
  objectFit: "cover",
  width: "88px",
  height: "auto",
};

const unavailable = computed(() => props.art?.available === false);
const scene = computed(() => (unavailable.value ? null : (props.art.scene ?? null)));
const sceneUrl = computed(() => scene.value?.url ?? null);
const sceneLabel = computed(() => scene.value?.label ?? "");
const sceneAlt = computed(() => scene.value?.alt ?? "");
const scenePlaceholder = computed(() => (scene.value?.placeholder ?? null));
// A scene image that fails to load in the browser degrades to a truthful
// fallback frame (spec: art degradation never blocks gameplay). The failure
// flag resets only when the scene URL changes, so a stale URL is never
// re-fetched without a new URL or a user reload.
const imageLoadFailed = ref(false);
watch(sceneUrl, () => {
  imageLoadFailed.value = false;
});
const sceneNote = computed(() =>
  scene.value && scene.value.status === "pending" && scene.value.url
    ? "場景圖像生成中，顯示上一版圖像"
    : "",
);
// Flat entry objects keyed by catalog ID, in the catalog's own order.
const portraitEntries = computed(() => {
  if (unavailable.value) return [];
  return Object.entries(props.art.portrait_catalog ?? {}).map(([id, entry]) => ({
    id,
    ...entry,
  }));
});
</script>

<template>
  <aside class="art-panel" data-testid="art-panel">
    <h3 class="art-panel__title" data-testid="art-panel__title">美術展示</h3>

    <div
      v-if="unavailable"
      class="art-panel__unavailable"
      data-testid="art-panel__scene-placeholder"
      :data-kind="props.art.reason?.code"
      :style="PLACEHOLDER_FRAME_STYLE"
    >
      <p class="art-panel__unavailable-reason" data-testid="art-panel__unavailable">
        {{ props.art.reason?.message }}
      </p>
    </div>

    <section v-else class="art-panel__section" data-testid="art-panel__section">
      <div class="art-panel__scene-frame" data-testid="art-panel__scene-frame">
        <img
          v-if="sceneUrl && !imageLoadFailed"
          class="art-panel__scene"
          data-testid="art-panel__scene"
          :src="sceneUrl"
          aria-hidden="true"
          :style="SCENE_STYLE"
          @error="imageLoadFailed = true"
        />
        <div
          v-else-if="imageLoadFailed || scenePlaceholder"
          class="art-panel__scene-placeholder"
          data-testid="art-panel__scene-placeholder"
          :data-kind="imageLoadFailed ? 'load_failed' : (scenePlaceholder?.kind ?? 'unavailable')"
        >
          <span class="art-panel__placeholder-kind" data-testid="art-panel__scene-placeholder-kind">
            {{ imageLoadFailed ? 'load_failed' : scenePlaceholder.kind }}
          </span>
          <p class="art-panel__placeholder-label" data-testid="art-panel__scene-placeholder-label">
            {{ imageLoadFailed ? '載入失敗' : scenePlaceholder.label }}
          </p>
        </div>
        <p v-if="sceneNote" class="art-panel__generating" data-testid="art-panel__generating">
          {{ sceneNote }}
        </p>
        <p class="art-panel__scene-label" data-testid="art-panel__scene-label">
          {{ sceneLabel }}
        </p>
        <p class="art-panel__scene-alt" data-testid="art-panel__scene-alt">
          {{ sceneAlt }}
        </p>
      </div>

      <div
        v-if="portraitEntries.length > 0"
        class="art-panel__portraits"
        data-testid="art-panel__portraits"
      >
        <div
          v-for="entry in portraitEntries"
          :key="entry.id"
          class="art-panel__portrait-tile"
          :data-testid="`art-panel__portrait--${entry.id}`"
          :data-placeholder="String(entry.placeholder !== null && entry.placeholder !== undefined)"
          :data-status="entry.status"
        >
          <img
            v-if="entry.url"
            class="art-panel__portrait-img"
            :data-testid="`art-panel__portrait-img--${entry.id}`"
            :src="entry.url"
            aria-hidden="true"
            :style="PORTRAIT_STYLE"
          />
          <div v-else class="art-panel__portrait-placeholder" :data-testid="`art-panel__portrait-placeholder--${entry.id}`">
            <span class="art-panel__placeholder-kind">{{ entry.placeholder?.kind }}</span>
            <p class="art-panel__placeholder-label">{{ entry.placeholder?.label }}</p>
          </div>
          <p class="art-panel__portrait-context" :data-testid="`art-panel__portrait-context--${entry.id}`">
            <span class="art-panel__portrait-context-name">{{ entry.context?.name }}</span>
            <span class="art-panel__portrait-context-role">{{ entry.context?.role }}</span>
          </p>
        </div>
      </div>
    </section>
  </aside>
</template>

<style scoped>
.art-panel {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  box-sizing: border-box;
  padding: var(--sp-3) var(--sp-4);
  background: var(--panel);
  border: var(--line);
  border-radius: var(--radius);
  font-family: var(--f-sans);
}

.art-panel__title {
  margin: 0;
  color: var(--paper-100);
  font-family: var(--f-display);
  font-size: 1em;
}

.art-panel__unavailable {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 64px;
  background: var(--panel-hi);
  border: 1px dashed var(--seal-600);
  border-radius: var(--radius-sm);
}

.art-panel__unavailable-reason {
  margin: 0;
  color: var(--paper-300);
  font-size: 0.85em;
}

.art-panel__section {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.art-panel__scene-frame {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.art-panel__scene {
  max-width: 100%;
}

.art-panel__scene-placeholder {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  padding: var(--sp-2) var(--sp-3);
  background: var(--panel-hi);
  border: 1px dashed var(--seal-600);
  border-radius: var(--radius-sm);
}

.art-panel__generating {
  margin: 0;
  color: var(--warn);
  font-size: 0.85em;
}

.art-panel__scene-label {
  margin: 0;
  color: var(--paper-100);
  font-size: 0.9em;
}

.art-panel__scene-alt {
  margin: 0;
  color: var(--paper-500);
  font-size: 0.85em;
}

.art-panel__portraits {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-3);
  padding-top: var(--sp-2);
  border-top: var(--line);
}

.art-panel__portrait-tile {
  position: relative;
  width: 88px;
  aspect-ratio: 3 / 4;
  overflow: hidden;
  border-radius: var(--radius-sm);
}

.art-panel__portrait-placeholder {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: var(--sp-1);
  padding: var(--sp-2);
  height: 100%;
  background: var(--panel-hi);
  border: 1px dashed var(--seal-600);
  border-radius: var(--radius-sm);
}

.art-panel__portrait-context {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  margin: 0;
  padding: 2px var(--sp-1);
  background: var(--ink-950);
  color: var(--paper-100);
  font-family: var(--f-mono);
  font-size: 0.75em;
}

.art-panel__portrait-context-role {
  color: var(--gold-400);
}

.art-panel__placeholder-kind {
  color: var(--paper-500);
  font-family: var(--f-mono);
  font-size: 0.8em;
  text-transform: uppercase;
}

.art-panel__placeholder-label {
  margin: 0;
  color: var(--paper-300);
  font-size: 0.85em;
}
</style>
