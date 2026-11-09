<script setup>
// CodexArt (handbook-codex-tab, design D4): a codex entry's art, as a tile
// thumbnail or the detail hero. It renders the slot's art descriptor through
// the shared ordered-attempt lifecycle (`useArtwork`, as ReferenceArtwork
// does) and owns no fallback policy of its own beyond the codex rule: until
// an image (or the descriptor's terminal silhouette) has loaded — a null art,
// an attempt still in flight, every permitted source failed — the category
// emblem stands, so the frame is never empty. The terminal alpha mask counts
// as a loaded image: its probe stays invisible and ArtworkAlpha paints the
// silhouette only after that same resource reported a load.
import { computed, onBeforeUnmount } from "vue";
import ArtworkAlpha from "../ArtworkAlpha.vue";
import CodexEmblem from "./CodexEmblem.vue";
import { artworkAvailability, artworkTerminalUrl } from "../../lib/artwork.js";
import { useArtwork } from "../../composables/useArtwork.js";

const props = defineProps({
  // The slot's art descriptor, or null.
  art: { type: Object, default: null },
  // The committed `lore_codex` panel the descriptor came from.
  panel: { type: Object, default: null },
  // The category key whose emblem is the fallback face.
  emblem: { type: String, default: null },
  // "tile" (a wall thumbnail) or "hero" (the detail band).
  variant: { type: String, default: "tile" },
});

const availability = computed(() =>
  artworkAvailability({ panel: props.panel, required: true, hasReference: !!props.art, artwork: props.art }),
);
const { attempt, phase, onImageLoad, onImageError, dispose } = useArtwork(() => props.art, availability);

const url = computed(() => attempt.value?.url ?? null);
const silhouette = computed(() => !!url.value && url.value === artworkTerminalUrl(props.art));
const showImage = computed(() => !!url.value && (phase.value === "loading" || phase.value === "success"));
const loaded = computed(() => !!url.value && phase.value === "success");
const alphaResult = computed(() => (silhouette.value && loaded.value ? { url: url.value, phase: "success" } : null));

onBeforeUnmount(() => dispose());
</script>

<template>
  <div class="codex-art" :class="`codex-art--${variant}`" :data-art-state="loaded ? 'loaded' : 'emblem'">
    <span v-if="!loaded" class="codex-art__emblem" data-testid="handbook__art-emblem">
      <CodexEmblem :name="emblem" :stroke-width="variant === 'hero' ? 0.9 : 1.3" />
    </span>
    <ArtworkAlpha v-if="alphaResult" class="codex-art__alpha" :result="alphaResult" />
    <img
      v-if="showImage"
      :key="attempt.token"
      class="codex-art__img"
      :class="{ 'codex-art__img--probe': silhouette }"
      data-testid="handbook__art-image"
      :src="url"
      :data-attempt-token="attempt.token"
      alt=""
      aria-hidden="true"
      draggable="false"
      @load="onImageLoad"
      @error="onImageError"
    >
  </div>
</template>

<style scoped>
/* The tile art and hero art of the approved prototype's `.hb-tile__art`,
   `.hb-tile__emblem`, `.hb-hero__art` and `.hb-hero__emblem`
   (docs/design/handbook-codex-titles/CodexTabProto.vue). */
.codex-art {
  position: relative;
  display: grid;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.codex-art__emblem {
  grid-area: 1 / 1;
  place-self: center;
  width: 46%;
  height: 46%;
  margin-bottom: 18%;
  color: var(--gold-400);
}

.codex-art--hero .codex-art__emblem {
  width: calc(120px * var(--ui-scale));
  height: calc(120px * var(--ui-scale));
  margin-bottom: 0;
  color: var(--gold-500);
  filter: drop-shadow(0 0 18px rgba(228, 200, 142, 0.25));
}

.codex-art__img,
.codex-art__alpha {
  position: absolute;
  inset: 0;
  display: block;
  width: 100%;
  height: 100%;
}

.codex-art__img {
  object-fit: cover;
  object-position: center 30%;
}

.codex-art--hero .codex-art__img {
  object-position: center 28%;
}

/* The terminal probe is never painted: it only carries the load signal for
   the alpha mask, which paints the silhouette itself. */
.codex-art__img--probe {
  visibility: hidden;
}
</style>
